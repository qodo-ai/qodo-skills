import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { planMarketplaceAutoStart } from '../scripts/plan-marketplace-auto-start.mjs';

const sha = 'b'.repeat(40);
const release = { tag_name: 'v1.0.10', draft: false, prerelease: false, immutable: true };
const index = Buffer.from(JSON.stringify({ schemaVersion: 2, packageVersion: '1.0.10', sourceCommit: sha }));
const bundle = Buffer.from(
  JSON.stringify({
    distribution: 'qodo-cli-managed',
    packageVersion: '1.0.10',
    source: { repository: 'https://github.com/qodo-ai/qodo-skills', tag: 'v1.0.10' },
  }),
);
const digest = (body) => `${createHash('sha256').update(body).digest('hex')}  artifact\n`;
const assetBodies = {
  'qodo-skills-index.json': index,
  'qodo-skills-index.json.sha256': Buffer.from(digest(index)),
  'qodo-cli-managed-bundle.json': bundle,
  'qodo-cli-managed-bundle.json.sha256': Buffer.from(digest(bundle)),
};
const releaseAssets = Object.keys(assetBodies).map((name) => ({
  name,
  url: `https://github.test/assets/${name}`,
}));
release.assets = releaseAssets;

function skillsPointer(publicTag = 'v1.0.10') {
  return {
    releaseTag: publicTag,
    releaseIndex: `skills/releases/${publicTag}/qodo-skills-index.json`,
    releaseIndexChecksum: `skills/releases/${publicTag}/qodo-skills-index.json.sha256`,
    cliManagedBundle: `skills/releases/${publicTag}/qodo-cli-managed-bundle.json`,
    cliManagedChecksum: `skills/releases/${publicTag}/qodo-cli-managed-bundle.json.sha256`,
  };
}

function response(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function fakeFetch({ publicTag = 'v1.0.10', runs = [], releaseBody = release, corruptIndex = false } = {}) {
  return async (input) => {
    const url = String(input);
    if (url.endsWith('/version.json')) return response({ skills: skillsPointer(publicTag) });
    if (url.endsWith('/qodo-skills-index.json')) return new Response(index);
    if (url.endsWith('/qodo-skills-index.json.sha256')) {
      return new Response(corruptIndex ? `${'0'.repeat(64)}  artifact\n` : digest(index));
    }
    if (url.endsWith('/qodo-cli-managed-bundle.json')) return new Response(bundle);
    if (url.endsWith('/qodo-cli-managed-bundle.json.sha256')) return new Response(digest(bundle));
    if (url.includes('/assets/')) {
      const name = url.split('/').at(-1);
      if (name === 'qodo-skills-index.json.sha256' && corruptIndex) {
        return new Response(`${'0'.repeat(64)}  artifact\n`);
      }
      return new Response(assetBodies[name]);
    }
    if (url.includes('/releases/tags/')) return response(releaseBody);
    if (url.includes('/commits/')) return response({ sha });
    if (url.includes('/actions/workflows/')) {
      const page = Number(new URL(url).searchParams.get('page'));
      return response({ workflow_runs: page === 1 ? runs : [] });
    }
    throw new Error(`unexpected request: ${url}`);
  };
}

test('the watcher uses same-repository workflow dispatch and keeps provider gates intact', () => {
  const workflow = readFileSync(
    fileURLToPath(new URL('../.github/workflows/marketplace-auto-start.yml', import.meta.url)),
    'utf8',
  );

  assert.match(workflow, /schedule:/);
  assert.match(workflow, /actions: write/);
  assert.match(workflow, /gh workflow run ship-marketplaces\.yml/);
  assert.match(workflow, /-f all=true/);
  assert.doesNotMatch(workflow, /group: qodo-marketplaces-\$\{\{ needs\.plan\.outputs\.tag \}\}/);
  assert.equal((workflow.match(/plan-marketplace-auto-start\.mjs/g) ?? []).length, 2);
  assert.doesNotMatch(workflow, /PRIVATE_KEY|repository_dispatch/);

  const ship = readFileSync(fileURLToPath(new URL('../.github/workflows/ship-marketplaces.yml', import.meta.url)), 'utf8');
  assert.match(ship, /environment:\n\s+name: marketplace-/);
});

test('enqueues an immutable release only after its compatibility pointer is live', async () => {
  const plan = await planMarketplaceAutoStart({
    requestedTag: 'v1.0.10',
    githubApi: 'https://github.test',
    versionUrl: 'https://distribution.test/version.json',
    fetchImpl: fakeFetch(),
  });

  assert.deepEqual(
    {
      tag: plan.tag,
      sourceCommit: plan.sourceCommit,
      compatibilityVerified: plan.compatibilityVerified,
      needed: plan.needed,
    },
    { tag: 'v1.0.10', sourceCommit: sha, compatibilityVerified: true, needed: true },
  );
});

test('does not enqueue the same marketplace release twice', async () => {
  const run = {
    id: 42,
    display_title: 'Ship marketplaces v1.0.10',
    status: 'in_progress',
    conclusion: null,
    html_url: 'https://github.test/run/42',
    head_branch: 'main',
  };
  const plan = await planMarketplaceAutoStart({
    githubApi: 'https://github.test',
    versionUrl: 'https://distribution.test/version.json',
    fetchImpl: fakeFetch({ runs: [run] }),
  });

  assert.equal(plan.needed, false);
  assert.equal(plan.existingRun.id, 42);
});

test('finds an earlier workflow run beyond the first API page', async () => {
  const page = Array.from({ length: 100 }, (_, id) => ({
    id,
    display_title: `Ship marketplaces v0.9.${id}`,
    head_branch: 'main',
  }));
  const existing = {
    id: 101,
    display_title: 'Ship marketplaces v1.0.10',
    head_branch: 'main',
    status: 'completed',
  };
  const fetchImpl = async (input) => {
    const url = String(input);
    if (url.endsWith('/version.json')) return response({ skills: skillsPointer() });
    if (url.endsWith('/qodo-skills-index.json')) return new Response(index);
    if (url.endsWith('/qodo-skills-index.json.sha256')) return new Response(digest(index));
    if (url.endsWith('/qodo-cli-managed-bundle.json')) return new Response(bundle);
    if (url.endsWith('/qodo-cli-managed-bundle.json.sha256')) return new Response(digest(bundle));
    if (url.includes('/assets/')) return new Response(assetBodies[url.split('/').at(-1)]);
    if (url.includes('/releases/tags/')) return response(release);
    if (url.includes('/commits/')) return response({ sha });
    if (url.includes('/actions/workflows/')) {
      return response({ workflow_runs: Number(new URL(url).searchParams.get('page')) === 1 ? page : [existing] });
    }
    throw new Error(`unexpected request: ${url}`);
  };

  const plan = await planMarketplaceAutoStart({
    githubApi: 'https://github.test',
    versionUrl: 'https://distribution.test/version.json',
    fetchImpl,
  });

  assert.equal(plan.needed, false);
  assert.equal(plan.existingRun.id, 101);
});

test('ignores a same-title run from a feature branch', async () => {
  const plan = await planMarketplaceAutoStart({
    githubApi: 'https://github.test',
    versionUrl: 'https://distribution.test/version.json',
    fetchImpl: fakeFetch({
      runs: [{ id: 42, display_title: 'Ship marketplaces v1.0.10', head_branch: 'feature' }],
    }),
  });
  assert.equal(plan.needed, true);
});

test('rejects a compatibility asset that does not match its published checksum', async () => {
  await assert.rejects(
    planMarketplaceAutoStart({
      githubApi: 'https://github.test',
      versionUrl: 'https://distribution.test/version.json',
      fetchImpl: fakeFetch({ corruptIndex: true }),
    }),
    /checksum mismatch/,
  );
});

test('rejects marketplace rollback below the highest default-branch release', async () => {
  await assert.rejects(
    planMarketplaceAutoStart({
      githubApi: 'https://github.test',
      versionUrl: 'https://distribution.test/version.json',
      fetchImpl: fakeFetch({
        runs: [{
          id: 43,
          display_title: 'Ship marketplaces v999999999999999999999.0.0',
          head_branch: 'main',
          conclusion: 'success',
        }],
      }),
    }),
    /refusing marketplace rollback/,
  );
});

test('does not let an invalid failed future dispatch poison the rollback watermark', async () => {
  const plan = await planMarketplaceAutoStart({
    githubApi: 'https://github.test',
    versionUrl: 'https://distribution.test/version.json',
    fetchImpl: fakeFetch({
      runs: [{ id: 44, display_title: 'Ship marketplaces v999.0.0', head_branch: 'main', conclusion: 'failure' }],
    }),
  });
  assert.equal(plan.watermark, null);
  assert.equal(plan.needed, true);
});

test('rejects production bytes that differ from the immutable release asset', async () => {
  const altered = Buffer.from(JSON.stringify({ schemaVersion: 2, packageVersion: '1.0.10', sourceCommit: sha, drift: true }));
  const fetchImpl = fakeFetch();
  await assert.rejects(
    planMarketplaceAutoStart({
      githubApi: 'https://github.test',
      versionUrl: 'https://distribution.test/version.json',
      fetchImpl: async (input, init) => {
        if (String(input).includes('/assets/qodo-skills-index.json')) return new Response(altered);
        return fetchImpl(input, init);
      },
    }),
    /differs from immutable release/,
  );
});

test('rejects a requested release before its production compatibility pointer advances', async () => {
  await assert.rejects(
    planMarketplaceAutoStart({
      requestedTag: 'v1.0.11',
      githubApi: 'https://github.test',
      versionUrl: 'https://distribution.test/version.json',
      fetchImpl: fakeFetch(),
    }),
    /is not production-ready/,
  );
});

test('rejects mutable release metadata', async () => {
  await assert.rejects(
    planMarketplaceAutoStart({
      githubApi: 'https://github.test',
      versionUrl: 'https://distribution.test/version.json',
      fetchImpl: fakeFetch({ releaseBody: { ...release, immutable: false } }),
    }),
    /not published, stable, and immutable/,
  );
});

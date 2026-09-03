import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { planMarketplaceAutoStart } from '../scripts/plan-marketplace-auto-start.mjs';

const sha = 'b'.repeat(40);
const release = { tag_name: 'v1.0.10', draft: false, prerelease: false, immutable: true };

function response(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function fakeFetch({ publicTag = 'v1.0.10', runs = [], releaseBody = release } = {}) {
  return async (input) => {
    const url = String(input);
    if (url.endsWith('/version.json')) return response({ skills: { releaseTag: publicTag } });
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
    { tag: plan.tag, sourceCommit: plan.sourceCommit, needed: plan.needed },
    { tag: 'v1.0.10', sourceCommit: sha, needed: true },
  );
});

test('does not enqueue the same marketplace release twice', async () => {
  const run = {
    id: 42,
    display_title: 'Ship marketplaces v1.0.10',
    status: 'in_progress',
    conclusion: null,
    html_url: 'https://github.test/run/42',
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
  }));
  const existing = { id: 101, display_title: 'Ship marketplaces v1.0.10', status: 'completed' };
  const fetchImpl = async (input) => {
    const url = String(input);
    if (url.endsWith('/version.json')) return response({ skills: { releaseTag: 'v1.0.10' } });
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

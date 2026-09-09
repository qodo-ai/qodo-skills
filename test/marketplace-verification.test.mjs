import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { planMarketplaceVerification } from '../scripts/plan-marketplace-verification.mjs';
import { checkVisibility, visibilitySummary } from '../scripts/verify-marketplace-visibility.mjs';
import { verifyClaudeDocument, verifyKiroDocument } from '../scripts/marketplace-release.mjs';

const sha = 'a'.repeat(40);
const contract = JSON.parse(readFileSync(new URL('../distribution/marketplaces.json', import.meta.url), 'utf8'));
const run = (id, tag, overrides = {}) => ({
  id, run_attempt: 1, head_branch: 'main', event: 'workflow_dispatch', status: 'completed',
  conclusion: 'success', display_title: `Ship marketplaces ${tag}`, ...overrides,
});
const job = (provider, overrides = {}) => ({
  name: `ship-provider (${provider})`, status: 'completed', conclusion: 'success', ...overrides,
});

function fixture({ runs = [], jobs = {}, release = {}, extra = {} } = {}) {
  const requests = [];
  const fetchImpl = async (url, options) => {
    assert.equal(options.method, undefined, 'observation must only perform GET requests');
    requests.push(url);
    const path = new URL(url).pathname;
    let result;
    if (url in extra) result = extra[url];
    else if (path.endsWith('/workflows/ship-marketplaces.yml/runs')) result = { workflow_runs: runs };
    else if (path.endsWith('/jobs')) {
      const match = /\/runs\/(\d+)\/attempts\/(\d+)\/jobs$/.exec(path);
      assert.ok(match, 'job evidence must be attempt-specific');
      result = { jobs: jobs[`${match[1]}/${match[2]}`] ?? [] };
    } else if (path.includes('/releases/tags/')) {
      result = { tag_name: path.split('/').at(-1), immutable: true, draft: false, prerelease: false, ...release };
    } else if (path.includes('/commits/')) result = { sha };
    else throw new Error(`Unexpected URL ${url}`);
    return Response.json(result);
  };
  return { fetchImpl, requests };
}

test('selects the highest successful tag separately for each provider, not a newer unshipped release', async () => {
  const fake = fixture({
    runs: [run(40, 'v2.0.0'), run(30, 'v2.0.3'), run(20, 'v2.0.2'),
      run(60, 'v2.0.5', { conclusion: 'failure' }),
      run(70, 'v2.0.6', { head_branch: 'feature' }),
      run(80, 'v2.0.7', { status: 'in_progress' })],
    jobs: { '40/1': [job('claude'), job('kiro')], '30/1': [job('claude'), job('kiro', { conclusion: 'skipped' })],
      '20/1': [job('kiro')] },
  });
  const plan = await planMarketplaceVerification(fake);
  assert.deepEqual(plan.include.map(({ provider, tag }) => [provider, tag]), [['claude', 'v2.0.3'], ['kiro', 'v2.0.2']]);
  assert.deepEqual(plan.unshipped, []);
  assert.ok(plan.include.every((entry) => entry.commit === sha));
  assert.ok(!fake.requests.some((url) => url.includes('/releases/latest') || url.includes('/runs/40/')));
});

test('successful Codex-only shipping cannot claim Claude or Kiro shipped', async () => {
  const plan = await planMarketplaceVerification(fixture({
    runs: [run(1, 'v2.0.2')], jobs: { '1/1': [job('codex'), job('claude', { conclusion: 'skipped' })] },
  }));
  assert.deepEqual(plan.include, []);
  assert.deepEqual(plan.unshipped, ['claude', 'kiro']);
});

test('supports successful pre-split runs and binds jobs to the successful rerun attempt', async () => {
  const fake = fixture({ runs: [run(1, 'v2.0.2', { run_attempt: 3 })],
    jobs: { '1/1': [job('kiro')], '1/3': [job('claude', { name: 'verify-provider-visible (claude)' })] } });
  const plan = await planMarketplaceVerification(fake);
  assert.deepEqual(plan.include.map((entry) => entry.provider), ['claude']);
  assert.ok(plan.include[0].shippingRun.endsWith('/1/attempts/3'));
  assert.deepEqual(plan.unshipped, ['kiro']);
});

test('finds provider targets on later workflow-run and job pages', async () => {
  const prefix = 'https://api.github.com/repos/qodo-ai/qodo-skills';
  const runs = Array.from({ length: 100 }, (_, i) => run(i + 10, 'v2.0.3', { conclusion: 'failure' }));
  const fake = fixture({ runs, jobs: { '1/1': Array.from({ length: 100 }, () => job('codex')) }, extra: {
    [`${prefix}/actions/workflows/ship-marketplaces.yml/runs?event=workflow_dispatch&branch=main&status=success&per_page=100&page=2`]:
      { workflow_runs: [run(1, 'v2.0.2')] },
    [`${prefix}/actions/runs/1/attempts/1/jobs?per_page=100&page=2`]: { jobs: [job('claude'), job('kiro')] },
  } });
  assert.equal((await planMarketplaceVerification(fake)).include.length, 2);
});

test('manual recovery checks an immutable tag without inventing successful shipping evidence', async () => {
  const fake = fixture();
  const plan = await planMarketplaceVerification({ ...fake, requestedTag: 'v2.0.2' });
  assert.equal(plan.include.length, 2);
  assert.ok(plan.include.every((entry) => entry.shippingRun === null && entry.tag === 'v2.0.2'));
  assert.equal(fake.requests.length, 2, 'resolve the shared release once without querying runs');
});

test('rejects unsafe tag input and unpublished, mutable, or prerelease targets', async () => {
  for (const requestedTag of ['main', 'v2.0.2;echo fail', 'v2.0.2\n', 'v02.0.2']) {
    await assert.rejects(planMarketplaceVerification({ ...fixture(), requestedTag }), /invalid stable skills tag/);
  }
  for (const release of [{ immutable: false }, { draft: true }, { prerelease: true }, { tag_name: 'v2.0.1' }]) {
    await assert.rejects(planMarketplaceVerification({ ...fixture({ release }), requestedTag: 'v2.0.2' }), /published, stable, immutable/);
  }
});

test('API failures and malformed job responses fail planning instead of silently dropping a provider', async () => {
  await assert.rejects(planMarketplaceVerification({ fetchImpl: async () => new Response('', { status: 503 }) }), /HTTP 503/);
  const url = 'https://api.github.com/repos/qodo-ai/qodo-skills/actions/runs/1/attempts/1/jobs?per_page=100&page=1';
  await assert.rejects(planMarketplaceVerification(fixture({ runs: [run(1, 'v2.0.2')], extra: { [url]: {} } })), /invalid shipping job list/);
});

test('public visibility stays false until both Claude pins and paths match the release', async () => {
  const selected = contract.providers.find((entry) => entry.id === 'claude');
  const document = {
    renames: { 'qodo-skills': 'qodo' },
    plugins: selected.listings.map((listing) => ({ name: listing.id, source: {
      source: 'git-subdir', url: 'https://github.com/qodo-ai/qodo-skills.git',
      ref: 'main', path: listing.sourcePath, sha,
    } })),
  };
  const context = { tag: 'v2.0.2', commit: sha };
  const verify = async (_, target, config) => verifyClaudeDocument(document, target, config);
  assert.equal((await checkVisibility('claude', context, contract, verify)).state, 'provider-visible');
  document.plugins[1].source.sha = 'b'.repeat(40);
  const stale = await checkVisibility('claude', context, contract, verify);
  assert.equal(stale.state, 'unverified');
  assert.match(stale.error, /qodo-standards: provider SHA/);
  document.plugins[1].source.sha = sha;
  document.plugins[0].source.path = '.';
  assert.equal((await checkVisibility('claude', context, contract, verify)).state, 'unverified');
});

test('uses the target release contract instead of assuming the current checkout contract', async () => {
  const released = structuredClone(contract);
  const selected = released.providers.find((entry) => entry.id === 'kiro');
  selected.sourceRef = 'marketplace-kiro-released';
  const document = JSON.stringify(selected.listings.map((entry) => ({
    name: entry.id, pathInRepo: entry.sourcePath, repositoryBranch: selected.sourceRef,
    repositoryCloneUrl: 'git@github.com:qodo-ai/qodo-skills.git',
    repositoryUrl: `https://github.com/qodo-ai/qodo-skills/tree/${selected.sourceRef}/${entry.sourcePath}`,
  })));
  const result = await checkVisibility('kiro', { tag: 'v2.0.2', commit: sha }, released,
    async (_, context, config) => verifyKiroDocument(document, context, config));
  assert.equal(result.state, 'provider-visible');
  await assert.rejects(checkVisibility('codex', {}, contract), /Missing verifiable/);
});

test('observer is independent, read-only, bounded, and cannot turn mismatches green', () => {
  const workflow = readFileSync(new URL('../.github/workflows/verify-marketplace-visibility.yml', import.meta.url), 'utf8');
  assert.match(workflow, /workflow_run:[\s\S]*workflows: \[Ship marketplaces\]/);
  assert.match(workflow, /cron: '8,23,38,53 \* \* \* \*'/);
  assert.match(workflow, /actions: read\s+contents: read/);
  assert.match(workflow, /fail-fast: false/);
  assert.match(workflow, /timeout-minutes: 5/);
  assert.doesNotMatch(workflow, /continue-on-error|environment:|secrets\.|contents: write|marketplace-release-lock|create-github-app-token/);
  assert.match(workflow, /RELEASE_CATALOG: release-source\/distribution\/marketplaces.json/);
});

test('a visible moving branch does not claim it matches the reference release commit', async () => {
  const observed = 'b'.repeat(40);
  const result = await checkVisibility('kiro', { tag: 'v2.0.4', commit: sha }, contract,
    async () => [{ id: 'qodo', branch: 'main', commit: observed }, { id: 'qodo-standards', branch: 'main', commit: observed }]);
  assert.equal(result.state, 'provider-visible');
  assert.equal(result.verification, 'branch-source');
  const summary = visibilitySummary(result);
  assert.ok(summary.includes(observed));
  assert.match(summary, /Reference release:.*v2.0.4/);
  assert.match(summary, /tracks `main`/);
  assert.doesNotMatch(summary, /Every configured listing resolves to this release/);
});

test('shipping rejects an old Kiro contract after legacy branch promotion is removed', () => {
  const workflow = readFileSync(new URL('../.github/workflows/ship-marketplaces.yml', import.meta.url), 'utf8');
  const guard = workflow.match(/name: Require the Kiro main-source contract[\s\S]*?<<'NODE'\n([\s\S]*?)\n\s+NODE/)[1];
  const temp = mkdtempSync(join(tmpdir(), 'kiro-shipping-contract-'));
  try {
    mkdirSync(join(temp, 'distribution'));
    const candidate = structuredClone(contract);
    for (const [mode, sourceRef, status] of [
      ['provider-tracked-branch', 'main', 0],
      ['protected-release-branch', 'marketplace-kiro', 1],
      ['provider-tracked-branch', 'other', 1],
    ]) {
      Object.assign(candidate.providers.find((entry) => entry.id === 'kiro'), { mode, sourceRef });
      writeFileSync(join(temp, 'distribution/marketplaces.json'), JSON.stringify(candidate));
      const result = spawnSync(process.execPath, ['--input-type=module'], { input: guard, cwd: temp, encoding: 'utf8' });
      assert.equal(result.status, status, result.stderr);
      if (status) assert.match(result.stderr, /Select a release whose Kiro contract tracks main/);
    }
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});

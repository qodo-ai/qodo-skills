/** Exercise atomic marketplace release admission without network access. */
import assert from 'node:assert/strict';
import {
  acquireReleaseLock,
  releaseLockContext,
  releaseReleaseLock,
} from './marketplace-release-lock.mjs';

const repository = 'qodo-ai/qodo-skills';
const commit = '0123456789abcdef0123456789abcdef01234567';
const lockRefPath = `/repos/${repository}/git/ref/heads/qodo-marketplace-release-lock`;
const updateRefPath = `/repos/${repository}/git/refs/heads/qodo-marketplace-release-lock`;

function context(runId, releaseTag) {
  return { repository, runId, releaseTag, commit };
}

function fakeGitHub() {
  const state = {
    ref: undefined,
    commits: new Map([[commit, {
      sha: commit,
      message: 'release source',
      tree: { sha: 'f'.repeat(40) },
      parents: [],
    }]]),
    runs: new Map(),
    nextCommit: 1,
    conflictStatus: 422,
  };
  const api = async ({ method, path, body }) => {
    if (method === 'GET' && path === lockRefPath) {
      if (!state.ref) throw Object.assign(new Error('not found'), { status: 404 });
      return { object: { type: 'commit', sha: state.ref } };
    }
    if (method === 'GET' && path.startsWith(`/repos/${repository}/git/commits/`)) {
      const value = state.commits.get(path.split('/').at(-1));
      if (!value) throw Object.assign(new Error('not found'), { status: 404 });
      return value;
    }
    if (method === 'POST' && path === `/repos/${repository}/git/commits`) {
      const sha = state.nextCommit.toString(16).padStart(40, 'a');
      const value = {
        sha,
        message: body.message,
        tree: { sha: body.tree },
        parents: body.parents.map((parent) => ({ sha: parent })),
      };
      state.commits.set(sha, value);
      state.nextCommit += 1;
      return value;
    }
    if (method === 'POST' && path === `/repos/${repository}/git/refs`) {
      if (state.ref) throw Object.assign(new Error('already exists'), { status: state.conflictStatus });
      assert.equal(body.ref, 'refs/heads/qodo-marketplace-release-lock');
      state.ref = body.sha;
      return {};
    }
    if (method === 'PATCH' && path === updateRefPath) {
      assert.equal(body.force, false);
      const candidate = state.commits.get(body.sha);
      if (!candidate || candidate.parents[0]?.sha !== state.ref) {
        throw Object.assign(new Error('not a fast forward'), { status: state.conflictStatus });
      }
      state.ref = body.sha;
      return {};
    }
    if (method === 'GET' && path.startsWith(`/repos/${repository}/actions/runs/`)) {
      const run = state.runs.get(path.split('/').at(-1));
      if (!run) throw Object.assign(new Error('not found'), { status: 404 });
      return run;
    }
    throw new Error(`Unexpected fake GitHub request: ${method} ${path}`);
  };
  return { api, state };
}

function currentOwner(fake) {
  const record = fake.state.commits.get(fake.state.ref);
  return JSON.parse(record.message.split('\n').slice(1).join('\n'));
}

assert.deepEqual(releaseLockContext({
  GITHUB_REPOSITORY: repository,
  GITHUB_RUN_ID: '17',
  RELEASE_TAG: 'v1.0.5',
  GITHUB_SHA: commit,
}), context('17', 'v1.0.5'));
assert.throws(() => releaseLockContext({}), /GITHUB_REPOSITORY is missing or invalid/);

const first = fakeGitHub();
const owner = await acquireReleaseLock(context('17', 'v1.0.5'), first.api, new Date('2026-08-26T00:00:00Z'));
assert.deepEqual(owner, {
  state: 'active',
  runId: '17',
  releaseTag: 'v1.0.5',
  createdAt: '2026-08-26T00:00:00.000Z',
});
assert.equal((await acquireReleaseLock(context('17', 'v1.0.5'), first.api)).runId, '17');
first.state.runs.set('17', { status: 'in_progress', html_url: 'https://example.test/runs/17' });
await assert.rejects(
  acquireReleaseLock(context('18', 'v1.0.6'), first.api),
  /v1\.0\.5 is still active: https:\/\/example\.test\/runs\/17/,
);
assert.equal(await releaseReleaseLock(context('18', 'v1.0.6'), first.api), false);
assert.equal(await releaseReleaseLock(context('17', 'v1.0.5'), first.api), true);
assert.equal(currentOwner(first).state, 'released');

const stale = fakeGitHub();
await acquireReleaseLock(context('21', 'v1.0.5'), stale.api);
stale.state.runs.set('21', { status: 'completed', html_url: 'https://example.test/runs/21' });
const replacement = await acquireReleaseLock(context('22', 'v1.0.6'), stale.api);
assert.equal(replacement.runId, '22');
assert.equal(currentOwner(stale).releaseTag, 'v1.0.6');

// A deleted owner run is stale; authorization and transport failures still fail closed.
const deletedOwner = fakeGitHub();
await acquireReleaseLock(context('23', 'v1.0.5'), deletedOwner.api);
const deletedReplacement = await acquireReleaseLock(context('24', 'v1.0.6'), deletedOwner.api);
assert.equal(deletedReplacement.runId, '24');
assert.equal(currentOwner(deletedOwner).releaseTag, 'v1.0.6');
const lookupFailure = fakeGitHub();
await acquireReleaseLock(context('25', 'v1.0.5'), lookupFailure.api);
const lookupFailureApi = async (request) => {
  if (request.method === 'GET' && request.path.endsWith('/actions/runs/25')) {
    throw Object.assign(new Error('forbidden'), { status: 403 });
  }
  return lookupFailure.api(request);
};
await assert.rejects(acquireReleaseLock(context('26', 'v1.0.6'), lookupFailureApi), /forbidden/);

// Initial creation is atomic: a contender that loses POST /git/refs never proceeds.
const creationRace = fakeGitHub();
creationRace.state.conflictStatus = 409;
const creationApi = creationRace.api;
let injectInitialWinner = true;
const racingCreationApi = async (request) => {
  if (injectInitialWinner && request.method === 'POST' && request.path.endsWith('/git/refs')) {
    injectInitialWinner = false;
    await acquireReleaseLock(context('31', 'v1.0.7'), creationApi);
  }
  return creationApi(request);
};
await assert.rejects(
  acquireReleaseLock(context('30', 'v1.0.6'), racingCreationApi),
  /v1\.0\.7 acquired the release lock first/,
);

// Stale takeover is compare-and-swap: only one child can fast-forward the observed parent.
const takeoverRace = fakeGitHub();
await acquireReleaseLock(context('40', 'v1.0.5'), takeoverRace.api);
takeoverRace.state.runs.set('40', { status: 'completed' });
const takeoverApi = takeoverRace.api;
let injectTakeoverWinner = true;
const racingTakeoverApi = async (request) => {
  if (injectTakeoverWinner && request.method === 'PATCH' && request.path === updateRefPath) {
    injectTakeoverWinner = false;
    await acquireReleaseLock(context('42', 'v1.0.7'), takeoverApi);
  }
  return takeoverApi(request);
};
await assert.rejects(
  acquireReleaseLock(context('41', 'v1.0.6'), racingTakeoverApi),
  /v1\.0\.7 acquired the release lock first/,
);
assert.equal(currentOwner(takeoverRace).runId, '42');

// Old-owner cleanup cannot release a replacement that won the same observed parent.
const cleanupRace = fakeGitHub();
await acquireReleaseLock(context('50', 'v1.0.5'), cleanupRace.api);
cleanupRace.state.runs.set('50', { status: 'completed' });
const cleanupApi = cleanupRace.api;
let injectReplacement = true;
const racingCleanupApi = async (request) => {
  if (injectReplacement && request.method === 'PATCH' && request.path === updateRefPath) {
    injectReplacement = false;
    await acquireReleaseLock(context('51', 'v1.0.6'), cleanupApi);
  }
  return cleanupApi(request);
};
assert.equal(await releaseReleaseLock(context('50', 'v1.0.5'), racingCleanupApi), false);
assert.equal(currentOwner(cleanupRace).state, 'active');
assert.equal(currentOwner(cleanupRace).runId, '51');

console.log('Marketplace release lock tests passed.');

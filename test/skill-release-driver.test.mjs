import assert from 'node:assert/strict';
import test from 'node:test';
import { releaseBranch, releaseMarker, runSkillRelease } from '../scripts/run-skill-release.mjs';

function fixture({ existing = false } = {}) {
  const base = 'a'.repeat(40), head = 'b'.repeat(40), tree = 'c'.repeat(40);
  const repository = 'qodo-ai/qodo-skills';
  const pr = { number: 123, state: 'open', user: { login: 'github-actions[bot]' }, body: releaseMarker,
    base: { ref: 'main', repo: { full_name: repository } },
    head: { ref: releaseBranch, sha: head, repo: { full_name: repository } } };
  const state = { main: base, branch: existing ? head : null, prs: existing ? [pr] : [], commitTree: 'd'.repeat(40) };
  const calls = [];
  const options = { repository, base, log() {},
    run(command, args) {
      calls.push({ command, args });
      if (command === 'git' && args[0] === 'rev-parse') return args[1] === 'HEAD' ? base : tree;
      return '';
    },
    plan() { return { baseline: 'e'.repeat(40), pending: true, summary: 'Update wisdom.' }; },
    prepare() { return { version: '2.0.5' }; },
    async request(path, body, method) {
      calls.push({ path, body, method });
      if (body) return { number: 123, html_url: 'https://github.com/qodo-ai/qodo-skills/pull/123' };
      if (path.endsWith('/git/ref/heads/main')) return { object: { sha: state.main } };
      if (path.endsWith(`/git/ref/heads/${releaseBranch}`)) return state.branch ? { object: { sha: state.branch } } : null;
      if (path.includes('pulls?state=open')) return structuredClone(state.prs);
      if (path.includes('pulls?state=closed')) return [];
      if (path.endsWith('/pulls/123')) return structuredClone(pr);
      if (path.includes('/git/commits/')) return { tree: { sha: state.commitTree }, parents: [{ sha: base }] };
      throw new Error(`Unexpected request ${path}`);
    } };
  return { options, state, calls, pr, base, head, tree,
    pushes: () => calls.filter((c) => c.command === 'git' && c.args[0] === 'push'),
    writes: () => calls.filter((c) => c.body) };
}

test('creates a single release PR without writing contributor branches or main', async () => {
  const f = fixture();
  await runSkillRelease(f.options);
  assert.deepEqual(f.pushes()[0].args, ['push', `--force-with-lease=refs/heads/${releaseBranch}:`, 'origin', `HEAD:refs/heads/${releaseBranch}`]);
  assert.equal(f.writes().length, 1);
  assert.equal(f.writes()[0].body.head, releaseBranch);
  assert.equal(f.writes()[0].body.base, 'main');
  assert.match(f.writes()[0].body.body, /Approve workflows to run/);
  assert.ok(f.calls.some((c) => c.args?.[0] === 'scripts/validate-diff.mjs'));
});

test('refreshes only the inspected bot-owned branch with an explicit lease', async () => {
  const f = fixture({ existing: true });
  await runSkillRelease(f.options);
  assert.ok(f.pushes()[0].args.includes(`--force-with-lease=refs/heads/${releaseBranch}:${f.head}`));
  assert.equal(f.writes()[0].method, 'PATCH');
  assert.ok(f.writes()[0].path.endsWith('/pulls/123'));
});

test('an identical release tree on the same main commit is not pushed again', async () => {
  const f = fixture({ existing: true });
  f.state.commitTree = f.tree;
  await runSkillRelease(f.options);
  assert.equal(f.pushes().length, 0);
});

test('complete reverts close the open bot PR without rewriting its branch', async () => {
  const f = fixture({ existing: true });
  f.options.prepare = () => null;
  await runSkillRelease(f.options);
  assert.equal(f.pushes().length, 0);
  assert.deepEqual(f.writes().map((c) => c.body), [{ state: 'closed' }]);
});

test('a merged release with no pending changes does not start a preparation loop', async () => {
  const f = fixture();
  f.options.prepare = () => null;
  await runSkillRelease(f.options);
  assert.equal(f.pushes().length, 0);
  assert.equal(f.writes().length, 0);
});

test('stale workflow completions are skipped and ref races never publish', async () => {
  const stale = fixture();
  stale.state.main = 'f'.repeat(40);
  await runSkillRelease(stale.options);
  assert.equal(stale.pushes().length, 0);
  for (const target of ['main', 'branch']) {
    const f = fixture({ existing: true });
    f.options.prepare = () => { f.state[target] = 'f'.repeat(40); return { version: '2.0.5' }; };
    await assert.rejects(runSkillRelease(f.options), /changed; no release PR update/);
    assert.equal(f.pushes().length + f.writes().length, 0);
  }
});

test('unrecognized PRs or orphan branches cannot be overwritten', async () => {
  for (const kind of ['author', 'marker', 'branch', 'orphan']) {
    const f = fixture({ existing: true });
    if (kind === 'author') f.pr.user.login = 'contributor';
    if (kind === 'marker') f.pr.body = 'unrelated work';
    if (kind === 'branch') f.pr.head.ref = 'contributor/skills';
    if (kind === 'orphan') f.state.prs = [];
    await assert.rejects(runSkillRelease(f.options), /unrecognized|no matching bot-owned PR/);
    assert.equal(f.pushes().length + f.writes().length, 0);
  }
});

test('a PR closed during preparation or a failed branch lease stops before PR mutation', async () => {
  const f = fixture({ existing: true });
  f.options.prepare = () => { f.pr.state = 'closed'; return { version: '2.0.5' }; };
  await assert.rejects(runSkillRelease(f.options), /changed or closed/);
  assert.equal(f.pushes().length + f.writes().length, 0);
  const race = fixture({ existing: true });
  const run = race.options.run;
  race.options.run = (command, args, options) => {
    if (args[0] === 'push') throw new Error('lease rejected');
    return run(command, args, options);
  };
  await assert.rejects(runSkillRelease(race.options), /lease rejected/);
  assert.equal(race.writes().length, 0);
});

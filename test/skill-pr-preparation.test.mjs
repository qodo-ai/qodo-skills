import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { appendFileSync, cpSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { prepareSkillPullRequest } from '../scripts/prepare-skill-pr.mjs';
import { runPreparation } from '../scripts/run-skill-pr-preparation.mjs';
import { incrementVersion } from '../scripts/prepare-release.mjs';

const source = dirname(dirname(fileURLToPath(import.meta.url)));
const wisdom = 'skills/qodo-codebase-wisdom/SKILL.md';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'skill-pr-test-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const name of readdirSync(source)) {
    if (name !== '.git' && name !== 'node_modules') cpSync(join(source, name), join(root, name), { recursive: true });
  }
  const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  git('init', '--quiet');
  for (const [key, value] of Object.entries({ 'user.name': 'Test', 'user.email': 'test@example.com',
    'commit.gpgsign': 'false', 'core.autocrlf': 'false', 'core.safecrlf': 'false' })) git('config', key, value);
  const commit = (message) => { git('add', '--all'); git('commit', '--quiet', '-m', message); return git('rev-parse', 'HEAD'); };
  const base = commit('base');
  const edit = (path = wisdom, text = '\nCite evidence for each conclusion.\n') => appendFileSync(join(root, path), text);
  const prepare = (head, targetBase = base) => {
    git('reset', '--hard', targetBase);
    git('clean', '-fd');
    return prepareSkillPullRequest({ root, base: targetBase, head, number: 123 });
  };
  return { root, git, commit, base, edit, prepare };
}

test('browser-only edit prepares all packages, validates, and remains idempotent after more edits', (t) => {
  const f = fixture(t);
  const prior = JSON.parse(readFileSync(join(f.root, 'distribution/catalog.json')));
  f.edit();
  const authored = f.commit('edit in GitHub');
  const result = f.prepare(authored);
  assert.equal(result.status, 'prepared');
  assert.equal(result.version, incrementVersion(prior.package.version, 'patch'));
  assert.ok(result.additions.some(({ path }) => path === 'kiro-power/skills/qodo-codebase-wisdom/SKILL.md'));
  assert.ok(result.additions.some(({ path }) => path === 'codex-packages/qodo/skills/qodo-codebase-wisdom/SKILL.md'));
  assert.ok(result.additions.some(({ path }) => path === `releases/v${result.version}.json`));
  // Model the API commit exactly: append only these additions on the contributor's head.
  f.git('reset', '--hard', authored);
  f.git('clean', '-fd');
  for (const { path, contents } of result.additions) {
    mkdirSync(dirname(join(f.root, path)), { recursive: true });
    writeFileSync(join(f.root, path), Buffer.from(contents, 'base64'));
  }
  const prepared = f.commit('bot commit');
  execFileSync(process.execPath, ['scripts/validate-diff.mjs', f.base], { cwd: f.root });
  cpSync(join(source, 'node_modules'), join(f.root, 'node_modules'), { recursive: true });
  for (const args of [['scripts/validate.mjs'], ['scripts/build-release-index.mjs', '--check'],
    ['scripts/build-cli-managed-bundle.mjs', '--check']]) {
    execFileSync(process.execPath, args, { cwd: f.root, stdio: 'pipe' });
  }
  const again = f.prepare(prepared);
  assert.equal(again.status, 'unchanged');
  assert.deepEqual(again.additions, []);
  f.git('reset', '--hard', prepared);
  f.edit(wisdom, '\nExplain remaining uncertainty.\n');
  const updated = f.commit('second browser edit');
  const refreshed = f.prepare(updated);
  assert.equal(refreshed.status, 'prepared');
  assert.equal(refreshed.version, result.version);
  const skill = refreshed.additions.find(({ path }) => path === 'kiro-power/skills/qodo-codebase-wisdom/SKILL.md');
  assert.match(Buffer.from(skill.contents, 'base64').toString(), /Explain remaining uncertainty/);
});

test('multiple existing skills share one release and CRLF inputs remain supported', (t) => {
  const f = fixture(t);
  f.edit();
  const second = 'skills/qodo-review/SKILL.md';
  f.edit(second);
  writeFileSync(join(f.root, wisdom), readFileSync(join(f.root, wisdom), 'utf8').replace(/\r?\n/g, '\r\n'));
  const result = f.prepare(f.commit('two edits'));
  const release = JSON.parse(readFileSync(join(f.root, `releases/v${result.version}.json`)));
  assert.deepEqual(release.skills.map(({ name }) => name).sort(), ['qodo-codebase-wisdom', 'qodo-review']);
});

test('partial and complete reversions reconcile versions, projections and the new release record', (t) => {
  const f = fixture(t);
  const second = 'skills/qodo-review/SKILL.md';
  f.edit();
  f.edit(second);
  const original = f.prepare(f.commit('two skills'));
  const bot = f.commit('prepared release');
  const revertBody = (path) => {
    const baseText = f.git('show', `${f.base}:${path}`);
    const current = readFileSync(join(f.root, path), 'utf8');
    const versionLine = current.match(/^  version: .+$/m)[0];
    writeFileSync(join(f.root, path), `${baseText.replace(/^  version: .+$/m, versionLine)}\n`);
  };
  revertBody(wisdom);
  const partial = f.prepare(f.commit('revert one skill body'));
  assert.equal(partial.status, 'prepared');
  assert.equal(partial.version, original.version);
  assert.equal(readFileSync(join(f.root, wisdom), 'utf8').trim(), f.git('show', `${f.base}:${wisdom}`));
  const release = JSON.parse(readFileSync(join(f.root, `releases/v${partial.version}.json`)));
  assert.deepEqual(release.skills.map(({ name }) => name), ['qodo-review']);
  f.commit('partial reconciliation');
  execFileSync(process.execPath, ['scripts/validate-diff.mjs', f.base], { cwd: f.root });
  // A complete revert after the original two-skill bot commit restores the exact base tree.
  f.git('reset', '--hard', bot);
  revertBody(wisdom);
  revertBody(second);
  const revertedHead = f.commit('revert all instruction bodies');
  const complete = f.prepare(revertedHead);
  assert.equal(complete.status, 'prepared');
  assert.equal(complete.version, null);
  assert.deepEqual(complete.deletions, [{ path: `releases/v${original.version}.json` }]);
  assert.equal(f.git('diff', '--cached', '--name-only', f.base), '');
  // Apply the API payload to the real reverted head and verify that no stale release survives.
  f.git('reset', '--hard', revertedHead);
  for (const { path, contents } of complete.additions) writeFileSync(join(f.root, path), Buffer.from(contents, 'base64'));
  for (const { path } of complete.deletions) rmSync(join(f.root, path));
  f.commit('complete reconciliation');
  assert.equal(f.git('diff', '--name-only', f.base), '');
});

test('PR scripts are neither executed nor overwritten', (t) => {
  const f = fixture(t);
  f.edit();
  writeFileSync(join(f.root, 'scripts/sync-adapters.mjs'), 'throw new Error("UNTRUSTED SCRIPT EXECUTED");\n');
  const result = f.prepare(f.commit('script with skill'));
  assert.equal(result.status, 'skipped');
  assert.match(result.reason, /mixed or structural/);
  assert.equal(f.git('status', '--porcelain'), '');
});

test('preserves dependency and npm script edits instead of treating them as generated version changes', (t) => {
  const f = fixture(t);
  for (const path of ['package.json', 'package-lock.json']) {
    f.git('reset', '--hard', f.base);
    f.edit();
    const value = JSON.parse(readFileSync(join(f.root, path)));
    if (path === 'package.json') value.scripts.check = 'throw-away-author-change';
    else value.packages['node_modules/ajv'].version = '0.0.0';
    writeFileSync(join(f.root, path), JSON.stringify(value));
    assert.match(f.prepare(f.commit('mixed manifest edit')).reason, /non-version changes/);
    assert.equal(f.git('status', '--porcelain'), '');
  }
});

test('new skills, catalog edits, and manually prepared releases remain maintainer-owned', (t) => {
  const f = fixture(t);
  f.edit();
  const catalogPath = join(f.root, 'distribution/catalog.json');
  const original = readFileSync(catalogPath, 'utf8');
  const catalog = JSON.parse(original);
  catalog.skills[0].displayName = 'Changed';
  writeFileSync(catalogPath, JSON.stringify(catalog));
  assert.match(f.prepare(f.commit('metadata')).reason, /Catalog metadata/);
  f.edit();
  execFileSync(process.execPath, ['scripts/prepare-release.mjs', '--summary', 'Intentional minor release',
    '--skill', 'qodo-codebase-wisdom=minor'], { cwd: f.root, stdio: 'pipe' });
  assert.match(f.prepare(f.commit('manual release')).reason, /maintainer-prepared/);
  f.edit();
  mkdirSync(join(f.root, 'skills/qodo-new'));
  writeFileSync(join(f.root, 'skills/qodo-new/SKILL.md'), 'new skill');
  assert.match(f.prepare(f.commit('new skill')).reason, /structural/);
});

test('refuses stale bases and file type changes without reading targets', (t) => {
  const f = fixture(t);
  f.edit();
  const head = f.commit('skill edit');
  f.git('reset', '--hard', f.base);
  appendFileSync(join(f.root, 'README.md'), '\nNew main content.\n');
  const nextBase = f.commit('main moved');
  assert.throws(() => f.prepare(head, nextBase), /Update branch/);
  f.git('reset', '--hard', head);
  f.git('update-index', '--chmod=+x', wisdom);
  f.git('commit', '--quiet', '-m', 'executable skill');
  const executable = f.git('rev-parse', 'HEAD');
  assert.throws(() => f.prepare(executable), /regular non-executable/);
});

test('does not discard edits outside the actual generated files', (t) => {
  const f = fixture(t);
  f.edit();
  writeFileSync(join(f.root, 'kiro-power/extra.txt'), 'authored content');
  assert.throws(() => f.prepare(f.commit('extra generated-root file')), /discard unrelated edits/);
});

function driverFixture() {
  const base = 'a'.repeat(40);
  const head = 'b'.repeat(40);
  const pr = { state: 'open', base: { ref: 'main', sha: base, repo: { full_name: 'qodo-ai/qodo-skills' } },
    head: { ref: 'contributor/edit', sha: head, repo: { full_name: 'qodo-ai/qodo-skills' } } };
  const calls = [];
  const options = { repository: 'qodo-ai/qodo-skills', number: 123, base, log() {},
    run(command, args) { calls.push({ command, args }); return args[0] === 'rev-parse' ? head : ''; },
    prepare() { return { status: 'prepared', version: '2.0.5', additions: [{ path: wisdom, contents: 'dGVzdA==' }] }; },
    async request(path, body) { calls.push({ path, body }); return body
      ? { data: { createCommitOnBranch: { commit: { oid: 'c'.repeat(40), url: 'https://github.com/example/commit' } } } }
      : structuredClone(pr); } };
  return { options, calls, pr, base, head };
}

test('publication uses the exact inspected PR head and only appends the generated commit', async () => {
  const f = driverFixture();
  await runPreparation(f.options);
  const writes = f.calls.filter(({ body }) => body);
  assert.equal(writes.length, 1);
  assert.equal(writes[0].body.variables.input.expectedHeadOid, f.head);
  assert.equal(writes[0].body.variables.input.branch.branchName, f.pr.head.ref);
  assert.ok(f.calls.some(({ args }) => args?.[0] === 'scripts/validate-diff.mjs'));
});

test('publishes complete-revert deletions and can validate the unchanged base tree', async () => {
  const f = driverFixture();
  f.options.prepare = () => ({ status: 'prepared', version: null, additions: [],
    deletions: [{ path: 'releases/v2.0.5.json' }] });
  await runPreparation(f.options);
  const input = f.calls.find(({ body }) => body).body.variables.input;
  assert.deepEqual(input.fileChanges.deletions, [{ path: 'releases/v2.0.5.json' }]);
  assert.match(input.message.headline, /remove reverted/);
  assert.ok(f.calls.some(({ args }) => args?.includes('--allow-empty')));
});

test('forks, closed PRs, changed heads and moved bases cannot publish a commit', async () => {
  for (const change of ['fork', 'closed', 'head', 'base', 'branch']) {
    const f = driverFixture();
    const request = f.options.request;
    let reads = 0;
    f.options.request = async (path, body) => {
      const result = await request(path, body);
      if (!body && ++reads === (change === 'fork' || change === 'closed' ? 1 : 2)) {
        if (change === 'fork') result.head.repo.full_name = 'someone/fork';
        if (change === 'closed') result.state = 'closed';
        if (change === 'head') result.head.sha = 'd'.repeat(40);
        if (change === 'base') result.base.sha = 'e'.repeat(40);
        if (change === 'branch') result.head.ref = 'different';
      }
      return result;
    };
    if (change === 'fork' || change === 'closed') await runPreparation(f.options);
    else await assert.rejects(runPreparation(f.options), /changed/);
    assert.equal(f.calls.filter(({ body }) => body).length, 0, change);
  }
});

import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const reference = readFileSync(join(root, 'skills/qodo-review/references/mcp-local-review.md'), 'utf8');
const cleanEnvironment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^GIT_/i.test(key)));
const parents = new Map();
const recipePaths = new Map();
const gitPath = process.platform === 'win32' ? null
  : execFileSync('/usr/bin/which', ['git'], { encoding: 'utf8' }).trim();
const posixTest = process.platform === 'win32' ? test.skip : test;

function recipe(name) {
  const match = reference.match(new RegExp('```sh ' + name + '\\n([\\s\\S]*?)\\n```'));
  assert.ok(match, `Missing executable recipe ${name}`);
  return match[1];
}

function git(repo, ...args) {
  return execFileSync(gitPath, args, { cwd: repo, env: cleanEnvironment, encoding: 'utf8' }).trim();
}

function fixture(t, objectFormat = 'sha1') {
  const directory = mkdtempSync(join(tmpdir(), 'qodo-mcp-recipe-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const repo = join(directory, 'repo');
  mkdirSync(repo);
  const bin = join(directory, 'bin');
  mkdirSync(bin);
  symlinkSync(gitPath, join(bin, 'git'));
  recipePaths.set(repo, bin);
  git(repo, 'init', '-q', '--initial-branch=topic', `--object-format=${objectFormat}`);
  return { directory, repo };
}

function commit(repo, content, mergeParents = []) {
  const message = 'fixture';
  const parent = parents.has(repo) ? `from ${parents.get(repo)}\n` : '';
  const merges = mergeParents.map((sha) => `merge ${sha}\n`).join('');
  const stream = `commit refs/heads/topic\ncommitter Fixture <fixture@example.test> 1700000000 +0000\ndata ${message.length}\n${message}\n${parent}${merges}M 100644 inline app.py\ndata ${Buffer.byteLength(content)}\n${content}\n\n`;
  execFileSync(gitPath, ['fast-import', '--quiet'], { cwd: repo, env: cleanEnvironment, input: stream });
  git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/topic');
  git(repo, 'read-tree', 'HEAD');
  git(repo, 'checkout-index', '-a', '-f');
  const head = git(repo, 'rev-parse', 'HEAD');
  parents.set(repo, head);
  return head;
}

function run(name, repo, variables, acceptedExitCodes = [0]) {
  try {
    return execFileSync('/bin/sh', ['-e', '-c', recipe(name)], {
      cwd: repo, env: { ...cleanEnvironment, PATH: recipePaths.get(repo), ...variables },
      encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'],
    });
  } catch (error) {
    if (acceptedExitCodes.includes(error.status)) return error.stdout;
    throw error;
  }
}

function history(repo, base, head) {
  const lines = run('history', repo, { BASE: base, HEAD: head }).trim().split('\n');
  const shallow = lines.pop() === 'true';
  const baseLine = lines.pop();
  const headLine = lines.pop();
  const logCount = lines.length;
  const parsed = [...new Set([...new Set([headLine, ...lines])].slice(0, 199).concat(baseLine))].map((line) => {
    const [commit_sha, tree_sha, ...parent_shas] = line.split(' ');
    return { commit_sha, tree_sha, parent_shas };
  });
  const records = parsed.filter((record) => record.parent_shas.length <= 16);
  const covered = new Set([base]);
  for (let pass = 0; pass < records.length; pass += 1) {
    for (const record of records) {
      if (record.parent_shas.length && record.parent_shas.every((parent) => covered.has(parent))) {
        covered.add(record.commit_sha);
      }
    }
  }
  return {
    commits: records,
    complete: !shallow && logCount < 200 && records.length === parsed.length && covered.has(head),
  };
}

const snapshotCases = ['sha1', 'sha256'].flatMap((format) => [false, true].map((previousDirty) => ({ format, previousDirty })));
for (const { format, previousDirty } of snapshotCases) {
  posixTest(`documented recipes recover ${format} snapshots with previousDirty=${previousDirty} without Qodo`, (t) => {
    const { directory, repo } = fixture(t, format);
    assert.throws(() => execFileSync('/bin/sh', ['-c', 'command -v qodo'], {
      env: { ...cleanEnvironment, PATH: recipePaths.get(repo) },
    }));
    const base = commit(repo, 'base = 1\n');
    const head = commit(repo, 'base = 1\nfirst = 2\n');
    assert.equal(git(repo, 'remote'), '');
    const collected = history(repo, base, head);
    assert.equal(collected.complete, true);
    assert.equal(collected.commits[0].commit_sha, head);
    for (const record of collected.commits) {
      assert.equal(record.tree_sha, git(repo, 'rev-parse', `${record.commit_sha}^{tree}`));
      assert.equal(record.commit_sha.length, format === 'sha1' ? 40 : 64);
    }

    const snapshot = join(directory, 'private');
    mkdirSync(snapshot, { mode: 0o700 });
    run('snapshot-setup', repo, { ROOT: repo, TMP: snapshot });
    const variables = { GIT_DIR: join(snapshot, 'snapshot.git'), GIT_INDEX_FILE: join(snapshot, 'index') };
    const materialize = (patch, name) => {
      const file = join(snapshot, name);
      writeFileSync(file, patch, { mode: 0o600 });
      return run('snapshot-tree', repo, { ...variables, BASE: base, PATCH: file }).trim();
    };
    const priorLine = previousDirty ? 'previous_dirty = 6\n' : '';
    if (previousDirty) writeFileSync(join(repo, 'app.py'), 'base = 1\nfirst = 2\n' + priorLine);
    const first = run('tracked-patch', repo, { BASE: base, FILE: 'app.py' });
    const previousTree = materialize(first, 'first.patch');
    assert.equal(previousTree === git(repo, 'rev-parse', `${head}^{tree}`), !previousDirty);

    writeFileSync(join(repo, 'app.py'), 'base = 1\nfirst = 2\n' + priorLine + 'staged = 3\n');
    git(repo, 'add', 'app.py');
    writeFileSync(join(repo, 'app.py'), 'base = 1\nfirst = 2\n' + priorLine + 'staged = 3\ndirty = 4\n');
    writeFileSync(join(repo, 'new.py'), 'untracked = 5\n');
    const indexBefore = git(repo, 'ls-files', '--stage');
    const statusBefore = git(repo, 'status', '--porcelain');
    const current = run('tracked-patch', repo, { BASE: base, FILE: 'app.py' })
      + run('untracked-patch', repo, { FILE: 'new.py' }, [0, 1]);
    assert.match(current, /\+first = 2/);
    assert.match(current, /\+staged = 3/);
    assert.match(current, /\+dirty = 4/);
    assert.match(current, /diff --git a\/new.py b\/new.py/);
    const currentTree = materialize(current, 'current.patch');
    assert.notEqual(currentTree, previousTree);
    const delta = run('snapshot-delta', repo, {
      ...variables, PREVIOUS_TREE: previousTree, CURRENT_TREE: currentTree,
    });
    assert.doesNotMatch(delta, /\+first = 2/);
    assert.doesNotMatch(delta, /\+previous_dirty = 6/);
    assert.match(delta, /\+dirty = 4/);
    const unchanged = run('snapshot-delta', repo, {
      ...variables, PREVIOUS_TREE: currentTree, CURRENT_TREE: currentTree,
    });
    assert.equal(unchanged, '');
    assert.equal(git(repo, 'rev-parse', 'HEAD'), head);
    assert.equal(git(repo, 'ls-files', '--stage'), indexBefore);
    assert.equal(git(repo, 'status', '--porcelain'), statusBefore);
  });
}

posixTest('history recipe includes actual HEAD when HEAD equals base', (t) => {
  const { repo } = fixture(t);
  const base = commit(repo, 'base = 1\n');
  const result = history(repo, base, base);
  assert.equal(result.complete, true);
  assert.equal(result.commits.length, 1);
  assert.equal(result.commits[0].tree_sha, git(repo, 'rev-parse', 'HEAD^{tree}'));
});

posixTest('bounded history and shallow repositories cannot claim complete collection', (t) => {
  const { directory, repo } = fixture(t);
  const base = commit(repo, 'base = 1\n');
  let head;
  for (let i = 0; i < 201; i += 1) head = commit(repo, `value = ${i}\n`);
  const bounded = history(repo, base, head);
  assert.equal(bounded.commits.length, 200);
  assert.equal(bounded.complete, false);
  assert.ok(bounded.commits.some((record) => record.commit_sha === base));
  const shallow = join(directory, 'shallow');
  git(directory, 'clone', '-q', '--depth=1', `file://${repo}`, shallow);
  recipePaths.set(shallow, recipePaths.get(repo));
  assert.equal(history(shallow, head, head).complete, false);
});

posixTest('history checks all merge parents, including ancestry outside the comparison base', (t) => {
  const { repo } = fixture(t);
  const rootCommit = commit(repo, 'root = 1\n');
  const base = commit(repo, 'base = 2\n');
  const side = [
    'commit refs/heads/side', 'committer Fixture <fixture@example.test> 1700000001 +0000',
    'data 4', 'side', `from ${rootCommit}`, '',
  ].join('\n');
  execFileSync(gitPath, ['fast-import', '--quiet'], { cwd: repo, env: cleanEnvironment, input: side });
  const sideHead = git(repo, 'rev-parse', 'refs/heads/side');
  const head = commit(repo, 'merged = 3\n', [sideHead]);
  const result = history(repo, base, head);
  assert.deepEqual(result.commits[0].parent_shas, [base, sideHead]);
  assert.ok(result.commits.some((record) => record.commit_sha === sideHead));
  assert.equal(result.complete, false);
});

posixTest('an octopus merge beyond the wire parent limit remains representable as incomplete history', (t) => {
  const { repo } = fixture(t);
  const base = commit(repo, 'base = 1\n');
  const refs = Array.from({ length: 16 }, (_, index) => `refs/heads/side-${index}`);
  const stream = refs.map((ref) => [
    `commit ${ref}`, 'committer Fixture <fixture@example.test> 1700000001 +0000',
    `data ${ref.length}`, ref, `from ${base}`, '',
  ].join('\n')).join('\n');
  execFileSync(gitPath, ['fast-import', '--quiet'], { cwd: repo, env: cleanEnvironment, input: stream });
  const head = commit(repo, 'merged = 2\n', refs.map((ref) => git(repo, 'rev-parse', ref)));
  assert.equal(git(repo, 'show', '-s', '--format=%P', head).split(' ').length, 17);
  const result = history(repo, base, head);
  assert.equal(result.complete, false);
  assert.ok(!result.commits.some((record) => record.commit_sha === head));
  assert.ok(result.commits.every((record) => record.parent_shas.length <= 16));
});

test('guidance preserves capability, permission, retry and recovery boundaries', () => {
  for (const text of [
    'all merge parents', 'snapshot_permission_changed', 'incremental_diff_too_large',
    'snapshot_unavailable', 'identical arguments and the same key', 'twenty completed records for seven days',
    'complete=false', 'Without advertised history support', 'operation_id` is not a checkpoint ID',
  ]) assert.ok(reference.includes(text), text);
  const skill = readFileSync(join(root, 'skills/qodo-review/SKILL.md'), 'utf8');
  assert.match(skill, /references\/mcp-local-review.md/);
  assert.doesNotMatch(skill, /If no collector is available/);
});

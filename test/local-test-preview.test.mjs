import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  appendFileSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { prepareSkillRelease } from '../scripts/skill-release-plan.mjs';
import { runLocalTests } from '../scripts/test-local.mjs';

const source = dirname(dirname(fileURLToPath(import.meta.url)));
const wisdom = 'skills/qodo-codebase-wisdom/SKILL.md';
const read = (root, path) => readFileSync(join(root, path), 'utf8');
const json = (root, path) => JSON.parse(read(root, path));
const git = (root, ...args) => execFileSync('git', args, {
  cwd: root, encoding: 'utf8', env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' }, stdio: ['ignore', 'pipe', 'pipe'],
}).trimEnd();
const check = (root, ...args) => execFileSync(process.execPath, args, { cwd: root, stdio: 'pipe' });

function inventory(root, prefix = '') {
  return readdirSync(join(root, prefix), { withFileTypes: true }).flatMap((entry) => {
    if (['.git', 'node_modules'].includes(entry.name)) return [];
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    return entry.isDirectory() ? inventory(root, path)
      : [[path, createHash('sha256').update(readFileSync(join(root, path))).digest('hex')]];
  }).sort(([left], [right]) => left.localeCompare(right));
}

function snapshot(root) {
  return {
    head: git(root, 'rev-parse', 'HEAD'), status: git(root, 'status', '--porcelain'),
    index: readFileSync(join(root, '.git/index')), files: inventory(root),
  };
}

function fixture(t) {
  const parent = mkdtempSync(join(tmpdir(), 'local-test-'));
  t.after(() => rmSync(parent, { recursive: true, force: true, maxRetries: 5 }));
  const root = join(parent, 'source');
  const temporaryParent = join(parent, 'previews');
  mkdirSync(root);
  mkdirSync(temporaryParent);
  for (const name of readdirSync(source)) {
    if (!['.git', 'node_modules', '.DS_Store', 'antigravity-plugins'].includes(name)) {
      cpSync(join(source, name), join(root, name), { recursive: true });
    }
  }
  // Model the release before this adapter: a source commit introduces the new
  // generator, but deliberately does not commit its Antigravity output tree.
  const generator = read(root, 'scripts/sync-adapters.mjs');
  writeFileSync(join(root, 'scripts/sync-adapters.mjs'), '// Previous released generator.\n');
  git(root, 'init', '--quiet');
  for (const [key, value] of Object.entries({ 'user.name': 'Test', 'user.email': 'test@example.com',
    'core.autocrlf': 'false', 'core.safecrlf': 'false', 'commit.gpgsign': 'false' })) git(root, 'config', key, value);
  const commit = (message) => { git(root, 'add', '--all'); git(root, 'commit', '--quiet', '-m', message); };
  commit('prepared release before Antigravity');
  const base = git(root, 'rev-parse', 'HEAD');
  git(root, 'update-ref', 'refs/remotes/origin/main', base);
  writeFileSync(join(root, 'scripts/sync-adapters.mjs'), generator);
  commit('add source adapter without generated packages');
  cpSync(join(source, 'node_modules'), join(root, 'node_modules'), { recursive: true, dereference: true });
  const run = (runSuite, options = {}) => runLocalTests(root, { temporaryParent, runSuite, ...options });
  return { root, temporaryParent, base, commit, run };
}

test('clean source checkout tests generate Antigravity only in a temporary preview and clean up', (t) => {
  const f = fixture(t);
  assert.equal(git(f.root, 'status', '--porcelain'), '');
  assert.equal(existsSync(join(f.root, 'antigravity-plugins')), false);
  const before = snapshot(f.root);
  const originalVersion = json(f.root, 'distribution/catalog.json').package.version;
  let preview;
  f.run((root) => {
    preview = root;
    assert.notEqual(json(root, 'distribution/catalog.json').package.version, originalVersion);
    assert.equal(existsSync(join(root, 'antigravity-plugins/qodo/plugin.json')), true);
    check(root, 'scripts/validate.mjs');
    check(root, 'scripts/build-release-index.mjs', '--check');
    check(root, 'scripts/build-cli-managed-bundle.mjs', '--check');
    check(root, '--test', 'test/antigravity-plugin.test.mjs', 'test/setup-packaging.test.mjs');
  });
  assert.deepEqual(snapshot(f.root), before, 'files, index, HEAD, and versions must remain untouched');
  assert.equal(existsSync(preview), false);
  assert.deepEqual(readdirSync(f.temporaryParent), []);
});

test('local preview includes staged, unstaged, and new source files without changing the index', (t) => {
  const f = fixture(t);
  appendFileSync(join(f.root, wisdom), '\nStaged local evidence.\n');
  git(f.root, 'add', wisdom);
  appendFileSync(join(f.root, wisdom), '\nUnstaged local evidence.\n');
  const reference = 'skills/qodo-codebase-wisdom/references/local-example.md';
  writeFileSync(join(f.root, reference), 'New local reference.\n');
  const before = snapshot(f.root);
  f.run((root) => {
    const installed = read(root, 'antigravity-plugins/qodo/skills/qodo-codebase-wisdom/SKILL.md');
    assert.match(installed, /Staged local evidence/);
    assert.match(installed, /Unstaged local evidence/);
    assert.equal(read(root, `antigravity-plugins/qodo/${reference}`), 'New local reference.\n');
    check(root, 'scripts/sync-adapters.mjs', '--check');
  });
  assert.deepEqual(snapshot(f.root), before);
  assert.deepEqual(readdirSync(f.temporaryParent), []);
});

test('failed package tests propagate failure and still clean the preview without touching source', (t) => {
  const f = fixture(t);
  const before = snapshot(f.root);
  let preview;
  assert.throws(() => f.run((root) => {
    preview = root;
    writeFileSync(join(root, 'README.md'), 'Only the disposable checkout was changed.\n');
    throw new Error('injected package test failure');
  }), /injected package test failure/);
  assert.deepEqual(snapshot(f.root), before);
  assert.equal(existsSync(preview), false);
  assert.deepEqual(readdirSync(f.temporaryParent), []);
});

test('invalid generated source edits fail preparation instead of being repaired by the preview', (t) => {
  const f = fixture(t);
  mkdirSync(join(f.root, 'antigravity-plugins/qodo'), { recursive: true });
  writeFileSync(join(f.root, 'antigravity-plugins/qodo/plugin.json'), '{"name":"drift"}\n');
  const before = snapshot(f.root);
  let tested = false;
  assert.throws(() => f.run(() => { tested = true; }));
  assert.equal(tested, false);
  assert.deepEqual(snapshot(f.root), before);
  assert.deepEqual(readdirSync(f.temporaryParent), []);
});

for (const damage of ['changed manifest', 'missing package']) {
  test(`release PR ${damage} fails strict validation without regeneration`, (t) => {
    const f = fixture(t);
    const result = prepareSkillRelease(f.root);
    const plugins = join(f.root, 'antigravity-plugins/qodo');
    if (damage === 'changed manifest') writeFileSync(join(plugins, 'plugin.json'), '{"name":"drift"}\n');
    else rmSync(plugins, { recursive: true });
    f.commit('prepared release with damaged artifacts');
    const before = snapshot(f.root);
    let tested = false;
    assert.throws(() => f.run((root) => {
      tested = true;
      assert.equal(json(root, 'distribution/catalog.json').package.version, result.version);
      if (damage === 'changed manifest') assert.equal(read(root, 'antigravity-plugins/qodo/plugin.json'), '{"name":"drift"}\n');
      else assert.equal(existsSync(join(root, 'antigravity-plugins/qodo')), false);
      check(root, 'scripts/sync-adapters.mjs', '--check');
    }), /Generated adapters are stale/);
    assert.equal(tested, true, 'release artifacts must reach the strict checks without a new preview release');
    assert.deepEqual(snapshot(f.root), before);
    assert.deepEqual(readdirSync(f.temporaryParent), []);
  });
}

test('test scratch directories cannot be created inside the contributor checkout', (t) => {
  const f = fixture(t);
  const before = snapshot(f.root);
  assert.throws(() => f.run(() => {}, { temporaryParent: f.root }), /must be outside/);
  assert.deepEqual(snapshot(f.root), before);
});

test('Git environment overrides cannot redirect preview writes into the contributor checkout', (t) => {
  const f = fixture(t);
  const before = snapshot(f.root);
  const overrides = { GIT_DIR: join(f.root, '.git'), GIT_WORK_TREE: f.root, GIT_INDEX_FILE: join(f.root, '.git/index') };
  const prior = Object.fromEntries(Object.keys(overrides).map((key) => [key, process.env[key]]));
  try {
    Object.assign(process.env, overrides);
    f.run((root) => assert.equal(existsSync(join(root, 'antigravity-plugins/qodo/plugin.json')), true));
  } finally {
    for (const [key, value] of Object.entries(prior)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
  assert.deepEqual(snapshot(f.root), before);
  assert.deepEqual(readdirSync(f.temporaryParent), []);
});

test('committed CI mode dispatches only the strict suite in place and preserves its exit code', (t) => {
  const f = fixture(t);
  const before = snapshot(f.root);
  const fakeNpm = join(f.temporaryParent, 'npm.mjs');
  writeFileSync(fakeNpm, [
    "import assert from 'node:assert/strict';",
    "assert.deepEqual(process.argv.slice(2), ['run', 'test:artifacts']);",
    'assert.equal(process.cwd(), process.env.TEST_EXPECTED_ROOT);',
    'process.exit(Number(process.env.TEST_SUITE_EXIT));',
  ].join('\n'));
  for (const status of [0, 23]) {
    const result = spawnSync(process.execPath, ['scripts/test-local.mjs'], {
      cwd: f.root, encoding: 'utf8', env: { ...process.env, QODO_SKILLS_TEST_MODE: 'committed',
        npm_execpath: fakeNpm, TEST_EXPECTED_ROOT: realpathSync(f.root), TEST_SUITE_EXIT: String(status) },
    });
    assert.equal(result.status, status, result.stderr);
    assert.deepEqual(snapshot(f.root), before);
    assert.deepEqual(readdirSync(f.temporaryParent), ['npm.mjs']);
  }
});

test('CI and publishers explicitly test committed artifacts rather than regenerating them', () => {
  const manifest = json(source, 'package.json');
  assert.equal(manifest.scripts.test, 'node scripts/test-local.mjs');
  assert.match(manifest.scripts['test:artifacts'], /^npm run check &&/);
  assert.doesNotMatch(manifest.scripts['test:artifacts'], /npm test|test-local\.mjs|npm run adapters/);
  for (const workflow of ['validate', 'release', 'ship-marketplaces']) {
    assert.match(read(source, `.github/workflows/${workflow}.yml`),
      /env:\s*\n\s*QODO_SKILLS_TEST_MODE: committed\s*\n\s*run: npm test/);
  }
});

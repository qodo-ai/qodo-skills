import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { importRuntime, selected, verifyRuntime } from '../scripts/import-cockpit-runtime.mjs';
import { buildCliManagedBundle } from '../scripts/build-cli-managed-bundle.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const skillName = 'qodo-review-cockpit';
const canonical = join(root, 'skills', skillName);
const python = execFileSync('python3', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' }).trim();
function temp(t) {
  const path = realpathSync(mkdtempSync(join(tmpdir(), 'cockpit-package-')));
  t.after(() => { chmodTree(path, 0o755, 0o644); rmSync(path, { recursive: true, force: true }); });
  return path;
}
function put(path, text) { mkdirSync(dirname(path), { recursive: true }); writeFileSync(path, text); }
function chmodTree(path, dirMode, fileMode) {
  if (!existsSync(path)) return;
  chmodSync(path, dirMode);
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) chmodTree(child, dirMode, fileMode);
    else chmodSync(child, fileMode);
  }
}
function git(path, ...args) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^GIT_/i.test(name)));
  return execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-C', path, ...args],
    { encoding: 'utf8', env, stdio: ['pipe', 'pipe', 'pipe'] }).trim();
}
// A committed policy hash is retained alongside the manifest-driven sanitizer.
const policy = '# fixture release policy\n';
function sourceFixture(t) {
  const path = temp(t);
  git(path, 'init', '-q');
  git(path, 'config', 'user.name', 'ZzAuthor'); git(path, 'config', 'user.email', 'zzauthor@example.invalid');
  const files = { 'cockpit/__init__.py': '', 'cockpit/__main__.py': 'print("fixture")\n',
    'app/index.html': '<html>Fixture</html>\n', 'config.json': '{}\n', LICENSE: 'Fixture terms\n',
    'release/build.py': policy, 'release/manifest.json': JSON.stringify({never: [], rules: [{name:'secret',pattern:'SECRET_TEST'}]}),
    'cockpit/helper.py': '# release:internal\nprivate detail\n# /release:internal\npublic = True\n',
    'memory/amr/MEMORY.md': 'never import\n', 'sessions/private.json': 'never import\n',
    'config.local.json': 'never import\n', 'app/design.png': 'never import\n' };
  for (const [name, text] of Object.entries(files)) put(join(path, name), text);
  git(path, 'add', '.'); git(path, 'commit', '-qm', 'Fixture snapshot');
  return { source: path, commit: git(path, 'rev-parse', 'HEAD'), destination: join(temp(t), 'skill') };
}

test('committed import is deterministic, sanitizes internal blocks, excludes state and pins hashes', (t) => {
  const options = sourceFixture(t);
  const first = importRuntime(options);
  assert.equal(first.commit, options.commit);
  assert.equal(first.files.length, 6);
  assert.equal(readFileSync(join(options.destination, 'runtime/cockpit/helper.py'), 'utf8'), 'public = True\n');
  const helper = first.files.find((f) => f.path === 'cockpit/helper.py');
  assert.equal(helper.strippedLines, 3); assert.notEqual(helper.sourceSha256, helper.sha256);
  const receipt = readFileSync(join(options.destination, 'runtime-manifest.json'), 'utf8');
  importRuntime(options);
  assert.equal(readFileSync(join(options.destination, 'runtime-manifest.json'), 'utf8'), receipt);
  verifyRuntime(options.destination);
  put(join(options.destination, 'runtime/app/index.html'), 'tampered');
  assert.throws(() => verifyRuntime(options.destination));
});

test('import rejects mutable refs, dirty source and bad policy output before replacing payload', (t) => {
  const options = sourceFixture(t);
  importRuntime(options);
  const before = readFileSync(join(options.destination, 'runtime-manifest.json'), 'utf8');
  assert.throws(() => importRuntime({ ...options, commit: 'HEAD' }), /full lowercase/);
  put(join(options.source, 'cockpit/helper.py'), 'dirty\n');
  assert.throws(() => importRuntime(options), /dirty/);
  git(options.source, 'checkout', '--', 'cockpit/helper.py');
  put(join(options.source, 'cockpit/helper.py'), 'SECRET_TEST\n');
  git(options.source, 'add', '.'); git(options.source, 'commit', '-qm', 'Unsafe fixture');
  assert.throws(() => importRuntime({ ...options, commit: git(options.source, 'rev-parse', 'HEAD') }));
  assert.equal(readFileSync(join(options.destination, 'runtime-manifest.json'), 'utf8'), before);
});

test('resource allowlist excludes real data, local config, binaries and traversal', () => {
  for (const path of ['memory/amr/MEMORY.md', 'sessions/a.json', 'config.local.json',
    'app/design.png', 'app/.env', 'cockpit/__pycache__/a.pyc', 'install.sh', 'PLAN.md']) assert.equal(selected(path), false);
  for (const path of ['../x', 'app/../x', '/app/index.html']) assert.throws(() => selected(path));
});

function installedFixture(t) {
  const path = temp(t), installed = join(path, 'plugin/skills', skillName), bin = join(path, 'bin');
  cpSync(canonical, installed, { recursive: true });
  put(join(installed, 'runtime/cockpit/__init__.py'), '');
  put(join(installed, 'runtime/cockpit/__main__.py'), `import json,os,sys\nprint(json.dumps({'argv':sys.argv[1:],'home':os.environ.get('REVIEW_COCKPIT_HOME'),'bytecode':sys.dont_write_bytecode}))\n`);
  const log = join(path, 'cli-log.jsonl');
  put(join(bin, 'qodo'), `#!${python}\nimport json,os,sys\nwith open(os.environ['PROBE_LOG'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\nif '--version' in sys.argv: print(os.environ.get('CLI_VERSION','2.1.1'))\nelif 'whoami' in sys.argv:\n print('{}'); sys.exit(int(os.environ.get('AUTH_EXIT','0')))\nelse: print('{}')\n`);
  chmodSync(join(bin, 'qodo'), 0o755);
  const home = join(path, 'state');
  const run = (extra = {}, args = ['home']) => spawnSync(python, ['-B', join(installed, 'scripts/launch.py'), ...args], {
    cwd: path, encoding: 'utf8', env: { ...process.env, PATH: bin, HOME: path,
      REVIEW_COCKPIT_HOME: home, PROBE_LOG: log, ...extra },
  });
  return { path, installed, home, log, run };
}

test('installed launcher works from unrelated cwd/read-only resources with ordered gates and stamped provenance', (t) => {
  const f = installedFixture(t);
  const markdown = readFileSync(join(f.installed, 'SKILL.md'), 'utf8').replace(/distribution skills-sh/g, 'distribution marketplace --host codex')
    .replace('distribution: "skills-sh"', 'distribution: "marketplace"');
  put(join(f.installed, 'SKILL.md'), markdown);
  chmodTree(f.installed, 0o555, 0o444);
  const result = f.run({}, ['review', 'owner/repo#12', '--collect-only']);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { argv: ['--product', 'review', 'owner/repo#12', '--collect-only'], home: f.home, bytecode: true });
  const calls = readFileSync(f.log, 'utf8').trim().split('\n').map(JSON.parse);
  assert.deepEqual(calls[0], ['--version']);
  assert.deepEqual(calls[1], ['read', 'whoami', '--json', '--skill', skillName, '--skill-version', '1.0.0', '--distribution', 'marketplace', '--host', 'codex']);
  assert.deepEqual(calls[2], ['read', 'tools', '--json']);
  assert(!existsSync(join(f.installed, 'runtime/cockpit/__pycache__')));
});

test('version and auth failures stop before later probes; installed state home is refused', (t) => {
  const f = installedFixture(t);
  const old = f.run({ CLI_VERSION: '1.99.0' });
  assert.equal(old.status, 1); assert.match(old.stderr, /CLI prerequisite/);
  assert.equal(readFileSync(f.log, 'utf8').trim().split('\n').length, 1);
  rmSync(f.log);
  const denied = f.run({ AUTH_EXIT: '7' });
  assert.equal(denied.status, 1); assert.match(denied.stderr, /authentication probe failed/);
  assert.equal(readFileSync(f.log, 'utf8').trim().split('\n').length, 2);
  const state = f.run({ REVIEW_COCKPIT_HOME: join(f.installed, 'sessions') });
  assert.equal(state.status, 1); assert.match(state.stderr, /outside installed/);
});

test('replacing installed resources preserves external sessions, config, styles and legacy installation', (t) => {
  const f = installedFixture(t);
  const saved = { 'sessions/session/events.jsonl': 'local reviewer note\n',
    'config.json': '{"memory":{"enabled":true}}\n', 'my-styles/custom.json': '{"id":"custom"}\n' };
  for (const [path, text] of Object.entries(saved)) put(join(f.home, path), text);
  const legacy = join(f.path, '.agents/skills/review-prs/SKILL.md'); put(legacy, 'standalone');
  rmSync(f.installed, { recursive: true }); cpSync(canonical, f.installed, { recursive: true });
  for (const [path, text] of Object.entries(saved)) assert.equal(readFileSync(join(f.home, path), 'utf8'), text);
  assert.equal(readFileSync(legacy, 'utf8'), 'standalone');
});

test('every generated host and CLI bundle retain all pinned runtime resources unchanged', () => {
  const manifest = verifyRuntime();
  const hosts = ['packages/qodo', 'codex-packages/qodo', 'antigravity-plugins/qodo', 'kiro-power'];
  for (const host of hosts) assert.deepEqual(verifyRuntime(join(root, host, 'skills', skillName)), manifest, host);
  const { bundle } = buildCliManagedBundle(root);
  const files = bundle.skills[skillName].files;
  for (const resource of manifest.files) {
    const packaged = files.find((f) => f.path === `runtime/${resource.path}`);
    assert(packaged, resource.path); assert.equal(packaged.sha256, resource.sha256);
  }
});

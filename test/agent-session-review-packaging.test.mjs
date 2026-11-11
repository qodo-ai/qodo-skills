import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { selected, verifyRuntime } from '../scripts/agent-session-review-runtime.mjs';
import { gunzipSync } from 'node:zlib';
import { buildEnterpriseBundle } from '../scripts/build-enterprise-bundle.mjs';
import { kiroRoot } from '../scripts/package-projections.mjs';
import { buildCliManagedBundle } from '../scripts/build-cli-managed-bundle.mjs';
import { buildRepositoryCatalog } from '../scripts/build-repository-catalog.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const skillName = 'qodo-agent-session-review';
const canonical = join(root, 'skills', skillName);
const python = execFileSync(process.platform === 'win32' ? 'python' : 'python3', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' }).trim();
function temp(t) {
  let path = realpathSync(mkdtempSync(join(tmpdir(), 'cockpit-package-')));
  // Python expands Windows 8.3 aliases; compare the same canonical spelling.
  if (process.platform === 'win32') path = execFileSync(python,
    ['-c', 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())', path], {encoding: 'utf8'}).trim();
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
function componentFixture(t) {
  const destination = join(temp(t), 'skill');
  cpSync(canonical, destination, {recursive: true});
  return {destination, runtime: join(destination, 'runtime')};
}

test('maintained source edits validate directly without an upstream checkout or pin update', (t) => {
  const f = componentFixture(t), before = verifyRuntime(f.destination);
  assert(!existsSync(join(f.destination, 'runtime-manifest.json')));
  const path = join(f.runtime, 'cockpit/__init__.py');
  put(path, readFileSync(path, 'utf8') + '\n# A maintained local change.\n');
  const after = verifyRuntime(f.destination);
  assert.notEqual(after.files.find((file) => file.path === 'cockpit/__init__.py').sha256,
    before.files.find((file) => file.path === 'cockpit/__init__.py').sha256);
  assert.equal(after.files.length, before.files.length);
});

test('component hygiene rejects state, private content and internal markers without rewriting source', (t) => {
  const f = componentFixture(t), path = join(f.runtime, 'app/review.js');
  for (const content of ['https://workspace.slack.com/archives/FAKE',
    '# release:internal\nprivate\n# /release:internal\n']) {
    put(path, content);
    assert.throws(() => verifyRuntime(f.destination), /hygiene blocked|Internal release marker/);
    assert.equal(readFileSync(path, 'utf8'), content);
  }
  rmSync(path);
  put(join(f.runtime, 'sessions/private.json'), '{}');
  assert.throws(() => verifyRuntime(f.destination), /Forbidden runtime directory/);
});

test('resource limits and component terms apply to maintained source', (t) => {
  const f = componentFixture(t), file = join(f.runtime, 'app/large.js');
  for (const content of ['x'.repeat(512 * 1024 + 1), 'x\n'.repeat(300_000)]) {
    put(file, content);
    assert.throws(() => verifyRuntime(f.destination), /512 KiB/); rmSync(file);
  }
  put(join(f.runtime, 'LICENSE'), 'Changed component terms');
  assert.throws(() => verifyRuntime(f.destination), /component LICENSE changed/);
});

test('only named existing component files have the inherited line-count exception', (t) => {
  const f = componentFixture(t);
  for (const name of ['cockpit/new_helper.py', 'app/new_widget.js', 'fixtures/demo-new.json']) {
    const path = join(f.runtime, name);
    put(path, Array.from({length: 501}, () => ' ').join('\n') + '\n');
    assert.throws(() => verifyRuntime(f.destination), /500-line limit/);
    rmSync(path);
  }
  assert(verifyRuntime(f.destination).files.some((entry) => entry.path === 'cockpit/server.py'));
});

test('hygiene exceptions remain scoped to the exact allowed path and matched span', (t) => {
  const f = componentFixture(t), file = join(f.runtime, 'fixtures/demo-policy.json');
  put(file, '{"repo":"qodo-ai/shop-demo"}'); verifyRuntime(f.destination);
  put(file, '{"repo":"qodo-ai/shop-demo","other":"qodo-ai/private-example"}');
  assert.throws(() => verifyRuntime(f.destination), /private-repo/); rmSync(file);
  put(join(f.runtime, 'app/policy.js'), 'qodo-ai/shop-demo');
  assert.throws(() => verifyRuntime(f.destination), /private-repo/);
});

test('only the reviewed favicon is admitted; disguised documents are rejected', (t) => {
  const f = componentFixture(t), file = join(f.runtime, 'app/favicon.svg');
  const before = readFileSync(file), inventory = verifyRuntime(f.destination);
  assert.equal(inventory.files.find((entry) => entry.path === 'app/favicon.svg').sha256,
    createHash('sha256').update(before).digest('hex'));
  put(file, '<svg xmlns="http://www.w3.org/2000/svg"/>');
  assert.throws(() => verifyRuntime(f.destination), /Reviewed favicon SHA-256/); put(file, before);
  for (const content of ['%PDF-1.7 renamed', '<svg xmlns="http://www.w3.org/2000/svg"/>']) {
    put(join(f.runtime, 'app/document.js'), content);
    assert.throws(() => verifyRuntime(f.destination), /Unreviewed binary/);
  }
});

test('resource allowlist excludes real data, local config, binaries and traversal', () => {
  for (const path of ['memory/amr/MEMORY.md', 'sessions/a.json', 'config.local.json',
    'app/design.png', 'app/other.svg', 'app/nested/favicon.svg', 'app/.env', 'cockpit/__pycache__/a.pyc', 'install.sh', 'PLAN.md']) assert.equal(selected(path), false);
  for (const path of ['../x', 'app/../x', '/app/index.html']) assert.throws(() => selected(path));
  assert.equal(kiroRoot('qodo'), 'kiro-power');
  assert.equal(kiroRoot('qodo-agent-session-review'), 'kiro-power-agent-session-review');
  assert.throws(() => kiroRoot('qodo-../../elsewhere'), /Invalid Qodo package/);
});

function installedFixture(t, resources = canonical, stubEngine = true) {
  const path = temp(t), installed = join(path, 'plugin/skills', skillName), bin = join(path, 'bin');
  cpSync(resources, installed, { recursive: true });
  if (stubEngine) {
    put(join(installed, 'runtime/cockpit/__init__.py'), '');
    put(join(installed, 'runtime/cockpit/__main__.py'), `import json,os,sys\nprint(json.dumps({'argv':sys.argv[1:],'home':os.environ.get('REVIEW_COCKPIT_HOME'),'bytecode':sys.dont_write_bytecode}))\n`);
  }
  const log = join(path, 'cli-log.jsonl');
  const shim = join(bin, process.platform === 'win32' ? 'qodo.py' : 'qodo');
  put(shim, `#!${python}\n${readFileSync(join(root, 'test/fixtures/agent-session-review-cli.py'), 'utf8')}`);
  chmodSync(shim, 0o755);
  if (process.platform === 'win32') {
    put(join(bin, 'qodo.cmd'), `@"${python}" "%~dp0qodo.py" %*\r\n`);
    put(join(bin, 'qodo.mjs'), `import {spawnSync} from 'node:child_process';\nconst p=spawnSync(${JSON.stringify(python)},[${JSON.stringify(shim)},...process.argv.slice(2)],{stdio:'inherit'});process.exit(p.status??1);\n`);
  }
  const home = join(path, 'state');
  const run = (extra = {}, args = ['home']) => spawnSync(python, ['-B', join(installed, 'scripts/launch.py'), ...args], {
    cwd: path, encoding: 'utf8', env: { ...process.env,
      PATH: process.platform === 'win32' ? [bin, dirname(process.execPath)].join(';') : bin,
      HOME: path, USERPROFILE: path, QODO_HOME: join(path, '.qodo'), REVIEW_COCKPIT_QODO: '',
      REVIEW_COCKPIT_HOME: home, PROBE_LOG: log, PYTHONUTF8: '0', ...extra },
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

test('installed metadata host takes precedence over a body example stamp', (t) => {
  const f = installedFixture(t);
  const path = join(f.installed, 'SKILL.md');
  put(path, readFileSync(path, 'utf8').replace('  distribution: "skills-sh"',
    '  distribution: "skills-sh"\n  host: "kiro"')
    .replace('--distribution skills-sh\n', '--distribution skills-sh --host codex\n'));
  const result = f.run();
  assert.equal(result.status, 0, result.stderr);
  const auth = readFileSync(f.log, 'utf8').trim().split('\n').map(JSON.parse)[1];
  assert.deepEqual(auth.slice(-2), ['--host', 'kiro']);
});

test('Windows UTF8 restart waits and preserves exact arguments and failure status', () => {
  const code = `import importlib.util,pathlib,sys,types
from unittest import mock
path=pathlib.Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location('cockpit_launcher_test',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
args=['note','A note with spaces — שלום 👍','quotes" and backslash\\\\tail']
with mock.patch.object(sys,'flags',types.SimpleNamespace(utf8_mode=0)), mock.patch.object(sys,'platform','win32'), mock.patch.object(sys,'argv',[str(path),*args]), mock.patch.object(module.subprocess,'call',return_value=7) as wait, mock.patch.object(module.os,'execv',side_effect=AssertionError('Windows must wait')):
 try: module.main()
 except SystemExit as error: assert error.code==7,error.code
 else: raise AssertionError('child failure was swallowed')
 assert wait.call_args.args[0]==[sys.executable,'-X','utf8','-B',str(path),*args],wait.call_args
 assert module.os.environ['PYTHONUTF8']=='1'
`;
  execFileSync(python, ['-B', '-c', code, join(canonical, 'scripts/launch.py')], {encoding: 'utf8'});
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

test('error envelopes and malformed identity fail before catalog without leaking payloads', (t) => {
  for (const payload of ['{}','[]','{"workspace_id":"fixture"}','{"error":{"code":"not_logged_in","message":"PRIVATE_IDENTITY"}}', 'not-json']) {
    const f = installedFixture(t);
    const result = f.run({ AUTH_PAYLOAD: payload });
    assert.equal(result.status, 1); assert.match(result.stderr, /authentication probe failed/);
    assert(!result.stderr.includes('PRIVATE_IDENTITY'));
    assert.equal(readFileSync(f.log, 'utf8').trim().split('\n').length, 2);
  }
  for (const identity of [{email:'fixture@example.test'}, {email:'service@example.test',tenant_id:'fixture-tenant',workspace_id:null,user_id:null}]) {
    const f=installedFixture(t), result=f.run({AUTH_PAYLOAD:JSON.stringify(identity)});
    assert.equal(result.status,0,result.stderr);
  }
  for (const payload of ['{}','[]','{"tools":[]}','{"tools":[{"group":"codebase","leaf":"write","access":"write","mutating":true}]}','{"error":{"code":"not_supported"}}']) {
    const f = installedFixture(t);
    const result = f.run({ CATALOG_PAYLOAD: payload });
    assert.equal(result.status, 1); assert.match(result.stderr, /read catalog probe failed/);
    assert(!existsSync(f.home));
  }
});

test('data-home aliases and the configured CLI command retain one consistent launch identity', (t) => {
  const f = installedFixture(t);
  const official = join(f.path, 'session-review-data');
  const selected = f.run({ QODO_AGENT_SESSION_REVIEW_HOME: official,
    QODO_AGENT_SESSION_REVIEW_CLI: join(f.path, process.platform === 'win32' ? 'bin/qodo.cmd' : 'bin/qodo') });
  assert.equal(selected.status, 0, selected.stderr);
  assert.equal(JSON.parse(selected.stdout).home, official);
  const alias = join(f.path, 'legacy-data');
  const result = f.run({ REVIEW_COCKPIT_HOME: '', PR_COCKPIT_HOME: alias,
    REVIEW_COCKPIT_QODO: join(f.path, process.platform === 'win32' ? 'bin/qodo.cmd' : 'bin/qodo') });
  assert.equal(result.status, 0, result.stderr); assert.equal(JSON.parse(result.stdout).home, alias);
  const standard = f.run({ REVIEW_COCKPIT_HOME: '', PR_COCKPIT_HOME: '' });
  assert.equal(standard.status, 0, standard.stderr);
  assert.equal(JSON.parse(standard.stdout).home, join(f.path, '.qodo/agent-session-review'));
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

test('actual generated Claude/Codex installs collect, refresh, retain notes/marks on reinstall and export read-only', (t) => {
  for (const host of ['packages/qodo-agent-session-review', 'codex-packages/qodo-agent-session-review']) {
    const f = installedFixture(t, join(root, host, 'skills', skillName), false);
    const sessions = join(f.path, 'custom-sessions');
    const config = JSON.stringify({ sessions, memory: {enabled: false}, style: 'package' });
    const style = '{"id":"my-style","title":"Personal style"}';
    put(join(f.home, 'config.json'), config); put(join(f.home, 'my-styles/my-style.json'), style);
    chmodTree(f.installed, 0o555, 0o444);
    const collected = f.run({STUB_MANAGED: '1'}, ['review', 'demo/repo#1', '--collect-only']);
    assert.equal(collected.status, 0, collected.stderr);
    const sid = readFileSync(join(sessions, 'latest'), 'utf8').trim();
    const data = JSON.parse(readFileSync(join(sessions, sid, 'review-data.json')));
    assert.equal(data.product, true); assert.equal(data.provider_writes, false);
    assert.equal(data.memory.enabled, 'False');
    const pr = data.prs[0].key;
    const enriched = f.run({}, ['enrich', join(f.installed, 'references/example-enrich.json'), '--session', sid]);
    assert.equal(enriched.status, 0, enriched.stderr);
    assert.deepEqual(JSON.parse(enriched.stdout).warnings, []);
    const content = JSON.parse(readFileSync(join(sessions, sid, 'review-data.json')));
    assert.equal(content.behavior.files[0].hunks[0].lines[0].text, 'The helper returns two instead of one.');
    assert.equal(content.prs[0].decisions[0].id, 'larger-value');
    assert.deepEqual(content.prs[0].layer_coverage.uncovered, []);
    const noteText = 'Installed package reviewer note — שלום 👍';
    const note = f.run({}, ['note', '--session', sid, '--pr', pr, noteText]);
    assert.equal(note.status, 0, note.stderr);
    const events = join(sessions, sid, 'events.jsonl'), before = readFileSync(events, 'utf8');
    assert(before.split('\n').filter(Boolean).map(JSON.parse).some((event) => event.note === noteText || event.text === noteText));
    const mark = f.run({}, ['mark', '--session', sid, '--pr', pr, '👍']);
    assert.equal(mark.status, 0, mark.stderr);
    const persisted = readFileSync(events, 'utf8');
    const refreshed = f.run({STUB_MANAGED: '1'}, ['refresh', '--session', sid]);
    assert.equal(refreshed.status, 0, refreshed.stderr);
    assert.equal(readFileSync(events, 'utf8'), persisted);
    const updated = JSON.parse(readFileSync(join(sessions, sid, 'review-data.json')));
    assert.equal(updated.session, sid);
    assert.equal(updated.prs[0].qodo_review.commit, 'b'.repeat(40));
    assert(!updated.prs[0].qodo_read_error);
    assert(!existsSync(join(f.home, 'memory')));
    assert(!existsSync(join(sessions, sid, 'memory')));
    verifyRuntime(f.installed);
    chmodTree(f.installed, 0o755, 0o644); rmSync(f.installed, {recursive: true});
    cpSync(join(root, host, 'skills', skillName), f.installed, {recursive: true});
    chmodTree(f.installed, 0o555, 0o444);
    const output = join(f.path, 'review.html');
    const exported = f.run({}, ['export', '--session', sid, '--out', output]);
    assert.equal(exported.status, 0, exported.stderr);
    assert(readFileSync(output, 'utf8').includes('Installed package reviewer note'));
    assert.equal(readFileSync(events, 'utf8'), persisted);
    assert.equal(readFileSync(join(f.home, 'config.json'), 'utf8'), config);
    assert.equal(readFileSync(join(f.home, 'my-styles/my-style.json'), 'utf8'), style);
    verifyRuntime(f.installed);
  }
});

function archiveFiles(archive) {
  const bytes = gunzipSync(archive), files = new Map();
  for (let offset = 0; offset + 512 <= bytes.length;) {
    const header = bytes.subarray(offset, offset + 512);
    if (header.every((byte) => byte === 0)) break;
    const text = (start, length) => header.subarray(start, start + length).toString().replace(/\0.*$/, '');
    const name = text(0, 100), prefix = text(345, 155), size = parseInt(text(124, 12).trim() || '0', 8);
    files.set(prefix ? `${prefix}/${name}` : name, bytes.subarray(offset + 512, offset + 512 + size));
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  return files;
}

test('unlisted beta packages stay out of repository marketplace indexes', (t) => {
  const generated = temp(t);
  for (const path of ['scripts', 'distribution', 'skills', 'node_modules', 'package.json']) {
    cpSync(join(root, path), join(generated, path), { recursive: true });
  }
  execFileSync(process.execPath, [join(generated, 'scripts/sync-adapters.mjs')], { cwd: generated, stdio: 'pipe' });
  const catalog = JSON.parse(readFileSync(join(root, 'distribution/catalog.json')));
  const listed = catalog.installPackages.filter((pkg) => pkg.providerListed !== false).map((pkg) => pkg.name).sort();
  for (const path of ['.agents/plugins/marketplace.json', '.claude-plugin/marketplace.json']) {
    const marketplace = JSON.parse(readFileSync(join(generated, path)));
    assert.deepEqual(marketplace.plugins.map((plugin) => plugin.name).sort(), listed, path);
    assert(!marketplace.plugins.some((plugin) => plugin.name === 'qodo-agent-session-review'), path);
  }
  assert(catalog.installPackages.some((pkg) => pkg.name === 'qodo-agent-session-review' && pkg.default === false));
  const packageEntry = buildRepositoryCatalog(generated, 'a'.repeat(40)).skills.find((skill) => skill.name === skillName);
  assert(packageEntry, 'explicit repository catalog retains the optional skill');
  for (const path of ['SKILL.md', 'scripts/launch.py', 'runtime/LICENSE', 'runtime/app/index.html']) {
    assert(packageEntry.files.some((file) => file.path === path), `explicit package retains ${path}`);
  }
});

test('optional hosts retain maintained runtime while legacy managed packages remain unchanged', (t) => {
  const manifest = verifyRuntime();
  const readme = readFileSync(join(root, 'kiro-power-agent-session-review/README.md'), 'utf8');
  assert(readme.includes('kiro-power-agent-session-review'));
  assert(readme.includes('local'));
  assert(!readme.includes('through the Kiro Powers marketplace'));
  const hosts = ['packages/qodo-agent-session-review', 'codex-packages/qodo-agent-session-review', 'antigravity-plugins/qodo-agent-session-review', 'kiro-power-agent-session-review'];
  for (const host of hosts) assert.deepEqual(verifyRuntime(join(root, host, 'skills', skillName)), manifest, host);
  const { bundle } = buildCliManagedBundle(root);
  assert(!bundle.skills[skillName], 'Unsupported optional package must not enter legacy CLI-managed schema');
  const output = temp(t);
  buildEnterpriseBundle({output, commit: 'a'.repeat(40)});
  const archive = archiveFiles(readFileSync(join(output,
    `qodo-enterprise-bundle-v${JSON.parse(readFileSync(join(root, 'package.json'))).version}.tar.gz`)));
  assert(![...archive.keys()].some((name) => name.includes(skillName)),
    'Unsupported optional package must not enter legacy enterprise schema');
  for (const host of hosts) {
    const plugin = JSON.parse(readFileSync(join(root, host, 'plugin.json')));
    assert.equal(plugin.license, 'MIT AND LicenseRef-Qodo-Cockpit', host);
  }
  for (const name of ['qodo', 'qodo-standards']) {
    assert.equal(JSON.parse(readFileSync(join(root, 'packages', name, 'plugin.json'))).license, 'MIT');
    assert(!existsSync(join(root, 'packages', name, 'skills', skillName)));
  }
});

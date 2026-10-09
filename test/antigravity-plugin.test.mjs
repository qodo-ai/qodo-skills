import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import {
  cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { stampSkillProvenance } from '../scripts/skill-provenance.mjs';
import { executeReleaseTransaction } from '../scripts/prepare-release.mjs';

const source = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (root, path) => readFileSync(join(root, path), 'utf8').replace(/\r\n/g, '\n');
const catalog = JSON.parse(read(source, 'distribution/catalog.json'));
const author = { name: 'Qodo', email: 'support@qodo.ai', url: 'https://www.qodo.ai' };
const keywords = ['qodo', 'code-review', 'code-intelligence', 'standards', 'coding-agents'];

function files(root, prefix = '') {
  return readdirSync(join(root, prefix), { withFileTypes: true }).flatMap((entry) => {
    assert.ok(!entry.isSymbolicLink(), `${prefix}/${entry.name}: unexpected symlink`);
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    return entry.isDirectory() ? files(root, path) : [path];
  }).sort();
}

function temporary(t) {
  const root = mkdtempSync(join(tmpdir(), 'qodo-antigravity-test-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return root;
}

test('Antigravity manifests satisfy the Marketplace contract and exact package membership', () => {
  const plugins = join(source, 'antigravity-plugins');
  const canonicalLogo = readFileSync(join(source, 'distribution/assets/antigravity/qodo.png'));
  assert.deepEqual([...canonicalLogo.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(canonicalLogo.toString('ascii', 12, 16), 'IHDR');
  const width = canonicalLogo.readUInt32BE(16);
  const height = canonicalLogo.readUInt32BE(20);
  assert.equal(width, height);
  assert.ok(width >= 128);
  assert.ok([4, 6].includes(canonicalLogo[25]), 'Marketplace PNG must include an alpha channel');
  assert.deepEqual(readdirSync(plugins).sort(), catalog.installPackages.map((pkg) => pkg.name).sort());
  for (const pkg of catalog.installPackages) {
    const root = join(plugins, pkg.name);
    const manifest = JSON.parse(read(root, 'plugin.json'));
    assert.deepEqual(manifest, {
      name: pkg.name,
      displayName: pkg.displayName,
      version: catalog.package.version,
      description: pkg.antigravity.description,
      logo: 'assets/qodo.png',
      suggestedPrompts: pkg.antigravity.suggestedPrompts,
      category: 'Developer Tools',
      keywords,
      author,
      homepage: catalog.package.homepage,
      repository: catalog.package.repository,
      license: catalog.package.license,
    });
    assert.match(manifest.name, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
    assert.ok(manifest.description.length >= 120 && manifest.description.length <= 160);
    assert.ok(manifest.suggestedPrompts.length >= 1 && manifest.suggestedPrompts.length <= 3);
    for (const prompt of manifest.suggestedPrompts) {
      assert.ok(prompt.trim());
      assert.doesNotMatch(prompt, /\$qodo-/, 'Marketplace prompts must not depend on Codex skill syntax');
    }
    assert.deepEqual(readFileSync(join(root, manifest.logo)), canonicalLogo);
    assert.deepEqual(readdirSync(root).sort(), ['README.md', 'assets', 'plugin.json', 'skills']);
    assert.deepEqual(readdirSync(join(root, 'skills')).sort(), [...pkg.skills].sort());
    const readme = read(root, 'README.md');
    assert.ok(readme.includes(`/blob/v${catalog.package.version}/docs/antigravity.md`));
    assert.ok(readme.includes(`/releases/tag/v${catalog.package.version}`));
  }
  assert.ok(catalog.installPackages.find((pkg) => pkg.name === 'qodo').skills.includes('qodo-review-notes'));
  assert.equal(catalog.installPackages.find((pkg) => pkg.name === 'qodo-standards').skills.length, 2);
});

test('all Antigravity workflows and supporting files match their canonical source', () => {
  for (const pkg of catalog.installPackages) {
    for (const name of pkg.skills) {
      const canonical = join(source, 'skills', name);
      const installed = join(source, 'antigravity-plugins', pkg.name, 'skills', name);
      assert.deepEqual(files(installed), files(canonical));
      for (const path of files(canonical)) {
        if (path === 'SKILL.md') {
          const skill = catalog.skills.find((entry) => entry.name === name);
          const expected = stampSkillProvenance(read(canonical, path), {
            name, version: skill.version, packageName: pkg.name,
            distribution: 'marketplace', host: 'antigravity',
          });
          const actual = read(installed, path);
          assert.equal(actual, expected);
          assert.ok(actual.includes(`--skill-version ${skill.version} --distribution marketplace --host antigravity`));
          assert.match(actual, /^  distribution: "marketplace"$/m);
          assert.match(actual, /^  instruction_mode: "embedded"$/m);
          assert.doesNotMatch(actual, /qodo help workflow |--host (?:kiro|codex|claude-code)/);
        } else {
          assert.equal(read(installed, path), read(canonical, path), `${name}/${path}`);
        }
      }
    }
  }
});

test('Antigravity generation detects and repairs missing, changed, and obsolete files deterministically', (t) => {
  const root = temporary(t);
  for (const path of ['scripts', 'distribution', 'skills']) {
    cpSync(join(source, path), join(root, path), { recursive: true });
  }
  const generate = () => execFileSync(process.execPath, ['scripts/sync-adapters.mjs'], { cwd: root });
  const check = () => spawnSync(process.execPath, ['scripts/sync-adapters.mjs', '--check'], { cwd: root, encoding: 'utf8' });
  const plugins = join(root, 'antigravity-plugins');
  const snapshot = () => files(plugins).map((path) => [path, read(plugins, path)]);
  generate();
  const expected = snapshot();
  generate();
  assert.deepEqual(snapshot(), expected);
  assert.equal(check().status, 0);
  const mutations = [
    () => rmSync(join(plugins, 'qodo/skills/qodo-setup/references'), { recursive: true }),
    () => writeFileSync(join(plugins, 'qodo/plugin.json'), '{"name":"qodo","version":"1.0.0"}\n'),
    () => {
      mkdirSync(join(plugins, 'qodo/skills/qodo-get-rules'), { recursive: true });
      writeFileSync(join(plugins, 'qodo/skills/qodo-get-rules/SKILL.md'), 'Optional skill leaked into core.\n');
    },
    () => {
      mkdirSync(join(plugins, 'obsolete-plugin'));
      writeFileSync(join(plugins, 'obsolete-plugin/plugin.json'), '{}\n');
    },
  ];
  for (const mutate of mutations) {
    mutate();
    const result = check();
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Generated adapters are stale:.*antigravity-plugins/s);
    generate();
    assert.deepEqual(snapshot(), expected);
    assert.equal(check().status, 0);
  }
});

test('release rollback restores existing Antigravity roots and removes newly generated roots', (t) => {
  for (const existing of [false, true]) {
    const root = temporary(t);
    const plugins = join(root, 'antigravity-plugins');
    if (existing) {
      mkdirSync(join(plugins, 'qodo'), { recursive: true });
      writeFileSync(join(plugins, 'qodo/plugin.json'), '{"name":"previous"}\n');
    }
    assert.throws(() => executeReleaseTransaction(root, () => {
      mkdirSync(join(plugins, 'qodo'), { recursive: true });
      writeFileSync(join(plugins, 'qodo/plugin.json'), '{"name":"updated"}\n');
      throw new Error('injected Antigravity release failure');
    }), /injected Antigravity release failure/);
    assert.equal(existsSync(plugins), existing);
    if (existing) assert.equal(read(plugins, 'qodo/plugin.json'), '{"name":"previous"}\n');
  }
});

test('release preparation rejects symlinked Antigravity mutation roots before writing', (t) => {
  const root = temporary(t);
  const outside = temporary(t);
  writeFileSync(join(outside, 'marker.txt'), 'unchanged');
  symlinkSync(outside, join(root, 'antigravity-plugins'), process.platform === 'win32' ? 'junction' : 'dir');
  let mutated = false;
  assert.throws(() => executeReleaseTransaction(root, () => { mutated = true; }), /must not be a symlink: antigravity-plugins/);
  assert.equal(mutated, false);
  assert.equal(read(outside, 'marker.txt'), 'unchanged');
});

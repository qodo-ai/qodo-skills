import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { stampSkillProvenance } from '../scripts/skill-provenance.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const read = (path) => readFileSync(join(root, path), 'utf8').replace(/\r\n/g, '\n');
const json = (path) => JSON.parse(read(path));
const entries = (path) => readdirSync(join(root, path)).sort();
const catalog = json('distribution/catalog.json');

test('Copilot lists separate core and Standards packages with matching versions', () => {
  const marketplace = json('.github/plugin/marketplace.json');
  assert.equal(marketplace.name, 'qodo-copilot');
  assert.deepEqual(marketplace.plugins.map(({ name }) => name), ['qodo', 'qodo-standards']);
  assert.deepEqual(entries('copilot-plugins'), ['qodo', 'qodo-standards']);
  for (const entry of marketplace.plugins) {
    assert.equal(entry.source, `./copilot-plugins/${entry.name}`);
    const manifest = json(`${entry.source}/plugin.json`);
    assert.equal(manifest.$schema, 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json');
    for (const field of ['name', 'description', 'version']) assert.equal(manifest[field], entry[field]);
    assert.equal(manifest.version, catalog.package.version);
    assert.equal(manifest.license, 'MIT');
    assert.equal(read(`${entry.source}/LICENSE`), read('LICENSE'));
    assert.deepEqual(entries(entry.source), ['LICENSE', 'README.md', 'plugin.json', 'skills']);
    const pkg = catalog.installPackages.find(({ name }) => name === entry.name);
    assert.deepEqual(entries(`${entry.source}/skills`), [...pkg.skills].sort());
    for (const name of pkg.skills) {
      const { version } = catalog.skills.find((skill) => skill.name === name);
      const actual = read(`${entry.source}/skills/${name}/SKILL.md`);
      const canonical = read(`skills/${name}/SKILL.md`);
      assert.equal(actual, stampSkillProvenance(canonical, {
        name, version, packageName: pkg.name, distribution: 'marketplace', host: 'github-copilot',
      }));
      assert.ok(actual.includes(`--skill-version ${version} --distribution marketplace --host github-copilot`));
    }
  }
});

test('Copilot Standards packages marketplace guidance ahead of the verified enterprise procedure', () => {
  const guidance = read('copilot-plugins/qodo-standards/skills/qodo-get-rules/references/skill-updates.md');
  const [ownerGuidance, enterprise] = guidance.split('\n## Manual enterprise skill updates\n');
  assert.match(ownerGuidance, /use the host's update action for that exact plugin and marketplace/);
  assert.match(ownerGuidance, /the enterprise procedure only after verifying enterprise ownership/);
  assert.match(enterprise, /agents update --enterprise --dry-run --json/);
});

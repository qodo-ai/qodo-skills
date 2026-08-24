/** Verify that the direct bundle is complete and portable to any agent-owned skills root. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const bundle = JSON.parse(readFileSync(join(root, 'distribution', 'qodo-skills-direct.json'), 'utf8'));
const targetRoot = mkdtempSync(join(tmpdir(), 'qodo-agent-skills-'));

try {
  assert.equal(bundle.schemaVersion, 2);
  assert.equal(bundle.package.name, 'qodo');
  assert.equal(bundle.package.version, catalog.package.version);
  assert.deepEqual(
    bundle.skills.map((skill) => skill.name).sort(),
    catalog.skills.map((skill) => skill.name).sort(),
    'direct bundle must contain every canonical skill',
  );
  assert.deepEqual(bundle.packages, catalog.installPackages);
  const core = bundle.packages.find((entry) => entry.default);
  assert.equal(core.name, 'qodo');
  assert.equal(core.skills.includes('qodo-get-rules'), false);
  assert.equal(
    bundle.packages.find((entry) => entry.name === 'qodo-standards').skills.includes('qodo-get-rules'),
    true,
  );

  for (const skill of bundle.skills.filter((entry) => core.skills.includes(entry.name))) {
    for (const file of skill.files) {
      assert.ok(!file.path.includes('..') && !file.path.startsWith('/'));
      const target = join(targetRoot, skill.name, file.path);
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, file.content);
      assert.equal(
        createHash('sha256').update(readFileSync(target)).digest('hex'),
        file.sha256,
        `${skill.name}/${file.path} changed during projection`,
      );
    }
    const skillText = readFileSync(join(targetRoot, skill.name, 'SKILL.md'), 'utf8');
    assert.match(skillText, new RegExp(`^---[\\s\\S]*?^name: ${skill.name}$`, 'm'));
  }

  assert.equal(existsSync(join(targetRoot, 'qodo-get-rules', 'SKILL.md')), false);
  console.log(`Validated package-aware bundle with ${core.skills.length} default portable skills.`);
} finally {
  rmSync(targetRoot, { recursive: true, force: true });
}

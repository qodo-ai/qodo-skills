/** Verify that the direct bundle is complete and portable to any agent-owned skills root. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
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
  assert.equal(bundle.schemaVersion, 1);
  assert.equal(bundle.package.name, 'qodo');
  assert.equal(bundle.package.version, catalog.package.version);
  assert.deepEqual(
    bundle.skills.map((skill) => skill.name).sort(),
    catalog.skills.map((skill) => skill.name).sort(),
    'direct bundle must contain every canonical skill',
  );

  for (const skill of bundle.skills) {
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

  console.log(`Validated one agent-neutral bundle with ${bundle.skills.length} portable skills.`);
} finally {
  rmSync(targetRoot, { recursive: true, force: true });
}

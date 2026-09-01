/** Contract tests for the data-only CLI-managed compatibility bundle. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  assertSafeRelativePath,
  buildCliManagedBundle,
} from './build-cli-managed-bundle.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const { output, checksum, bundle } = buildCliManagedBundle(root);

assert.equal(bundle.schemaVersion, 1);
assert.equal(bundle.distribution, 'qodo-cli-managed');
assert.equal(bundle.packageVersion, JSON.parse(readFileSync(join(root, 'package.json'))).version);
assert.deepEqual(Object.keys(bundle.skills), [...Object.keys(bundle.skills)].sort());
assert.equal(readFileSync(join(root, 'distribution', 'qodo-cli-managed-bundle.json'), 'utf8'), output);
assert.equal(readFileSync(join(root, 'distribution', 'qodo-cli-managed-bundle.json.sha256'), 'utf8'), checksum);
assert.equal(
  checksum,
  `${createHash('sha256').update(output).digest('hex')}  qodo-cli-managed-bundle.json\n`,
);

for (const [name, skill] of Object.entries(bundle.skills)) {
  assert.ok(skill.files.length > 0, `${name}: files are required`);
  assert.ok(skill.files.some((file) => file.path === 'SKILL.md'), `${name}: SKILL.md is required`);
  for (const file of skill.files) {
    assertSafeRelativePath(file.path);
    assert.equal(file.encoding, 'base64');
    const payload = Buffer.from(file.content, 'base64');
    assert.equal(payload.toString('base64'), file.content, `${name}/${file.path}: canonical base64`);
    assert.equal(createHash('sha256').update(payload).digest('hex'), file.sha256);
    if (file.path === 'SKILL.md') {
      const markdown = payload.toString('utf8');
      assert.match(markdown, /^  distribution: "qodo-cli-managed"$/m);
      assert.match(markdown, /--distribution qodo-cli-managed(?=\s|$)/);
      assert.doesNotMatch(markdown, /^  distribution: "(?:skills-sh|marketplace|kiro-power)"$/m);
    }
  }
}

for (const unsafe of ['', '/absolute', '../escape', 'a/../escape', 'a//b', 'a\\b']) {
  assert.throws(() => assertSafeRelativePath(unsafe), /Unsafe CLI-managed bundle path/);
}

assert.equal(bundle.aliases['pre-pr-review'], 'qodo-review');
assert.equal(bundle.aliases['resolve-findings'], 'qodo-review-resolver');
assert.equal(bundle.skills['qodo-get-rules'].recommended, false);
assert.equal(bundle.skills['qodo-manage-standards'].recommended, false);
assert.equal(bundle.skills['qodo-setup'].recommended, true);

console.log('CLI-managed compatibility bundle contract is valid.');

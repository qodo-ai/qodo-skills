import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, 'skills/qodo-setup');
const read = (dir, path) => readFileSync(join(dir, path), 'utf8').replace(/\r\n/g, '\n');
const main = read(source, 'SKILL.md');
const references = [...main.matchAll(/\]\((references\/[^)]+\.md)\)/g)].map((match) => match[1]);

test('setup on-demand references survive every marketplace adapter', () => {
  assert.ok(references.length > 0, 'compact setup must link its conditional procedures');
  for (const adapter of ['packages/qodo', 'codex-packages/qodo', 'kiro-power']) {
    const installed = join(root, adapter, 'skills/qodo-setup');
    const entrypoint = read(installed, 'SKILL.md');
    // Leave room for generated host and lifecycle provenance above the 4000-byte source budget.
    assert.ok(Buffer.byteLength(entrypoint, 'utf8') <= 4096, `${adapter}: oversized setup entrypoint`);
    for (const reference of references) {
      assert.ok(entrypoint.includes(`](${reference})`), `${adapter}: reference is not discoverable`);
      assert.equal(read(installed, reference), read(source, reference), `${adapter}: missing/stale procedure`);
      // References are copied verbatim; exact version/host flags belong in the stamped entrypoint.
      assert.doesNotMatch(read(installed, reference), /--skill-version\s+\S+\s+--distribution/);
    }
  }
});

test('CLI-managed setup preserves on-demand reference contents', () => {
  const bundle = JSON.parse(read(root, 'distribution/qodo-cli-managed-bundle.json'));
  const files = new Map(bundle.skills['qodo-setup'].files.map((file) => [
    file.path, Buffer.from(file.content, file.encoding).toString('utf8'),
  ]));
  for (const reference of references) {
    assert.equal(files.get(reference), read(source, reference), `CLI-managed: ${reference}`);
  }
});

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = readFileSync(join(root, 'skills/qodo-review/references/cli-execution.md'), 'utf8');
const recipe = source.match(/```sh\n(QODO_REVIEW_TMP=[\s\S]*?)\n```/)?.[1];
assert.ok(recipe, 'Collection recipe must remain inspectable');
const setupEnd = recipe.indexOf('cleanup_qodo_review');
assert.ok(setupEnd > 0, 'Setup-only tests must stop before cleanup, redirection and collection');
const setup = recipe.slice(0, setupEnd);

test('collection setup stops before redirection when temporary allocation fails or returns an invalid path',
  { skip: process.platform === 'win32' }, () => {
    // Execute only setup plus a harmless marker, never the redirect/cleanup/CLI loop.
    for (const mock of ['return 1', 'return 0', 'printf "%s" "/nonexistent-qodo-fixture-path"; return 0']) {
      const result = spawnSync('sh', ['-c', `mktemp() { ${mock}; }\n${setup}\nprintf 'REACHED\\n'\n`], { encoding: 'utf8' });
      assert.equal(result.error, undefined);
      assert.equal(result.status, 1);
      assert.equal(result.stdout, '', 'Setup failure must not reach any later command');
    }
  });

test('successful collection setup retains its verified unique directory',
  { skip: process.platform === 'win32' }, () => {
    const directory = mkdtempSync(join(tmpdir(), 'qodo-shell-setup-'));
    try {
      const result = spawnSync('sh', ['-c', `mktemp() { printf '%s' "$TEST_RUN_DIRECTORY"; }\n${setup}\nprintf '%s' "$QODO_REVIEW_TMP"`],
        { encoding: 'utf8', env: { ...process.env, TEST_RUN_DIRECTORY: directory } });
      assert.equal(result.error, undefined);
      assert.equal(result.status, 0);
      assert.equal(result.stdout, directory);
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });

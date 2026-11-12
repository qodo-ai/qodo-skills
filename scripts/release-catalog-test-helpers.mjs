/** Exercise complete optional packages through the standard release publisher. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildEnterpriseBundle } from './build-enterprise-bundle.mjs';
import { writeRepositoryCatalog } from './build-repository-catalog.mjs';
import { buildReleaseIndexFixture } from './release-index-test-helpers.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const name = 'qodo-repository-catalog.json';

export function buildStandardReleaseAssets(source, index, output, commit) {
  buildReleaseIndexFixture(source, index, commit);
  buildEnterpriseBundle({ output, commit, releaseIndex: join(index, 'qodo-skills-index.json') });
  writeRepositoryCatalog(root, commit, output);
}

export function assertRepositoryCatalogFailures({ checkout, enterpriseDir, publishEnv, publishPath, runShell }) {
  const path = join(enterpriseDir, name);
  const original = readFileSync(path);
  const checksum = readFileSync(`${path}.sha256`);
  try {
    unlinkSync(path);
    assert.throws(() => runShell(checkout, publishPath, publishEnv), /Release asset is missing/);
    const changed = Buffer.from(JSON.stringify({ ...JSON.parse(original), sourceCommit: '0'.repeat(40) }));
    writeFileSync(path, changed);
    writeFileSync(`${path}.sha256`, `${createHash('sha256').update(changed).digest('hex')}  ${name}\n`);
    assert.throws(() => runShell(checkout, publishPath, publishEnv), /repository catalog identity/);
    writeFileSync(path, original);
    assert.throws(() => runShell(checkout, publishPath, publishEnv));
  } finally {
    writeFileSync(path, original);
    writeFileSync(`${path}.sha256`, checksum);
  }
}

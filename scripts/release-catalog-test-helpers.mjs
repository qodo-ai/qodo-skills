/** Exercise complete optional packages through the standard release publisher. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildEnterpriseBundle } from './build-enterprise-bundle.mjs';
import { writeRepositoryCatalog } from './build-repository-catalog.mjs';
import { buildReleaseIndexFixture } from './release-index-test-helpers.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const name = 'qodo-repository-catalog.json';

export function copyCapturedSkillFixture(checkout) {
  const files = execFileSync('git', ['ls-files', '-z', '--', 'skills'], { cwd: root, encoding: 'utf8' });
  for (const file of files.split('\0').filter(Boolean)) {
    mkdirSync(dirname(join(checkout, file)), { recursive: true });
    copyFileSync(join(root, file), join(checkout, file));
  }
  const skill = join(checkout, 'skills/qodo-agent-session-review/SKILL.md');
  writeFileSync(skill, readFileSync(skill, 'utf8') + '\nCaptured release fixture, different from the automation checkout.\n');
}

export function buildStandardReleaseAssets(source, index, output, commit) {
  buildReleaseIndexFixture(source, index, commit);
  buildEnterpriseBundle({ output, commit, releaseIndex: join(index, 'qodo-skills-index.json') });
  writeRepositoryCatalog(source, commit, output);
  const payload = JSON.parse(readFileSync(join(output, name)));
  const skill = payload.skills.find((entry) => entry.name === 'qodo-agent-session-review');
  const packaged = skill.files.find((file) => file.path === 'SKILL.md');
  assert.deepEqual(Buffer.from(packaged.content, 'base64'),
    readFileSync(join(source, 'skills/qodo-agent-session-review/SKILL.md')));
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
    assert.throws(() => runShell(checkout, publishPath, publishEnv), /checksum|did NOT match|FAILED/i);
  } finally {
    writeFileSync(path, original);
    writeFileSync(`${path}.sha256`, checksum);
  }
}

export function assertCatalogPublication(state) {
  assert.ok(state.assets.includes(name));
  assert.ok(state.assets.includes(`${name}.sha256`));
  return state;
}

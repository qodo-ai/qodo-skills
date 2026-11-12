/** Exercise complete optional packages through the standard release publisher. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
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
  assertLegacyCatalogRecovery({ checkout, publishEnv, publishPath, runShell });
}

function assertLegacyCatalogRecovery({ checkout, publishEnv, publishPath, runShell }) {
  const git = (...args) => execFileSync('git', args, { cwd: checkout, encoding: 'utf8', stdio: 'pipe' }).trim();
  const original = publishEnv.GITHUB_SHA;
  const scratch = mkdtempSync(join(dirname(checkout), 'legacy-release-'));
  const source = join(scratch, 'source'), output = join(scratch, 'assets'), index = join(scratch, 'index');
  const tag = `v${JSON.parse(readFileSync(join(checkout, 'distribution/catalog.json'))).package.version}`;
  let tagged = false;
  try {
    // Only the captured source differs: the running automation keeps the new publisher.
    writeFileSync(join(checkout, 'scripts/publish-release.sh'), '#!/usr/bin/env bash\n# Historical publisher fixture.\n');
    git('add', 'scripts/publish-release.sh');
    const legacy = git('commit-tree', git('write-tree'), '-p', original, '-m', 'historical release inventory');
    const automation = git('commit-tree', `${original}^{tree}`, '-p', legacy, '-m', 'new release automation');
    git('reset', '--hard', automation);
    git('push', '--force', 'origin', `${automation}:refs/heads/main`);
    git('worktree', 'add', '--detach', source, legacy);
    buildStandardReleaseAssets(source, index, output, legacy);
    for (const file of [name, `${name}.sha256`]) unlinkSync(join(output, file));
    for (const file of ['qodo-cli-managed-bundle.json', 'qodo-cli-managed-bundle.json.sha256'])
      copyFileSync(join(source, 'distribution', file), join(output, file));
    for (const file of ['qodo-skills-index.json', 'qodo-skills-index.json.sha256'])
      copyFileSync(join(index, file), join(output, file));
    const statePath = join(scratch, 'state.json');
    writeFileSync(statePath, JSON.stringify({ exists: true, draft: false, immutable: true,
      assets: readdirSync(output), downloads: 0, edits: 1 }));
    git('tag', '--no-sign', '-a', tag, '-m', 'historical tag', legacy); tagged = true;
    git('push', 'origin', `refs/tags/${tag}:refs/tags/${tag}`);
    const env = { ...publishEnv, GITHUB_SHA: automation, QODO_RELEASE_COMMIT: legacy,
      QODO_RELEASE_SOURCE_DIR: source, QODO_RELEASE_INDEX_DIR: index, QODO_ENTERPRISE_RELEASE_DIR: output,
      FAKE_GH_STATE: statePath, FAKE_GH_ASSETS: output };
    runShell(checkout, publishPath, env);
    runShell(checkout, publishPath, env);
    const verified = JSON.parse(readFileSync(statePath));
    assert.equal(verified.edits, 1, 'historical retries must not republish');
    assert.ok(!verified.assets.includes(name));
    assert.ok(verified.downloads > 0, 'historical bytes must still be downloaded and verified');
  } finally {
    if (tagged) { git('push', 'origin', `:refs/tags/${tag}`); git('tag', '-d', tag); }
    if (existsSync(source)) git('worktree', 'remove', source);
    git('reset', '--hard', original);
    git('push', '--force', 'origin', `${original}:refs/heads/main`);
  }
}

export function assertCatalogPublication(state) {
  assert.ok(state.assets.includes(name));
  assert.ok(state.assets.includes(`${name}.sha256`));
  return state;
}

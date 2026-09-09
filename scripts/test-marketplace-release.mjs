/** Test marketplace selection, packaging, provider verification, and workflow gates. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { delimiter, join } from 'node:path';
import { tmpdir } from 'node:os';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  prepareMarketplace,
  resolveSelection,
  verifyClaudeDocument,
  verifyKiroDocument,
} from './marketplace-release.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const releasePreflight = readFileSync(join(root, 'scripts', 'verify-release-prerequisites.sh'), 'utf8');
const version = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).version;
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const context = {
  tag: `v${version}`,
  version,
  commit: '0123456789abcdef0123456789abcdef01234567',
  release: {},
};

function storedZipEntries(path) {
  const archive = readFileSync(path);
  const entries = new Map();
  let offset = 0;
  while (archive.readUInt32LE(offset) === 0x04034b50) {
    assert.equal(archive.readUInt16LE(offset + 8), 0, 'provider bundle entries must use stored mode');
    const size = archive.readUInt32LE(offset + 18);
    const nameLength = archive.readUInt16LE(offset + 26);
    const extraLength = archive.readUInt16LE(offset + 28);
    const nameStart = offset + 30;
    const dataStart = nameStart + nameLength + extraLength;
    const name = archive.subarray(nameStart, nameStart + nameLength).toString('utf8');
    entries.set(name, archive.subarray(dataStart, dataStart + size));
    offset = dataStart + size;
  }
  assert.equal(archive.readUInt32LE(offset), 0x02014b50, 'local entries must end at the central directory');
  return entries;
}

function verifyPacketFails(output, pattern) {
  const result = spawnSync(process.execPath, ['verify-codex-packet.mjs'], {
    cwd: output, encoding: 'utf8', timeout: 5_000,
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, pattern);
}

assert.deepEqual(
  resolveSelection({ claude: 'true', codex: false, kiro: true, all: false }),
  ['claude', 'kiro'],
);
assert.deepEqual(resolveSelection({ all: true }), ['claude', 'codex', 'kiro']);
assert.throws(() => resolveSelection({}), /Select at least one marketplace/);

const claudeDocument = {
  renames: { 'qodo-skills': 'qodo' },
  plugins: [
    {
      name: 'qodo',
      source: {
        source: 'git-subdir',
        url: 'https://github.com/qodo-ai/qodo-skills.git',
        path: 'packages/qodo',
        ref: 'main',
        sha: context.commit,
      },
    },
    {
      name: 'qodo-standards',
      source: {
        source: 'git-subdir',
        url: 'https://github.com/qodo-ai/qodo-skills.git',
        path: 'packages/qodo-standards',
        ref: 'main',
        sha: context.commit,
      },
    },
  ],
};
assert.equal(verifyClaudeDocument(claudeDocument, context).length, 2);
assert.throws(
  () => verifyClaudeDocument({ plugins: [claudeDocument.plugins[0]] }, context),
  /preserve the qodo-skills to qodo rename/,
);
assert.throws(
  () => verifyClaudeDocument({ renames: claudeDocument.renames, plugins: [claudeDocument.plugins[0]] }, context),
  /missing qodo-standards/,
);
assert.throws(
  () => verifyClaudeDocument({ renames: claudeDocument.renames, plugins: [{
    ...claudeDocument.plugins[0],
    source: { ...claudeDocument.plugins[0].source, path: '.' },
  }, claudeDocument.plugins[1]] }, context),
  /expected path packages\/qodo/,
);

const kiroDocument = JSON.stringify({
  powers: [
    {
      name: 'qodo',
      repositoryUrl: 'https://github.com/qodo-ai/qodo-skills/tree/main/kiro-power',
      repositoryCloneUrl: 'git@github.com:qodo-ai/qodo-skills.git',
      pathInRepo: 'kiro-power',
      repositoryBranch: 'main',
    },
    {
      name: 'qodo-standards',
      repositoryUrl: 'https://github.com/qodo-ai/qodo-skills/tree/main/kiro-power-standards',
      repositoryCloneUrl: 'git@github.com:qodo-ai/qodo-skills.git',
      pathInRepo: 'kiro-power-standards',
      repositoryBranch: 'main',
    },
  ],
});
const kiroResults = verifyKiroDocument(kiroDocument, context);
assert.equal(kiroResults.length, 2);
assert.equal(kiroResults[0].branch, 'main');
assert.equal(kiroResults[0].commit, undefined);
assert.throws(() => verifyKiroDocument('{}', context), /Kiro qodo/);
assert.throws(() => verifyKiroDocument(JSON.stringify({
  powers: [
    { name: 'qodo', repositoryUrl: 'https://github.com/qodo-ai/qodo-skills/tree/main/kiro-power' },
    { pathInRepo: 'kiro-power', repositoryBranch: 'main' },
  ],
}), context), /Kiro qodo/);

const temporaryRoot = mkdtempSync(join(tmpdir(), 'qodo-marketplace-release-'));
try {
  const output = join(temporaryRoot, 'packet');
  const prepared = prepareMarketplace('codex', context, output);
  const release = JSON.parse(readFileSync(join(prepared.output, 'release.json'), 'utf8'));
  assert.equal(release.providerMode, 'reviewed-portal-snapshot');
  assert.equal(release.listings.length, 2);
  assert.equal(release.artifacts.length, 2);
  assert.match(readFileSync(join(prepared.output, 'SUBMISSION.md'), 'utf8'), /protected GitHub environment approval/);
  assert.match(readFileSync(join(prepared.output, 'SUBMISSION.md'), 'utf8'), /Privacy:/);
  assert.ok(readFileSync(join(prepared.output, 'SUBMISSION.md'), 'utf8').includes(`qodo-codex-plugin-${version}.zip`));
  assert.equal(
    JSON.parse(readFileSync(join(prepared.output, 'listings', 'qodo', '.codex-plugin', 'plugin.json'), 'utf8')).name,
    'qodo',
  );
  const codexSkill = readFileSync(
    join(prepared.output, 'listings', 'qodo', 'skills', 'qodo-codebase-wisdom', 'SKILL.md'),
    'utf8',
  );
  const wisdomVersion = catalog.skills.find((skill) => skill.name === 'qodo-codebase-wisdom').version;
  assert.ok(
    codexSkill.includes(`--skill qodo-codebase-wisdom --skill-version ${wisdomVersion} --distribution marketplace --host codex`),
    'the Codex package must carry the catalog skill version and host provenance',
  );
  assert.match(codexSkill, /instruction_mode: "embedded"/);
  assert.match(codexSkill, /## Handle a skill update notice/);
  assert.doesNotMatch(codexSkill, /qodo help workflow/);
  const coreSubmission = JSON.parse(readFileSync(join(prepared.output, 'submissions', 'qodo.json'), 'utf8'));
  const standardsSubmission = JSON.parse(readFileSync(join(prepared.output, 'submissions', 'qodo-standards.json'), 'utf8'));
  assert.equal(coreSubmission.releaseType, 'initial');
  assert.equal(standardsSubmission.releaseType, 'initial');
  assert.equal(coreSubmission.artifact.listingId, 'qodo');
  assert.equal(standardsSubmission.artifact.listingId, 'qodo-standards');
  assert.equal(coreSubmission.positiveTests.length, 5);
  assert.equal(coreSubmission.negativeTests.length, 3);
  assert.equal(standardsSubmission.positiveTests.length, 5);
  assert.equal(standardsSubmission.negativeTests.length, 3);
  assert.equal(coreSubmission.listing.starterPrompts.length, 3);
  assert.equal(standardsSubmission.listing.starterPrompts.length, 2);
  assert.ok(!JSON.stringify(coreSubmission).includes('password'));
  const coreArchivePath = join(prepared.output, coreSubmission.artifact.path);
  const coreArchive = readFileSync(coreArchivePath);
  assert.equal(createHash('sha256').update(coreArchive).digest('hex'), coreSubmission.artifact.sha256);
  assert.ok(readFileSync(join(prepared.output, 'bundles', 'SHA256SUMS'), 'utf8')
    .split('\n').includes(`${coreSubmission.artifact.sha256}  qodo-codex-plugin-${version}.zip`));
  for (const line of readFileSync(join(prepared.output, 'bundles', 'SHA256SUMS'), 'utf8').trim().split('\n')) {
    const match = line.match(/^([0-9a-f]{64})  ([a-z0-9.-]+\.zip)$/);
    assert.ok(match, `invalid checksum record: ${line}`);
    assert.equal(
      createHash('sha256').update(readFileSync(join(prepared.output, 'bundles', match[2]))).digest('hex'),
      match[1],
    );
  }
  const packetVerification = spawnSync(process.execPath, ['verify-codex-packet.mjs'], {
    cwd: prepared.output,
    encoding: 'utf8',
    timeout: 5_000,
  });
  assert.equal(packetVerification.status, 0, packetVerification.stderr);
  assert.equal(JSON.parse(packetVerification.stdout).verified.length, 2);
  const coreEntries = storedZipEntries(coreArchivePath);
  assert.deepEqual(
    coreEntries.get('.codex-plugin/plugin.json'),
    readFileSync(join(prepared.output, 'listings', 'qodo', '.codex-plugin', 'plugin.json')),
  );
  assert.ok(coreEntries.has('skills/qodo-review/SKILL.md'));
  assert.ok(!coreEntries.has('skills/qodo-get-rules/SKILL.md'));
  assert.ok(!coreEntries.has('skills/find-skills/SKILL.md'));
  const standardsEntries = storedZipEntries(join(prepared.output, standardsSubmission.artifact.path));
  assert.ok(standardsEntries.has('skills/qodo-get-rules/SKILL.md'));
  assert.ok(!standardsEntries.has('skills/qodo-review/SKILL.md'));

  const repeat = prepareMarketplace('codex', context, join(temporaryRoot, 'repeat'));
  for (const artifact of release.artifacts) {
    assert.deepEqual(
      readFileSync(join(prepared.output, artifact.path)),
      readFileSync(join(repeat.output, artifact.path)),
      `${artifact.listingId} provider bundle must be byte-for-byte deterministic`,
    );
  }
  const repeatSubmissionPath = join(repeat.output, 'submissions', 'qodo.json');
  const repeatSubmission = JSON.parse(readFileSync(repeatSubmissionPath, 'utf8'));
  repeatSubmission.artifact.sha256 = '0'.repeat(64);
  writeFileSync(repeatSubmissionPath, `${JSON.stringify(repeatSubmission, null, 2)}\n`);
  verifyPacketFails(repeat.output, /submission artifact metadata mismatch/);

  const incomplete = prepareMarketplace('codex', context, join(temporaryRoot, 'incomplete'));
  const incompleteReleasePath = join(incomplete.output, 'release.json');
  const incompleteRelease = JSON.parse(readFileSync(incompleteReleasePath, 'utf8'));
  const removedArtifact = incompleteRelease.artifacts.pop();
  writeFileSync(incompleteReleasePath, `${JSON.stringify(incompleteRelease, null, 2)}\n`);
  rmSync(join(incomplete.output, removedArtifact.path));
  rmSync(join(incomplete.output, 'submissions', `${removedArtifact.listingId}.json`));
  const checksumPath = join(incomplete.output, 'bundles', 'SHA256SUMS');
  const retainedChecksums = readFileSync(checksumPath, 'utf8')
    .split('\n')
    .filter((line) => line && !line.endsWith(`  ${removedArtifact.path.slice('bundles/'.length)}`));
  writeFileSync(checksumPath, `${retainedChecksums.join('\n')}\n`);
  verifyPacketFails(incomplete.output, /exactly one artifact per Codex listing/);

  const swapped = prepareMarketplace('codex', context, join(temporaryRoot, 'swapped'));
  const swappedReleasePath = join(swapped.output, 'release.json');
  const swappedRelease = JSON.parse(readFileSync(swappedReleasePath, 'utf8'));
  const [firstArtifact, secondArtifact] = swappedRelease.artifacts;
  [firstArtifact.listingId, secondArtifact.listingId] = [secondArtifact.listingId, firstArtifact.listingId];
  writeFileSync(swappedReleasePath, `${JSON.stringify(swappedRelease, null, 2)}\n`);
  for (const artifact of swappedRelease.artifacts) {
    const submissionPath = join(swapped.output, 'submissions', `${artifact.listingId}.json`);
    const submission = JSON.parse(readFileSync(submissionPath, 'utf8'));
    submission.listingId = artifact.listingId;
    submission.artifact = artifact;
    writeFileSync(submissionPath, `${JSON.stringify(submission, null, 2)}\n`);
  }
  verifyPacketFails(swapped.output, /internal plugin identity does not match/);
  assert.throws(() => prepareMarketplace('codex', context, output), /already exists/);
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}

const workflow = readFileSync(join(root, '.github', 'workflows', 'ship-marketplaces.yml'), 'utf8');
for (const input of ['all', 'claude', 'codex', 'kiro']) {
  assert.match(workflow, new RegExp(`\\n      ${input}:`));
}
assert.ok((workflow.match(/type: boolean/g) ?? []).length >= 4);
assert.match(workflow, /fromJSON\(needs\.plan\.outputs\.matrix\)/);
assert.match(workflow, /has_verifiable/);
assert.match(workflow, /name: marketplace-codex/);
assert.match(workflow, /node verify-codex-packet\.mjs/);
assert.match(workflow, /Update the existing `qodo` listing/);
assert.match(workflow, /qodo-standards.*optional initial listing/);
assert.match(workflow, /name: marketplace-\$\{\{ matrix\.provider \}\}/);
assert.match(workflow, /required_reviewers/);
assert.match(workflow, /ship-provider:/);
assert.doesNotMatch(workflow, /verify-provider-visible|marketplace-release\.mjs verify|continue-on-error/);
assert.match(workflow, /awaiting provider verification/);
assert.match(workflow, /group: qodo-marketplace-provider-\$\{\{ matrix\.provider \}\}/);
assert.match(workflow, /group: qodo-marketplace-provider-[\s\S]*?cancel-in-progress: false/);
assert.match(workflow, /group: qodo-marketplaces-\$\{\{ inputs\.release_tag \}\}/);
assert.match(workflow, /run-name: Ship marketplaces \$\{\{ inputs\.release_tag \}\}/);
assert.match(workflow, /marketplace-release-lock\.mjs acquire/);
assert.match(workflow, /marketplace-release-lock\.mjs release/);
assert.equal(
  (workflow.match(/github\.ref == format\('refs\/heads\/\{0\}', github\.event\.repository\.default_branch\)/g) ?? []).length,
  2,
  'both write-scoped lock jobs must reject workflow dispatches from mutable non-default refs',
);
assert.match(workflow, /always\(\)[\s\S]*?github\.repository[\s\S]*?github\.ref == format/);
assert.doesNotMatch(workflow, /OPENAI_API_KEY|ANTHROPIC_API_KEY/);
const trustedCheckout = workflow.indexOf('Check out trusted release automation');
const lockAcquisition = workflow.indexOf('Acquire the cross-tag marketplace release lock');
const preflight = workflow.indexOf('Verify immutable release before executing release code');
const releaseCheckout = workflow.indexOf('Check out immutable release automation');
const preparationCheckout = workflow.indexOf('Check out the immutable release');
const validationInstall = workflow.indexOf('Install locked validation dependencies', preparationCheckout);
const canonicalValidation = workflow.indexOf('Validate canonical source and generated adapters', preparationCheckout);
assert.ok(trustedCheckout >= 0 && lockAcquisition > trustedCheckout && preflight > lockAcquisition);
assert.ok(releaseCheckout > preflight);
assert.ok(validationInstall > preparationCheckout && canonicalValidation > validationInstall);
assert.match(workflow, /npm ci --ignore-scripts --no-audit --no-fund/);
const preparationToolCheck = workflow.indexOf('Verify required preparation tools');
const preparationInstall = workflow.indexOf('npm ci --ignore-scripts --no-audit --no-fund');
assert.ok(
  preparationToolCheck >= 0 && preparationToolCheck < preparationInstall,
  'marketplace preparation must verify required tools before invoking npm',
);
assert.match(workflow, /for tool in git gh node npm; do/);
assert.match(workflow, /\.immutable'\)" = 'true'/);
assert.match(workflow, /release_tag must be an exact stable semver tag/);
assert.doesNotMatch(workflow, /SOURCE_REF:|QODO_RELEASE_ADMIN_TOKEN|QODO_SKILLS_RELEASE_APP|create-github-app-token|git\/refs/);
assert.match(workflow, /approved provider handoff succeeded/);

const protectionAudit = readFileSync(join(root, 'scripts', 'audit-release-protections.sh'), 'utf8');
assert.doesNotMatch(protectionAudit, /\.can_admins_bypass/);
assert.doesNotMatch(protectionAudit, /prevent_self_review/);
assert.doesNotMatch(protectionAudit, /deployment-branch-policies/);
assert.match(protectionAudit, /\.type == "required_reviewers"/);
assert.match(protectionAudit, /QODO_SKILLS_RELEASE_APP_PRIVATE_KEY/);
assert.match(protectionAudit, /\.permissions == \{"administration":"read","contents":"write","metadata":"read"\}/);
assert.match(protectionAudit, /orgs\/qodo-ai\/installations\?per_page=100/);
assert.match(protectionAudit, /repository_selection/);
assert.doesNotMatch(protectionAudit, /user\/installations/);
assert.match(releasePreflight, /installation\/repositories\?per_page=100/);
assert.doesNotMatch(protectionAudit, /refs\/heads\/marketplace-kiro|Kiro marketplace release/);
assert.match(readFileSync(join(root, 'scripts', 'audit-release-protections.cmd'), 'utf8'),
  /bash "%~dp0audit-release-protections\.sh"/);

if (process.platform !== 'win32') {
  const bashProbe = spawnSync('bash', ['--version'], { encoding: 'utf8', timeout: 5_000 });
  const jqProbe = spawnSync('jq', ['--version'], { encoding: 'utf8', timeout: 5_000 });
  for (const probe of [bashProbe, jqProbe]) {
    if (probe.error && probe.error.code !== 'ENOENT') throw probe.error;
  }
  if (!bashProbe.error && !jqProbe.error) {
    const preflightFixture = mkdtempSync(join(tmpdir(), 'qodo-kiro-preflight-'));
    try {
      const bin = join(preflightFixture, 'bin');
      mkdirSync(bin);
      const ghStub = join(bin, 'gh');
      writeFileSync(ghStub, `#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == "api /apps/qodo-skills-release-bot" ]]; then
  printf '{"id":12345,"slug":"qodo-skills-release-bot","owner":{"login":"qodo-ai"},"permissions":{"administration":"read","contents":"write","metadata":"read"}}\\n'
elif [[ "$*" == *"immutable-releases --jq .enabled"* ]]; then
  printf '%s\\n' "\${QODO_TEST_IMMUTABLE_RELEASES:-true}"
elif [[ "$*" == "api repos/qodo-ai/qodo-skills/environments/marketplace-kiro" ]]; then
  if [[ "\${QODO_TEST_MISSING_REVIEWER:-}" == 1 ]]; then
    printf '{"can_admins_bypass":true,"deployment_branch_policy":{"protected_branches":true,"custom_branch_policies":false},"protection_rules":[]}\\n'
  else
    printf '{"can_admins_bypass":true,"deployment_branch_policy":{"protected_branches":true,"custom_branch_policies":false},"protection_rules":[{"type":"required_reviewers","prevent_self_review":false,"reviewers":[{}]}]}\\n'
  fi
elif [[ "$*" == *"variables/QODO_SKILLS_RELEASE_APP_ID --jq .value"* ]]; then
  printf '%s\\n' "\${QODO_TEST_ENVIRONMENT_APP_ID:-12345}"
elif [[ "$*" == *"environments/marketplace-kiro/secrets --jq"* ]]; then
  printf 'true\\n'
elif [[ "$*" == *"orgs/qodo-ai/installations?per_page=100"* ]]; then
  if [[ "\${QODO_TEST_MISSING_INSTALLATION:-}" != 1 ]]; then
    printf '99\\t%s\\tread\\twrite\\tread\\n' "\${QODO_TEST_INSTALLATION_SELECTION:-selected}"
  fi
elif [[ "$*" == *"installation/repositories?per_page=100"* ]]; then
  printf '%s\\n' "\${QODO_TEST_INSTALLATION_REPOSITORIES:-qodo-ai/qodo-skills}"
elif [[ "$*" == *"rulesets?per_page=100"* ]]; then
  [[ "$*" == *"Immutable release tags"* ]] || exit 2
  printf '%s\\n' 78
elif [[ "$*" == "api repos/qodo-ai/qodo-skills/rulesets/78" ]]; then
  if [[ "\${QODO_TEST_OMIT_BYPASS:-}" == 1 ]]; then
    printf '{"id":78,"conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},"rules":[{"type":"update"},{"type":"deletion"}]}\\n'
  else
    printf '{"id":78,"conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},"rules":[{"type":"update"},{"type":"deletion"}],"bypass_actors":[]}\\n'
  fi
else
  printf 'unexpected gh invocation: %s\\n' "$*" >&2
  exit 2
fi
`);
      chmodSync(ghStub, 0o755);
      const preflightEnvironment = {
        ...process.env,
        PATH: `${bin}${delimiter}${process.env.PATH ?? ''}`,
        GH_TOKEN: 'test-token',
        GITHUB_REPOSITORY: 'qodo-ai/qodo-skills',
        QODO_SKILLS_RELEASE_APP_ID: '12345',
      };
      const auditEnvironment = { ...preflightEnvironment };
      delete auditEnvironment.QODO_SKILLS_RELEASE_APP_ID;
      const validAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: auditEnvironment, timeout: 5_000,
      });
      assert.equal(validAudit.status, 0, validAudit.stderr);
      assert.match(validAudit.stdout, /app_id=12345 tag_ruleset=78/);
      const missingInstallationAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: { ...auditEnvironment, QODO_TEST_MISSING_INSTALLATION: '1' }, timeout: 5_000,
      });
      assert.equal(missingInstallationAudit.status, 1, missingInstallationAudit.stderr);
      assert.match(missingInstallationAudit.stderr, /exactly one active qodo-ai installation/);
      const allRepositoriesAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: { ...auditEnvironment, QODO_TEST_INSTALLATION_SELECTION: 'all' }, timeout: 5_000,
      });
      assert.equal(allRepositoriesAudit.status, 1, allRepositoriesAudit.stderr);
      assert.match(allRepositoriesAudit.stderr, /selected-repository access/);
      const wrongRepositoryPreflight = spawnSync('bash', [join(root, 'scripts', 'verify-release-prerequisites.sh')], {
        encoding: 'utf8', env: { ...preflightEnvironment, QODO_TEST_INSTALLATION_REPOSITORIES: 'qodo-ai/other' }, timeout: 5_000,
      });
      assert.equal(wrongRepositoryPreflight.status, 1, wrongRepositoryPreflight.stderr);
      assert.match(wrongRepositoryPreflight.stderr, /installed on qodo-ai\/qodo-skills and no other repository/);
      const missingReviewerAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: { ...auditEnvironment, QODO_TEST_MISSING_REVIEWER: '1' }, timeout: 5_000,
      });
      assert.equal(missingReviewerAudit.status, 1, missingReviewerAudit.stderr);
      assert.match(missingReviewerAudit.stderr, /at least one release reviewer/);
      const mutableReleaseAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: { ...auditEnvironment, QODO_TEST_IMMUTABLE_RELEASES: 'false' }, timeout: 5_000,
      });
      assert.equal(mutableReleaseAudit.status, 1, mutableReleaseAudit.stderr);
      assert.match(mutableReleaseAudit.stderr, /Release immutability is disabled/);
      const hiddenBypassAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: { ...auditEnvironment, QODO_TEST_OMIT_BYPASS: '1' }, timeout: 5_000,
      });
      assert.equal(hiddenBypassAudit.status, 1, hiddenBypassAudit.stderr);
      assert.match(hiddenBypassAudit.stderr, /Immutable release tags/);
    } finally {
      rmSync(preflightFixture, { recursive: true, force: true });
    }
  }
}

console.log('Marketplace release workflow tests passed.');

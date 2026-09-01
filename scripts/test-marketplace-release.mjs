/** Test marketplace selection, packaging, provider verification, and workflow gates. */
import assert from 'node:assert/strict';
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
const context = {
  tag: 'v1.0.2',
  version: '1.0.2',
  commit: '0123456789abcdef0123456789abcdef01234567',
  release: {},
};

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
      repositoryUrl: 'https://github.com/qodo-ai/qodo-skills/tree/marketplace-kiro/kiro-power',
      pathInRepo: 'kiro-power',
      repositoryBranch: 'marketplace-kiro',
    },
    {
      name: 'qodo-standards',
      repositoryUrl: 'https://github.com/qodo-ai/qodo-skills/tree/marketplace-kiro/kiro-power-standards',
      pathInRepo: 'kiro-power-standards',
      repositoryBranch: 'marketplace-kiro',
    },
  ],
});
const kiroResults = verifyKiroDocument(kiroDocument, context);
assert.equal(kiroResults.length, 2);
assert.equal(kiroResults[0].branch, 'marketplace-kiro');
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
  assert.match(readFileSync(join(prepared.output, 'SUBMISSION.md'), 'utf8'), /protected GitHub environment approval/);
  assert.match(readFileSync(join(prepared.output, 'SUBMISSION.md'), 'utf8'), /Privacy:/);
  assert.equal(
    JSON.parse(readFileSync(join(prepared.output, 'listings', 'qodo', '.codex-plugin', 'plugin.json'), 'utf8')).name,
    'qodo',
  );
  const codexSkill = readFileSync(
    join(prepared.output, 'listings', 'qodo', 'skills', 'qodo-codebase-wisdom', 'SKILL.md'),
    'utf8',
  );
  assert.match(
    codexSkill,
    /--skill qodo-codebase-wisdom --skill-version 1\.1\.2 --distribution marketplace --host codex/,
  );
  assert.match(codexSkill, /instruction_mode: "embedded"/);
  assert.match(codexSkill, /## Handle a skill update notice/);
  assert.doesNotMatch(codexSkill, /qodo help workflow/);
  const coreSubmission = JSON.parse(readFileSync(join(prepared.output, 'submissions', 'qodo.json'), 'utf8'));
  const standardsSubmission = JSON.parse(readFileSync(join(prepared.output, 'submissions', 'qodo-standards.json'), 'utf8'));
  assert.equal(coreSubmission.releaseType, 'update');
  assert.equal(standardsSubmission.releaseType, 'initial');
  assert.equal(coreSubmission.positiveTests.length, 5);
  assert.equal(coreSubmission.negativeTests.length, 3);
  assert.equal(standardsSubmission.positiveTests.length, 5);
  assert.equal(standardsSubmission.negativeTests.length, 3);
  assert.equal(coreSubmission.listing.starterPrompts.length, 4);
  assert.equal(standardsSubmission.listing.starterPrompts.length, 2);
  assert.ok(!JSON.stringify(coreSubmission).includes('password'));
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
assert.match(workflow, /name: marketplace-\$\{\{ matrix\.provider \}\}/);
assert.match(workflow, /required_reviewers/);
assert.match(workflow, /verify-provider-visible/);
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
assert.match(workflow, /SOURCE_REF: marketplace-kiro/);
assert.doesNotMatch(workflow, /QODO_RELEASE_ADMIN_TOKEN/);
assert.match(workflow, /QODO_SKILLS_RELEASE_APP_ID/);
assert.match(workflow, /QODO_SKILLS_RELEASE_APP_PRIVATE_KEY/);
assert.match(workflow, /actions\/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1/);
assert.match(workflow, /owner: qodo-ai/);
assert.match(workflow, /repositories: qodo-skills/);
assert.match(workflow, /permission-administration: read/);
assert.match(workflow, /permission-contents: write/);
assert.match(workflow, /id: kiro-installation-audit-token/);
assert.match(workflow, /steps\.kiro-installation-audit-token\.outputs\.token/);
assert.match(workflow, /Verify Kiro release App installation scope/);
assert.match(workflow, /steps\.kiro-release-token\.outputs\.token/);
assert.match(workflow, /verify-kiro-release-source\.sh/);
assert.match(workflow, /-F force=false/);
const kiroSourcePreflight = readFileSync(join(root, 'scripts', 'verify-kiro-release-source.sh'), 'utf8');
assert.match(kiroSourcePreflight, /Kiro marketplace release/);
assert.match(kiroSourcePreflight, /# Usage: GH_TOKEN=/);
assert.doesNotMatch(kiroSourcePreflight, /gh api user/);
assert.match(kiroSourcePreflight, /gh api \/apps\/qodo-skills-release-bot/);
assert.match(kiroSourcePreflight, /\.permissions == \{"administration":"read","contents":"write","metadata":"read"\}/);
assert.match(kiroSourcePreflight, /include == \["refs\/heads\/marketplace-kiro"\]/);
assert.match(kiroSourcePreflight, /sort == \["creation", "deletion", "non_fast_forward", "update"\]/);
assert.match(kiroSourcePreflight, /length == 1/);
assert.match(kiroSourcePreflight, /jq --argjson release_app_id "\$\{RELEASE_APP_ID\}"/);
assert.match(kiroSourcePreflight, /actor_type == "Integration"/);
assert.match(kiroSourcePreflight, /actor_id == \$release_app_id/);
assert.match(kiroSourcePreflight, /has\("bypass_actors"\) \| not/);

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
assert.match(protectionAudit, /\.bypass_actors == \[\{"actor_id":\$release_app_id,"actor_type":"Integration","bypass_mode":"always"\}\]/);
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
  if [[ "$*" == *"Immutable release tags"* ]]; then printf '%s\\n' 78; else printf '%s\\n' 77; fi
elif [[ "$*" == "api repos/qodo-ai/qodo-skills/rulesets/78" ]]; then
  if [[ "\${QODO_TEST_OMIT_BYPASS:-}" == 1 ]]; then
    printf '{"id":78,"conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},"rules":[{"type":"update"},{"type":"deletion"}]}\\n'
  else
    printf '{"id":78,"conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},"rules":[{"type":"update"},{"type":"deletion"}],"bypass_actors":[]}\\n'
  fi
elif [[ "$*" == "api repos/qodo-ai/qodo-skills/rulesets/77" ]]; then
  if [[ "\${QODO_TEST_OMIT_BYPASS:-}" == 1 ]]; then
    printf '{"conditions":{"ref_name":{"include":["refs/heads/marketplace-kiro"],"exclude":[]}},"rules":[{"type":"creation"},{"type":"update"},{"type":"deletion"},{"type":"non_fast_forward"}]}\\n'
  else
    creation='{"type":"creation"},'
    if [[ "\${QODO_TEST_OMIT_CREATION:-}" == 1 ]]; then creation=''; fi
    printf '{"id":77,"conditions":{"ref_name":{"include":["%s"],"exclude":[]}},"rules":[%s{"type":"update"},{"type":"deletion"},{"type":"non_fast_forward"}],"bypass_actors":[{"bypass_mode":"always","actor_type":"%s","actor_id":%s}]}\\n' "\${QODO_TEST_RULESET_TARGET:-refs/heads/marketplace-kiro}" "$creation" "\${QODO_TEST_RULESET_ACTOR_TYPE:-Integration}" "\${QODO_TEST_RULESET_ACTOR_ID:-12345}"
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
      const validPreflight = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: preflightEnvironment,
        timeout: 5_000,
      });
      assert.equal(validPreflight.error, undefined, validPreflight.error?.message);
      assert.equal(validPreflight.status, 0, validPreflight.stderr);
      const missingCreationPreflight = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: { ...preflightEnvironment, QODO_TEST_OMIT_CREATION: '1' },
        timeout: 5_000,
      });
      assert.equal(missingCreationPreflight.error, undefined, missingCreationPreflight.error?.message);
      assert.equal(missingCreationPreflight.status, 1, missingCreationPreflight.stderr);
      assert.match(missingCreationPreflight.stderr, /protect creation\/update\/deletion\/force-push/);
      const mismatchedPreflight = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: { ...preflightEnvironment, QODO_TEST_RULESET_ACTOR_ID: '54321' },
        timeout: 5_000,
      });
      assert.equal(mismatchedPreflight.error, undefined, mismatchedPreflight.error?.message);
      assert.equal(mismatchedPreflight.status, 1, mismatchedPreflight.stderr);
      assert.match(mismatchedPreflight.stderr, /dedicated Integration bypass/);
      const wrongTypePreflight = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: { ...preflightEnvironment, QODO_TEST_RULESET_ACTOR_TYPE: 'Team' },
        timeout: 5_000,
      });
      assert.equal(wrongTypePreflight.error, undefined, wrongTypePreflight.error?.message);
      assert.equal(wrongTypePreflight.status, 1, wrongTypePreflight.stderr);
      assert.match(wrongTypePreflight.stderr, /dedicated Integration bypass/);
      const hiddenBypassPreflight = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: { ...preflightEnvironment, QODO_TEST_OMIT_BYPASS: '1' },
        timeout: 5_000,
      });
      assert.equal(hiddenBypassPreflight.error, undefined, hiddenBypassPreflight.error?.message);
      assert.equal(hiddenBypassPreflight.status, 0, hiddenBypassPreflight.stderr);
      const malformedTarget = spawnSync('bash', [join(root, 'scripts', 'verify-kiro-release-source.sh')], {
        encoding: 'utf8',
        env: { ...preflightEnvironment, QODO_TEST_RULESET_TARGET: 'refs/heads/marketplace-*' },
        timeout: 5_000,
      });
      assert.equal(malformedTarget.status, 1, malformedTarget.stderr);
      assert.match(malformedTarget.stderr, /cover only refs\/heads\/marketplace-kiro/);

      const auditEnvironment = { ...preflightEnvironment };
      delete auditEnvironment.QODO_SKILLS_RELEASE_APP_ID;
      const validAudit = spawnSync('bash', [join(root, 'scripts', 'audit-release-protections.sh')], {
        encoding: 'utf8', env: auditEnvironment, timeout: 5_000,
      });
      assert.equal(validAudit.status, 0, validAudit.stderr);
      assert.match(validAudit.stdout, /app_id=12345 tag_ruleset=78 kiro_ruleset=77/);
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

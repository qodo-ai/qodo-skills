/** Test marketplace selection, packaging, provider verification, and workflow gates. */
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
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
    /--skill qodo-codebase-wisdom --skill-version 1\.1\.1 --distribution marketplace --host codex/,
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
assert.doesNotMatch(workflow, /OPENAI_API_KEY|ANTHROPIC_API_KEY/);
const preflight = workflow.indexOf('Verify immutable release before executing release code');
const releaseCheckout = workflow.indexOf('Check out release automation');
const preparationCheckout = workflow.indexOf('Check out the immutable release');
const validationInstall = workflow.indexOf('Install locked validation dependencies', preparationCheckout);
const canonicalValidation = workflow.indexOf('Validate canonical source and generated adapters', preparationCheckout);
assert.ok(preflight >= 0 && releaseCheckout > preflight);
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
assert.match(workflow, /QODO_RELEASE_ADMIN_TOKEN/);
assert.match(workflow, /verify-kiro-release-source\.sh/);
assert.match(workflow, /-F force=false/);
const kiroSourcePreflight = readFileSync(join(root, 'scripts', 'verify-kiro-release-source.sh'), 'utf8');
assert.match(kiroSourcePreflight, /Kiro marketplace release/);
assert.match(kiroSourcePreflight, /# Usage: GH_TOKEN=/);
assert.match(kiroSourcePreflight, /gh api user --jq '\.id'/);
assert.match(kiroSourcePreflight, /include == \["refs\/heads\/marketplace-kiro"\]/);
assert.match(kiroSourcePreflight, /contains\(\["update", "deletion", "non_fast_forward"\]\)/);
assert.match(kiroSourcePreflight, /length == 1/);
assert.match(kiroSourcePreflight, /actor_id == '"\$\{RELEASE_ACTOR_ID\}"'/);

console.log('Marketplace release workflow tests passed.');

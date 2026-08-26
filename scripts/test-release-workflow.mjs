/** Verify that release publication fails closed before creating mutable artifacts. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import {
  chmodSync,
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const workflow = readFileSync(join(root, '.github', 'workflows', 'release.yml'), 'utf8');
const preflight = readFileSync(join(root, 'scripts', 'verify-release-prerequisites.sh'), 'utf8');
const publisher = readFileSync(join(root, 'scripts', 'publish-release.sh'), 'utf8');
const releaseSource = `${workflow}\n${preflight}\n${publisher}`;

assert.doesNotMatch(releaseSource, /^\s+push:/m,
  'source merge must not bypass the CLI-first release order or an unmet credential gate');
assert.match(releaseSource, /^\s+workflow_dispatch:/m);
assert.match(workflow, /run: scripts\/verify-release-prerequisites\.sh/);
assert.match(workflow, /run: scripts\/publish-release\.sh/);
assert.match(readFileSync(join(root, 'scripts', 'verify-release-prerequisites.cmd'), 'utf8'),
  /bash "%~dp0verify-release-prerequisites\.sh"/);
assert.match(readFileSync(join(root, 'scripts', 'publish-release.cmd'), 'utf8'),
  /bash "%~dp0publish-release\.sh"/);

const immutabilityPreflight = releaseSource.indexOf('immutable-releases');
const tagCreation = releaseSource.indexOf('git tag --no-sign -a');
const releaseCreation = releaseSource.indexOf('gh release create');
const firstAssetCheck = releaseSource.indexOf('.assets[].name');
const existingReleaseExit = releaseSource.indexOf('exit 0');
const exactMainGuard = releaseSource.indexOf('git rev-parse origin/main');
const validationInstall = releaseSource.indexOf('npm ci');
const validationRun = releaseSource.indexOf('npm test');
const existingReleaseBranch = releaseSource.indexOf('if [[ "${RELEASE_EXISTS}"');
const toolChecks = releaseSource.indexOf('for tool in gh git node npm mktemp sha256sum cmp rm; do');
const finalMainGuard = releaseSource.lastIndexOf('git rev-parse origin/main');
const tagPush = releaseSource.indexOf('git push origin "refs/tags/${TAG}:refs/tags/${TAG}"');
const releaseAdminTokenCheck = releaseSource.indexOf('QODO_RELEASE_ADMIN_TOKEN is required');
const tagRulesetCheck = releaseSource.indexOf('Immutable release tags ruleset is required');
const releaseDownload = releaseSource.indexOf('gh release download');
const downloadedChecksum = releaseSource.indexOf(
  'verify_sha256 qodo-skills-index.json.sha256',
  releaseDownload,
);
const localByteComparison = releaseSource.indexOf('cmp --silent');
const draftCreation = releaseSource.indexOf('gh release create "${TAG}" --draft');
const draftPublish = releaseSource.indexOf('gh release edit "${TAG}" --draft=false');
const draftAssetCheck = releaseSource.indexOf('.assets[].name', draftCreation);
const draftDownload = releaseSource.indexOf('gh release download', draftCreation);
const draftChecksum = releaseSource.indexOf(
  'verify_sha256 qodo-skills-index.json.sha256',
  draftDownload,
);
const draftByteComparison = releaseSource.indexOf('cmp --silent', draftCreation);
const remoteTagCheck = releaseSource.indexOf('Remote ${TAG} no longer resolves', draftCreation);
const publishedDownload = releaseSource.indexOf('gh release download', draftPublish);
const publishedChecksum = releaseSource.indexOf(
  'verify_sha256 qodo-skills-index.json.sha256',
  publishedDownload,
);
const publishedByteComparison = releaseSource.indexOf('cmp --silent', draftPublish);

assert.ok(immutabilityPreflight >= 0, 'release workflow must check repository immutability');
assert.ok(exactMainGuard >= 0 && exactMainGuard < tagCreation,
  'release workflow must require the exact merged main commit before creating a tag');
assert.match(releaseSource, /git fetch origin main --no-tags/);
assert.match(releaseSource, /git rev-parse origin\/main/);
assert.match(releaseSource, /git tag --no-sign -a/);
assert.ok(validationInstall >= 0 && validationInstall < validationRun,
  'locked validation dependencies must be installed before release validation');
assert.ok(finalMainGuard > validationRun && finalMainGuard < existingReleaseBranch,
  'the verified release commit must still be the exact main head before release handling');
assert.ok(toolChecks >= 0 && toolChecks < exactMainGuard,
  'external release tools must be checked before their first use');
assert.match(releaseSource, /command -v "\$\{tool\}"/);
assert.match(publisher, /command -v sha256sum/);
assert.match(publisher, /command -v shasum/);
assert.match(publisher, /shasum -a 256 --check/);
assert.match(publisher, /verify_sha256 qodo-skills-index\.json\.sha256/g);
assert.doesNotMatch(releaseSource, /"\$GITHUB_SHA"/,
  'scalar shell variables must use braced expansion');
assert.ok(tagCreation > immutabilityPreflight, 'immutability must be checked before creating a tag');
assert.ok(releaseCreation > immutabilityPreflight, 'immutability must be checked before creating a release');
assert.ok(firstAssetCheck >= 0 && firstAssetCheck < existingReleaseExit,
  'an existing release must be accepted only after its assets are verified');
assert.ok(releaseDownload > firstAssetCheck && releaseDownload < existingReleaseExit,
  'existing immutable release assets must be downloaded before success');
assert.ok(downloadedChecksum > releaseDownload && downloadedChecksum < existingReleaseExit,
  'the downloaded index must match its published checksum before success');
assert.ok(localByteComparison > downloadedChecksum && localByteComparison < existingReleaseExit,
  'downloaded immutable assets must match the validated local bytes before success');
assert.ok(releaseAdminTokenCheck > validationRun && releaseAdminTokenCheck < existingReleaseBranch,
  'immutability preflight must require an administration-read credential before tagging');
assert.ok(tagRulesetCheck > releaseAdminTokenCheck && tagRulesetCheck < existingReleaseBranch,
  'release-tag update/deletion protection must be verified before tagging');
assert.match(releaseSource, /\.conditions\.ref_name\.include/);
assert.match(releaseSource, /gh api --paginate "repos\/\$\{GITHUB_REPOSITORY\}\/rulesets\?per_page=100"/);
assert.match(releaseSource, /RULESET_COUNT/);
assert.match(releaseSource, /\.conditions\.ref_name\.exclude \| type == "array" and length == 0/);
assert.match(releaseSource, /contains\(\["update", "deletion"\]\)/);
assert.match(releaseSource, /index\("creation"\)\) == null/,
  'the release ruleset must permit initial tag creation');
assert.match(releaseSource, /\.bypass_actors \| type == "array" and length == 0/);
assert.match(releaseSource, /GH_TOKEN: \$\{\{ secrets\.QODO_RELEASE_ADMIN_TOKEN \}\}/);
assert.match(releaseSource, /GH_TOKEN: \$\{\{ github\.token \}\}/);
assert.ok(tagPush > tagCreation && tagPush < releaseCreation,
  'the validated annotated tag must be pushed without a force path before release creation');
assert.doesNotMatch(releaseSource, /--force-with-lease/);
assert.doesNotMatch(releaseSource, /\$\{GITHUB_SHA\}:refs\/heads\/main/);
assert.ok(draftCreation === releaseCreation,
  'a new immutable release must remain a draft while its assets are attached');
assert.ok(draftAssetCheck > draftCreation && draftAssetCheck < draftPublish,
  'the exact draft asset inventory must be checked before publication');
assert.ok(draftDownload > draftAssetCheck && draftDownload < draftPublish,
  'draft assets must be downloaded before publication');
assert.ok(draftChecksum > draftDownload && draftChecksum < draftPublish,
  'the downloaded draft index must match its checksum before publication');
assert.ok(draftByteComparison > draftChecksum && draftByteComparison < draftPublish,
  'the downloaded draft assets must match the validated checkout before publication');
assert.ok(remoteTagCheck > draftByteComparison && remoteTagCheck < draftPublish,
  'the protected remote tag must resolve to the validated commit immediately before publication');
assert.ok(draftPublish > draftCreation,
  'the verified draft must be explicitly published only after its assets are attached');
assert.ok(publishedDownload > draftPublish,
  'immutable assets must be downloaded again after publication');
assert.ok(publishedChecksum > publishedDownload,
  'published immutable assets must still match their checksum');
assert.ok(publishedByteComparison > publishedChecksum,
  'published immutable assets must still match the validated checkout');
assert.match(releaseSource, /RELEASE_EXISTS=false/);
assert.match(releaseSource, /gh api --include/);
assert.match(releaseSource, /HTTP\/\[0-9\.\]\+ 404/);
assert.match(releaseSource, /gh release upload "\$\{TAG\}" --clobber/,
  'a failed draft publication must be resumable without abandoning the version');
assert.match(releaseSource, /--jq '\.draft'/);
assert.match(releaseSource, /"refs\/tags\/\$\{TAG\}:refs\/tags\/\$\{TAG\}"/);
assert.match(releaseSource, /git rev-list -n 1 \"\$\{TAG\}\"/);
assert.match(releaseSource, /\.assets\[\]\.name/);
assert.match(
  readFileSync(join(root, '.gitattributes'), 'utf8'),
  /^\*\.sha256 text eol=lf$/m,
  'checksum manifests must remain LF-only so sha256sum never sees a CR-suffixed filename on Windows',
);
assert.match(
  readFileSync(join(root, '.gitattributes'), 'utf8'),
  /^\*\.sh text eol=lf$/m,
  'Git Bash entrypoints must remain LF-only on Windows',
);

const run = (cwd, command, args = [], env = {}) => execFileSync(command, args, {
  cwd,
  encoding: 'utf8',
  stdio: 'pipe',
  env: { ...process.env, ...env },
});
const runShell = (cwd, script, env = {}) => process.platform === 'win32'
  ? run(cwd, process.env.ComSpec ?? 'cmd.exe', [
    // `call` is cmd.exe's batch-file primitive. Without `/s`, cmd preserves the
    // one quote pair Node adds when serializing the space-containing path arg.
    '/d', '/c', 'call', script.replace(/\.sh$/, '.cmd'),
  ], env)
  : run(cwd, script, [], env);

// Keep a space in the harness path so Windows cmd /c quoting is exercised.
const harness = mkdtempSync(join(tmpdir(), 'qodo release behavior-'));
const bin = join(harness, 'bin');
const fakeGhState = join(harness, 'gh-state.json');
const fakeGhAssets = join(harness, 'gh-assets');
mkdirSync(bin, { recursive: true });
copyFileSync(join(root, 'scripts', 'fixtures', 'fake-release-gh.mjs'), join(bin, 'fake-release-gh.mjs'));
copyFileSync(join(root, 'scripts', 'fixtures', 'fake-release-gh.cmd'), join(bin, 'gh.cmd'));
copyFileSync(join(root, 'scripts', 'fixtures', 'fake-release-gh.mjs'), join(bin, 'gh'));
if (process.platform !== 'win32') chmodSync(join(bin, 'gh'), 0o755);
const fakeGhEnv = {
  PATH: `${bin}${delimiter}${process.env.PATH}`,
  GH_TOKEN: 'administration-read-test-token',
  GITHUB_REPOSITORY: 'qodo-ai/qodo-skills',
  FAKE_GH_STATE: fakeGhState,
  FAKE_GH_ASSETS: fakeGhAssets,
};

try {
  const preflightPath = join(root, 'scripts', 'verify-release-prerequisites.sh');
  runShell(root, preflightPath, fakeGhEnv);
  assert.throws(() => runShell(root, preflightPath, { ...fakeGhEnv, GH_TOKEN: '' }),
    /QODO_RELEASE_ADMIN_TOKEN is required/);
  assert.throws(() => runShell(root, preflightPath, {
    ...fakeGhEnv,
    FAKE_IMMUTABLE_RELEASES: 'false',
  }), /Release immutability is disabled/);
  assert.throws(() => runShell(root, preflightPath, {
    ...fakeGhEnv,
    FAKE_RULESET_IDS: '1\n2',
  }), /Exactly one active/);
  assert.throws(() => runShell(root, preflightPath, {
    ...fakeGhEnv,
    FAKE_RULESET_HAS_CREATION: 'true',
  }), /must protect update\/deletion, permit creation/);

  const behaviorOrigin = join(harness, 'origin.git');
  const checkout = join(harness, 'checkout');
  mkdirSync(checkout);
  run(checkout, 'git', ['init', '--initial-branch=main']);
  run(checkout, 'git', ['config', 'user.name', 'Release Test']);
  run(checkout, 'git', ['config', 'user.email', 'release-test@qodo.invalid']);
  for (const directory of ['distribution', 'releases', 'scripts']) {
    mkdirSync(join(checkout, directory), { recursive: true });
  }
  for (const file of ['catalog.json', 'qodo-skills-index.json', 'qodo-skills-index.json.sha256']) {
    copyFileSync(join(root, 'distribution', file), join(checkout, 'distribution', file));
  }
  copyFileSync(join(root, 'releases', 'v1.0.3.json'), join(checkout, 'releases', 'v1.0.3.json'));
  copyFileSync(join(root, 'scripts', 'release-notes.mjs'), join(checkout, 'scripts', 'release-notes.mjs'));
  copyFileSync(join(root, 'scripts', 'publish-release.sh'), join(checkout, 'scripts', 'publish-release.sh'));
  copyFileSync(join(root, 'scripts', 'publish-release.cmd'), join(checkout, 'scripts', 'publish-release.cmd'));
  chmodSync(join(checkout, 'scripts', 'publish-release.sh'), 0o755);
  run(checkout, 'git', ['add', '.']);
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '-m', 'release fixture']);
  const releaseSha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  run(harness, 'git', ['init', '--bare', '--initial-branch=main', behaviorOrigin]);
  run(checkout, 'git', ['remote', 'add', 'origin', behaviorOrigin]);
  run(checkout, 'git', ['push', '-u', 'origin', 'main']);
  // The publisher owns the tag's format. A runner-level signing preference
  // must not introduce a pinentry/key dependency into an automated release.
  run(checkout, 'git', ['config', 'tag.gpgSign', 'true']);

  const publishEnv = {
    ...fakeGhEnv,
    GH_TOKEN: 'contents-write-test-token',
    GITHUB_SHA: releaseSha,
    RUNNER_TEMP: harness,
  };
  const publishPath = join(checkout, 'scripts', 'publish-release.sh');
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_RELEASE_LOOKUP_ERROR: 'true',
  }), /Could not determine whether v1\.0\.3 already exists/);
  assert.equal(run(checkout, 'git', ['ls-remote', '--tags', 'origin', 'v1.0.3']).trim(), '');
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'stale checkout']);
  assert.notEqual(run(checkout, 'git', ['rev-parse', 'HEAD']).trim(), releaseSha);
  runShell(checkout, publishPath, publishEnv);
  assert.equal(run(checkout, 'git', ['rev-list', '-n', '1', 'v1.0.3']).trim(), releaseSha);
  const published = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.deepEqual(
    { draft: published.draft, immutable: published.immutable, edits: published.edits, downloads: published.downloads },
    { draft: false, immutable: true, edits: 1, downloads: 2 },
  );

  // A published retry must fetch the remote tag instead of trusting a stale local copy.
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'drift fixture']);
  const driftSha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', `${driftSha}:refs/tags/v1.0.3`]);
  assert.throws(() => runShell(checkout, publishPath, publishEnv));
  run(checkout, 'git', ['-c', 'tag.gpgSign=false', 'tag', '-f', '-a', 'v1.0.3', '-m', 'restore v1.0.3', releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', 'refs/tags/v1.0.3:refs/tags/v1.0.3']);

  // A public immutable retry is verification-only; it must not republish.
  runShell(checkout, publishPath, publishEnv);
  const verifiedRetry = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.equal(verifiedRetry.edits, 1);
  assert.equal(verifiedRetry.downloads, 3);

  // A mismatched draft asset fails before publication and remains resumable.
  writeFileSync(fakeGhState, `${JSON.stringify({
    exists: true,
    draft: true,
    immutable: false,
    assets: ['qodo-skills-index.json', 'qodo-skills-index.json.sha256'],
    downloads: 0,
    edits: 0,
  })}\n`);
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_CORRUPT_DOWNLOAD: 'draft',
  }));
  const rejectedDraft = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.equal(rejectedDraft.draft, true);
  assert.equal(rejectedDraft.edits, 0);
  runShell(checkout, publishPath, publishEnv);
  assert.equal(JSON.parse(readFileSync(fakeGhState, 'utf8')).immutable, true);

  // Publication is not success until GitHub reports the release immutable.
  writeFileSync(fakeGhState, `${JSON.stringify({
    exists: true,
    draft: true,
    immutable: false,
    assets: ['qodo-skills-index.json', 'qodo-skills-index.json.sha256'],
    downloads: 0,
    edits: 0,
  })}\n`);
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_PUBLISHED_MUTABLE: 'true',
  }), /Published release is mutable/);
  const rejectedMutable = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.deepEqual(
    { draft: rejectedMutable.draft, immutable: rejectedMutable.immutable, edits: rejectedMutable.edits },
    { draft: false, immutable: false, edits: 1 },
  );

  // The final public download is independently verified after publication.
  // A mismatch burns this immutable version and must still fail the workflow.
  writeFileSync(fakeGhState, `${JSON.stringify({
    exists: true,
    draft: true,
    immutable: false,
    assets: ['qodo-skills-index.json', 'qodo-skills-index.json.sha256'],
    downloads: 0,
    edits: 0,
  })}\n`);
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_CORRUPT_DOWNLOAD: 'published',
  }));
  const rejectedPublicBytes = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.deepEqual(
    {
      draft: rejectedPublicBytes.draft,
      immutable: rejectedPublicBytes.immutable,
      edits: rejectedPublicBytes.edits,
      downloads: rejectedPublicBytes.downloads,
    },
    { draft: false, immutable: true, edits: 1, downloads: 2 },
  );
} finally {
  rmSync(harness, { recursive: true, force: true });
}

const fixture = mkdtempSync(join(tmpdir(), 'qodo-release-lease-'));
const origin = join(fixture, 'origin.git');
const seed = join(fixture, 'seed');
const runner = join(fixture, 'runner');
const git = (cwd, args) => execFileSync('git', [
  '-c', 'commit.gpgsign=false',
  '-c', 'tag.gpgSign=false',
  ...args,
], { cwd, encoding: 'utf8', stdio: 'pipe' }).trim();

try {
  git(fixture, ['init', '--bare', '--initial-branch=main', origin]);
  const preReceive = join(origin, 'hooks', 'pre-receive');
  writeFileSync(preReceive, [
    '#!/usr/bin/env bash',
    '# Description: reject updates and deletions of release tags in this bare-repository fixture.',
    '# Usage: Git pre-receive hook; reads "<old-sha> <new-sha> <ref>" records from stdin.',
    'set -euo pipefail',
    'while read -r old_sha new_sha ref_name; do',
    '  case "${ref_name}" in',
    '    refs/tags/*)',
    '      if [[ "${old_sha}" == *[!0]* ]]; then',
    '        echo "immutable release tag update rejected: ${ref_name}" >&2',
    '        exit 1',
    '      fi',
    '      ;;',
    '  esac',
    'done',
    '',
  ].join('\n'));
  chmodSync(preReceive, 0o755);
  git(fixture, ['clone', origin, seed]);
  git(seed, ['config', 'user.name', 'Release Test']);
  git(seed, ['config', 'user.email', 'release-test@qodo.invalid']);
  writeFileSync(join(seed, 'release.txt'), 'v1\n');
  git(seed, ['add', 'release.txt']);
  git(seed, ['commit', '-m', 'release v1']);
  const releaseSha = git(seed, ['rev-parse', 'HEAD']);
  git(seed, ['push', 'origin', 'main']);

  git(fixture, ['clone', origin, runner]);
  git(runner, ['config', 'user.name', 'Release Test']);
  git(runner, ['config', 'user.email', 'release-test@qodo.invalid']);
  git(runner, ['tag', '-a', 'v1', '-m', 'v1']);
  git(runner, ['push', 'origin', 'refs/tags/v1:refs/tags/v1']);
  assert.equal(
    git(runner, ['ls-remote', 'origin', 'refs/tags/v1^{}']).split(/\s+/)[0],
    releaseSha,
  );

  writeFileSync(join(seed, 'release.txt'), 'v2\n');
  git(seed, ['add', 'release.txt']);
  git(seed, ['commit', '-m', 'advance main']);
  git(seed, ['push', 'origin', 'main']);
  git(runner, ['fetch', 'origin', 'main']);
  git(runner, ['tag', '-f', '-a', 'v1', '-m', 'moved v1', 'origin/main']);
  assert.throws(() => git(runner, [
    'push', '--force', 'origin', 'refs/tags/v1:refs/tags/v1',
  ]), /immutable release tag update rejected/);
  assert.equal(
    git(runner, ['ls-remote', 'origin', 'refs/tags/v1^{}']).split(/\s+/)[0],
    releaseSha,
  );
} finally {
  rmSync(fixture, { recursive: true, force: true });
}

console.log('Release workflow safety test passed.');

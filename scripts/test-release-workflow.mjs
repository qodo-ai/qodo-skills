/** Verify that release publication fails closed before creating mutable artifacts. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
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
import { buildEnterpriseBundle } from './build-enterprise-bundle.mjs';
import { assertDiscoveryManifestFailures } from './test-release-discovery-assets.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const workflow = readFileSync(join(root, '.github', 'workflows', 'release.yml'), 'utf8');
const preflight = readFileSync(join(root, 'scripts', 'verify-release-prerequisites.sh'), 'utf8');
const publisher = readFileSync(join(root, 'scripts', 'publish-release.sh'), 'utf8');
const protectionAudit = readFileSync(join(root, 'scripts', 'audit-release-protections.sh'), 'utf8');
const releaseSource = `${workflow}\n${preflight}\n${publisher}`;
const packageVersion = JSON.parse(
  readFileSync(join(root, 'package.json'), 'utf8'),
).version;
const releaseTag = `v${packageVersion}`;
const escapedReleaseTag = releaseTag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
assert.doesNotMatch(releaseSource, /^\s+push:/m,
  'source merge must not bypass the CLI-first release order or an unmet credential gate');
assert.match(releaseSource, /^\s+workflow_dispatch:/m);
assert.match(workflow, /github\.ref == format\('refs\/heads\/\{0\}', github\.event\.repository\.default_branch\)/,
  'the write-scoped release job must run only from the default branch');
assert.match(workflow, /run: scripts\/verify-release-prerequisites\.sh/);
assert.match(workflow, /run: scripts\/publish-release\.sh/);
assert.match(workflow, /qodo-release-source\/scripts\/build-enterprise-bundle\.mjs/);
assert.match(workflow, /git worktree add --detach/);
assert.match(workflow, /QODO_RELEASE_SOURCE_DIR: \$\{\{ runner\.temp \}\}\/qodo-release-source/);
assert.match(workflow, /QODO_RELEASE_NOTES_FILE: \$\{\{ runner\.temp \}\}\/qodo-release-notes\.md/);
assert.match(workflow, /QODO_ENTERPRISE_RELEASE_DIR/);
assert.match(readFileSync(join(root, 'scripts', 'verify-release-prerequisites.cmd'), 'utf8'),
  /bash "%~dp0verify-release-prerequisites\.sh"/);
assert.match(readFileSync(join(root, 'scripts', 'publish-release.cmd'), 'utf8'),
  /bash "%~dp0publish-release\.sh"/);

const tagCreation = releaseSource.indexOf('git tag --no-sign -a');
const releaseCreation = releaseSource.indexOf('gh release create');
const firstAssetCheck = releaseSource.indexOf('.assets[].name');
const existingReleaseExit = releaseSource.indexOf('exit 0');
const exactMainGuard = releaseSource.indexOf('git rev-parse origin/main');
const validationInstall = releaseSource.indexOf('npm ci');
const validationRun = releaseSource.indexOf('npm test');
const existingReleaseBranch = releaseSource.indexOf('if [[ "${RELEASE_EXISTS}"');
const toolChecks = releaseSource.indexOf('for tool in gh git node npm mktemp sha256sum cmp rm; do');
const firstMainGuard = releaseSource.indexOf('require_current_main');
const publisherReleaseLookup = publisher.indexOf('load_release');
const publisherTagCreation = publisher.indexOf('git tag --no-sign -a');
const publisherFinalMainGuard = publisher.lastIndexOf('require_current_main');
const publisherTagPush = publisher.indexOf('git push origin "refs/tags/${TAG}:refs/tags/${TAG}"');
const releaseTokenCheck = releaseSource.indexOf('installation-wide, read-only GitHub App token with Administration:read is required');
const checkoutGuard = publisher.indexOf('\nrequire_exact_release_checkout\n');
const catalogRead = publisher.indexOf('CURRENT_VERSION=');
const tagRulesetCheck = releaseSource.indexOf('Immutable release tags ruleset is required');
const releaseVerificationHelper = releaseSource.indexOf('verify_release_assets()');
const releaseDownload = releaseSource.indexOf('gh release download');
const downloadedVerification = releaseSource.indexOf('verify_release_assets "${VERIFY_DIR}"', releaseDownload);
const draftCreation = releaseSource.indexOf('gh release create "${TAG}" --draft');
const draftPublish = releaseSource.indexOf('gh api --method PATCH "${RELEASE_ENDPOINT}" -F draft=false');
const draftAssetCheck = releaseSource.indexOf('.assets[].name', draftCreation);
const draftDownload = releaseSource.indexOf('download_draft_release_assets_by_id "${VERIFY_DIR}"', draftCreation);
const draftVerification = releaseSource.indexOf('verify_release_assets "${VERIFY_DIR}"', draftDownload);
const remoteTagCheck = releaseSource.indexOf('require_annotated_release_tag', draftCreation);
const publishedDownload = releaseSource.indexOf('gh release download', draftPublish);
const publishedVerification = releaseSource.indexOf('verify_release_assets "${PUBLISHED_VERIFY_DIR}"', publishedDownload);
assert.match(protectionAudit, /repos\/\$\{GITHUB_REPOSITORY\}\/immutable-releases/,
  'the administrator audit must check repository immutability');
assert.match(preflight, /repos\/\$\{GITHUB_REPOSITORY\}\/immutable-releases/,
  'the protected App token must verify immutability before publication');
assert.match(workflow, /environment:\s*\n\s*name: marketplace-kiro/);
assert.match(workflow, /actions\/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1/);
assert.match(workflow, /permission-administration: read/);
assert.match(workflow, /Mint installation-wide read-only release preflight token/);
assert.doesNotMatch(workflow, /repositories: qodo-skills/,
  'the read-only preflight token must see the complete installation repository set');
assert.match(workflow, /GH_TOKEN: \$\{\{ steps\.release-preflight-token\.outputs\.token \}\}/);
assert.match(preflight, /installation\/repositories\?per_page=100/);
assert.ok(exactMainGuard >= 0 && exactMainGuard < tagCreation,
  'release workflow must require the exact merged main commit before creating a tag');
assert.match(releaseSource, /git fetch origin main --no-tags/);
assert.match(releaseSource, /git rev-parse origin\/main/);
assert.match(releaseSource, /git tag --no-sign -a/);
assert.ok(validationInstall >= 0 && validationInstall < validationRun,
  'locked validation dependencies must be installed before release validation');
assert.ok(firstMainGuard > validationRun && firstMainGuard < existingReleaseBranch,
  'the verified release commit must still be the exact main head before release handling');
assert.ok(checkoutGuard >= 0 && checkoutGuard < catalogRead,
  'the publisher must bind a clean local checkout to GITHUB_SHA before reading release assets');
assert.match(publisher, /git rev-parse HEAD/);
assert.match(publisher, /git diff --quiet --ignore-submodules --/);
assert.match(publisher, /git diff --cached --quiet --ignore-submodules --/);
assert.ok(toolChecks >= 0 && toolChecks < exactMainGuard,
  'external release tools must be checked before their first use');
assert.match(releaseSource, /command -v "\$\{tool\}"/);
assert.match(publisher, /command -v sha256sum/);
assert.match(publisher, /command -v shasum/);
assert.match(publisher, /shasum -a 256 --check/);
assert.match(publisher, /verify_sha256 qodo-skills-index\.json\.sha256/g);
assert.doesNotMatch(releaseSource, /"\$GITHUB_SHA"/,
  'scalar shell variables must use braced expansion');
assert.match(publisher, /gh api "\$\{RELEASE_ENDPOINT\}" --jq '\.immutable'/,
  'publication must verify the provider reports an immutable release');
assert.ok(firstAssetCheck >= 0 && firstAssetCheck < existingReleaseExit,
  'an existing release must be accepted only after its assets are verified');
assert.ok(releaseDownload > firstAssetCheck && releaseDownload < existingReleaseExit,
  'existing immutable release assets must be downloaded before success');
assert.ok(releaseVerificationHelper >= 0 && releaseVerificationHelper < existingReleaseBranch,
  'release asset checksum and byte verification must be defined before release handling');
assert.ok(downloadedVerification > releaseDownload && downloadedVerification < existingReleaseExit,
  'downloaded immutable assets must be checksum- and byte-verified before success');
assert.ok(releaseTokenCheck > validationRun && releaseTokenCheck < existingReleaseBranch,
  'runtime preflight must require an installation-wide read-only App token before tagging');
assert.ok(tagRulesetCheck > releaseTokenCheck && tagRulesetCheck < existingReleaseBranch,
  'release-tag update/deletion protection must be verified before tagging');
assert.match(releaseSource, /\.conditions\.ref_name\.include/);
assert.match(releaseSource, /gh api --paginate "repos\/\$\{GITHUB_REPOSITORY\}\/rulesets\?per_page=100"/);
assert.match(releaseSource, /RULESET_COUNT/);
assert.match(releaseSource, /\.conditions\.ref_name\.exclude \| type == "array" and length == 0/);
assert.match(releaseSource, /sort == \["deletion", "update"\]/);
assert.match(releaseSource, /index\("creation"\)\) == null/,
  'the release ruleset must permit initial tag creation');
assert.match(releaseSource, /has\("bypass_actors"\) \| not/);
assert.doesNotMatch(releaseSource, /QODO_RELEASE_ADMIN_TOKEN/);
assert.match(releaseSource, /GH_TOKEN: \$\{\{ github\.token \}\}/);
assert.ok(
  publisherFinalMainGuard > publisherReleaseLookup &&
  publisherFinalMainGuard > publisherTagCreation &&
  publisherFinalMainGuard < publisherTagPush,
  'main must be revalidated after draft discovery and immediately before the tag push');
assert.ok(publisherTagPush > publisherTagCreation,
  'the validated annotated tag must be pushed without a force path before release creation');
assert.doesNotMatch(releaseSource, /--force-with-lease/);
assert.doesNotMatch(releaseSource, /\$\{GITHUB_SHA\}:refs\/heads\/main/);
assert.ok(draftCreation === releaseCreation,
  'a new immutable release must remain a draft while its assets are attached');
assert.ok(draftAssetCheck > draftCreation && draftAssetCheck < draftPublish,
  'the exact draft asset inventory must be checked before publication');
assert.ok(draftDownload > draftAssetCheck && draftDownload < draftPublish,
  'draft assets must be downloaded before publication');
assert.ok(draftVerification > draftDownload && draftVerification < draftPublish,
  'the downloaded draft assets must be checksum- and byte-verified before publication');
assert.ok(remoteTagCheck > draftVerification && remoteTagCheck < draftPublish,
  'the protected remote tag must resolve to the validated commit immediately before publication');
assert.ok(draftPublish > draftCreation,
  'the verified draft must be explicitly published only after its assets are attached');
assert.ok(publishedDownload > draftPublish,
  'immutable assets must be downloaded again after publication');
assert.ok(publishedVerification > publishedDownload,
  'published immutable assets must still match their checksums and validated bytes');
assert.match(releaseSource, /RELEASE_EXISTS=false/);
assert.match(releaseSource, /releases\?per_page=100/,
  'draft discovery must use the release list because GitHub release-by-tag returns 404 for drafts');
assert.doesNotMatch(publisher, /releases\/tags\/\$\{TAG\}/,
  'draft reads must use the release ID returned by the list endpoint');
assert.match(workflow, /id: release-source/);
assert.match(workflow, /git merge-base --is-ancestor/);
assert.match(workflow, /QODO_RELEASE_COMMIT: \$\{\{ steps\.release-source\.outputs\.commit \}\}/);
assert.match(publisher, /A release commit behind current main may only resume an existing draft/);
assert.match(publisher, /git -C "\$\{RELEASE_SOURCE_DIR\}" rev-parse HEAD/);
assert.match(publisher, /release source HEAD is not QODO_RELEASE_COMMIT/);
assert.match(releaseSource, /upload_draft_release_asset_by_id "\$\{release_asset\}"/);
assert.doesNotMatch(publisher, /gh release upload/, 'tag lookup cannot address a draft release');
assert.doesNotMatch(releaseSource, /gh release upload[^\n]*--clobber/,
  'draft recovery must never overwrite an existing asset');
assert.doesNotMatch(releaseSource, /gh release delete-asset/,
  'draft recovery must never delete an existing asset');
assert.match(releaseSource, /git cat-file -t "refs\/tags\/\$\{TAG\}"/,
  'existing and fetched release refs must be annotated tag objects');
assert.match(releaseSource, /git rev-parse "refs\/tags\/\$\{TAG\}\^\{\}"/,
  'annotated release tags must peel to the validated commit');
assert.match(releaseSource, /--jq '\.draft'/);
assert.match(releaseSource, /"refs\/tags\/\$\{TAG\}:refs\/tags\/\$\{TAG\}"/);
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
  GH_TOKEN: 'repository-scoped-test-token',
  GITHUB_REPOSITORY: 'qodo-ai/qodo-skills',
  FAKE_GH_STATE: fakeGhState,
  FAKE_GH_ASSETS: fakeGhAssets,
  FAKE_RELEASE_TAG: releaseTag,
};
try {
  const preflightPath = join(root, 'scripts', 'verify-release-prerequisites.sh');
  runShell(root, preflightPath, fakeGhEnv);
  assert.throws(() => runShell(root, preflightPath, { ...fakeGhEnv, GH_TOKEN: '' }),
    /installation-wide, read-only GitHub App token with Administration:read is required/);
  assert.throws(() => runShell(root, preflightPath, {
    ...fakeGhEnv,
    FAKE_INSTALLATION_REPOSITORIES: 'qodo-ai/other',
  }), /installed on qodo-ai\/qodo-skills and no other repository/);
  assert.throws(() => runShell(root, preflightPath, {
    ...fakeGhEnv,
    FAKE_INSTALLATION_REPOSITORIES: 'qodo-ai/qodo-skills\nqodo-ai/other',
  }), /installed on qodo-ai\/qodo-skills and no other repository/);
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
  }), /must protect only update\/deletion, permit creation/);

  const behaviorOrigin = join(harness, 'origin.git');
  const checkout = join(harness, 'checkout');
  mkdirSync(checkout);
  run(checkout, 'git', ['init', '--initial-branch=main']);
  run(checkout, 'git', ['config', 'user.name', 'Release Test']);
  run(checkout, 'git', ['config', 'user.email', 'release-test@qodo.invalid']);
  for (const directory of ['distribution', 'releases', 'scripts']) {
    mkdirSync(join(checkout, directory), { recursive: true });
  }
  copyFileSync(join(root, '.gitattributes'), join(checkout, '.gitattributes'));
  for (const file of [
    'catalog.json',
    'qodo-cli-managed-bundle.json',
    'qodo-cli-managed-bundle.json.sha256',
    'qodo-skills-index.json',
    'qodo-skills-index.json.sha256',
  ]) {
    copyFileSync(join(root, 'distribution', file), join(checkout, 'distribution', file));
  }
  copyFileSync(join(root, 'releases', `${releaseTag}.json`), join(checkout, 'releases', `${releaseTag}.json`));
  copyFileSync(join(root, 'scripts', 'release-notes.mjs'), join(checkout, 'scripts', 'release-notes.mjs'));
  copyFileSync(join(root, 'scripts', 'publish-release.sh'), join(checkout, 'scripts', 'publish-release.sh'));
  copyFileSync(join(root, 'scripts', 'publish-release.cmd'), join(checkout, 'scripts', 'publish-release.cmd'));
  chmodSync(join(checkout, 'scripts', 'publish-release.sh'), 0o755);
  run(checkout, 'git', ['add', '.']);
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '-m', 'release fixture']);
  const releaseSha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  const enterpriseDir = join(harness, 'enterprise-assets');
  buildEnterpriseBundle({ output: enterpriseDir, commit: releaseSha });
  run(harness, 'git', ['init', '--bare', '--initial-branch=main', behaviorOrigin]);
  run(checkout, 'git', ['remote', 'add', 'origin', behaviorOrigin]);
  run(checkout, 'git', ['push', '-u', 'origin', 'main']);
  const releaseSourceCheckout = join(harness, 'release-source');
  run(checkout, 'git', ['worktree', 'add', '--detach', releaseSourceCheckout, releaseSha]);
  const releaseNotes = join(harness, 'release-notes.md');
  run(releaseSourceCheckout, process.execPath, [join(releaseSourceCheckout, 'scripts', 'release-notes.mjs'), releaseNotes]);
  // The publisher owns the tag format even when the runner prefers signed tags.
  run(checkout, 'git', ['config', 'tag.gpgSign', 'true']);

  const publishEnv = {
    ...fakeGhEnv,
    GH_TOKEN: 'contents-write-test-token',
    GITHUB_SHA: releaseSha,
    RUNNER_TEMP: harness,
    QODO_ENTERPRISE_RELEASE_DIR: enterpriseDir,
    QODO_RELEASE_NOTES_FILE: releaseNotes,
    QODO_RELEASE_SOURCE_DIR: releaseSourceCheckout,
  };
  const publishPath = join(checkout, 'scripts', 'publish-release.sh');
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_RELEASE_LOOKUP_ERROR: 'true',
  }), new RegExp(`Could not determine whether ${escapedReleaseTag} already exists`));
  assert.equal(run(checkout, 'git', ['ls-remote', '--tags', 'origin', releaseTag]).trim(), '');
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'stale checkout']);
  assert.notEqual(run(checkout, 'git', ['rev-parse', 'HEAD']).trim(), releaseSha);
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /checked-out HEAD is not GITHUB_SHA/);
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  writeFileSync(join(checkout, 'distribution', 'qodo-skills-index.json'), '{}\n');
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /release checkout has tracked worktree changes/);
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  assertDiscoveryManifestFailures({ publisher, enterpriseDir, checkout, publishPath, publishEnv, releaseTag, run, runShell });
  runShell(checkout, publishPath, publishEnv);
  assert.equal(run(checkout, 'git', ['rev-list', '-n', '1', releaseTag]).trim(), releaseSha);
  const published = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.deepEqual(
    { draft: published.draft, immutable: published.immutable, edits: published.edits, downloads: published.downloads },
    { draft: false, immutable: true, edits: 1, downloads: published.assets.length + 1 },
  );
  for (const corruption of [{ name: 'wrong title' }, { body: 'wrong notes' }]) {
    const corrupted = { ...published, ...corruption, draft: true, immutable: false, edits: 0, downloads: 0 };
    writeFileSync(fakeGhState, `${JSON.stringify(corrupted)}\n`);
    assert.throws(() => runShell(checkout, publishPath, publishEnv), /unexpected .* metadata/);
    assert.deepEqual(JSON.parse(readFileSync(fakeGhState, 'utf8')), corrupted);
  }
  writeFileSync(fakeGhState, `${JSON.stringify(published)}\n`);
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    FAKE_DUPLICATE_RELEASES: 'true',
  }), new RegExp(`Multiple releases claim ${escapedReleaseTag}`));
  // Recovery from reviewed automation changes must still use tagged bytes.
  writeFileSync(fakeGhState, `${JSON.stringify({
    ...published,
    draft: true,
    immutable: false,
    downloads: 0,
    edits: 0,
  })}\n`);
  const divergentIndex = '{"currentMainOnly":true}\n';
  writeFileSync(join(checkout, 'distribution', 'qodo-skills-index.json'), divergentIndex);
  writeFileSync(join(checkout, 'distribution', 'qodo-skills-index.json.sha256'),
    `${createHash('sha256').update(divergentIndex).digest('hex')}  qodo-skills-index.json\n`);
  run(checkout, 'git', ['add', 'distribution']);
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '-m', 'release recovery automation']);
  const recoverySha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  run(checkout, 'git', ['push', 'origin', 'main']);
  runShell(checkout, publishPath, {
    ...publishEnv,
    GITHUB_SHA: recoverySha,
    QODO_RELEASE_COMMIT: releaseSha,
  });
  const recovered = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.deepEqual(
    { draft: recovered.draft, immutable: recovered.immutable, edits: recovered.edits, downloads: recovered.downloads },
    { draft: false, immutable: true, edits: 1, downloads: recovered.assets.length + 1 },
  );
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', 'main']);

  // An older tag without a matching draft can never borrow current-main bytes.
  writeFileSync(fakeGhState, `${JSON.stringify({
    exists: false,
    draft: false,
    immutable: false,
    assets: [],
    downloads: 0,
    edits: 0,
  })}\n`);
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'unsafe untagged recovery']);
  const unsafeRecoverySha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  run(checkout, 'git', ['push', 'origin', 'main']);
  assert.throws(() => runShell(checkout, publishPath, {
    ...publishEnv,
    GITHUB_SHA: unsafeRecoverySha,
    QODO_RELEASE_COMMIT: releaseSha,
  }), /may only resume an existing draft/);
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', 'main']);
  writeFileSync(fakeGhState, `${JSON.stringify(recovered)}\n`);

  // A lightweight tag is not the promised release object.
  run(checkout, 'git', ['tag', '-d', releaseTag]);
  run(checkout, 'git', ['push', 'origin', `:refs/tags/${releaseTag}`]);
  run(checkout, 'git', ['-c', 'tag.gpgSign=false', 'tag', releaseTag, releaseSha]);
  run(checkout, 'git', ['push', 'origin', `refs/tags/${releaseTag}:refs/tags/${releaseTag}`]);
  assert.throws(() => runShell(checkout, publishPath, publishEnv), /is not an annotated tag/);
  run(checkout, 'git', ['tag', '-d', releaseTag]);
  run(checkout, 'git', ['-c', 'tag.gpgSign=false', 'tag', '--no-sign', '-a', releaseTag, '-m', releaseTag, releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', `refs/tags/${releaseTag}:refs/tags/${releaseTag}`]);

  // A published retry must fetch the remote tag instead of trusting a stale local copy.
  run(checkout, 'git', ['-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'drift fixture']);
  const driftSha = run(checkout, 'git', ['rev-parse', 'HEAD']).trim();
  run(checkout, 'git', ['reset', '--hard', releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', `${driftSha}:refs/tags/${releaseTag}`]);
  assert.throws(() => runShell(checkout, publishPath, publishEnv));
  run(checkout, 'git', ['-c', 'tag.gpgSign=false', 'tag', '-f', '-a', releaseTag, '-m', `restore ${releaseTag}`, releaseSha]);
  run(checkout, 'git', ['push', '--force', 'origin', `refs/tags/${releaseTag}:refs/tags/${releaseTag}`]);

  // A public immutable retry is verification-only; it must not republish.
  runShell(checkout, publishPath, publishEnv);
  const verifiedRetry = JSON.parse(readFileSync(fakeGhState, 'utf8'));
  assert.equal(verifiedRetry.edits, 1);
  assert.equal(verifiedRetry.downloads, verifiedRetry.assets.length + 2);

  // A resumed draft with an unexpected asset is rejected without mutation.
  const unexpectedDraft = {
    exists: true,
    draft: true,
    immutable: false,
    assets: ['qodo-skills-index.json', 'qodo-skills-index.json.sha256', 'stale-release.zip'],
    downloads: 0,
    edits: 0,
  };
  writeFileSync(fakeGhState, `${JSON.stringify(unexpectedDraft)}\n`);
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /unexpected asset inventory; refusing to replace anything/);
  assert.deepEqual(JSON.parse(readFileSync(fakeGhState, 'utf8')), unexpectedDraft);

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
  // A pre-existing public mutable release is never eligible for draft resume.
  const publicMutable = {
    exists: true,
    draft: false,
    immutable: false,
    assets: ['qodo-skills-index.json', 'qodo-skills-index.json.sha256'],
    downloads: 0,
    edits: 0,
  };
  writeFileSync(fakeGhState, `${JSON.stringify(publicMutable)}\n`);
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /Existing public release .* is mutable; refusing to overwrite its assets/);
  assert.deepEqual(JSON.parse(readFileSync(fakeGhState, 'utf8')), publicMutable);

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
    { draft: true, immutable: false, edits: 2 },
  );

  // A final-download mismatch burns the immutable version and fails the workflow.
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
    { draft: false, immutable: true, edits: 1, downloads: rejectedPublicBytes.assets.length + 1 },
  );
} finally {
  rmSync(harness, { recursive: true, force: true });
}
console.log('Release workflow safety test passed.');
await import('./test-release-tag-protection.mjs');

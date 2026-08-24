/** Exercise release preparation in an isolated repository copy. */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  appendFileSync,
  cpSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { incrementVersion } from './prepare-release.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const temporaryRoot = mkdtempSync(join(tmpdir(), 'qodo-skills-release-'));
const repositoryRoot = join(temporaryRoot, 'repository');
const sourceCatalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const expectedPackageVersion = incrementVersion(sourceCatalog.package.version, 'patch');
const sourceReview = sourceCatalog.skills.find((skill) => skill.name === 'qodo-review');
const expectedReviewVersion = incrementVersion(sourceReview.version, 'patch');

try {
  mkdirSync(repositoryRoot);
  for (const name of readdirSync(root)) {
    if (name === '.git' || name === 'node_modules') continue;
    cpSync(join(root, name), join(repositoryRoot, name), { recursive: true });
  }
  const reviewPath = join(repositoryRoot, 'skills', 'qodo-review', 'SKILL.md');
  writeFileSync(reviewPath, readFileSync(reviewPath, 'utf8').replace(/\r?\n/g, '\r\n'));
  execFileSync('git', ['init', '--quiet'], { cwd: repositoryRoot });
  execFileSync('git', ['config', 'user.name', 'Release Test'], { cwd: repositoryRoot });
  execFileSync('git', ['config', 'user.email', 'release-test@qodo.ai'], { cwd: repositoryRoot });
  execFileSync('git', ['config', 'core.autocrlf', 'false'], { cwd: repositoryRoot });
  execFileSync('git', ['config', 'core.safecrlf', 'false'], { cwd: repositoryRoot });
  execFileSync('git', ['config', 'commit.gpgsign', 'false'], { cwd: repositoryRoot });
  execFileSync('git', ['add', '.'], { cwd: repositoryRoot });
  execFileSync('git', ['commit', '--quiet', '-m', 'baseline'], { cwd: repositoryRoot });
  const base = execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: repositoryRoot,
    encoding: 'utf8',
  }).trim();
  execFileSync(process.execPath, [
    join(repositoryRoot, 'scripts', 'prepare-release.mjs'),
    '--summary', 'Exercise the release pipeline.',
    '--skill', 'qodo-review=patch',
  ], { cwd: repositoryRoot, stdio: 'pipe' });

  const catalog = JSON.parse(readFileSync(join(repositoryRoot, 'distribution', 'catalog.json'), 'utf8'));
  const review = catalog.skills.find((skill) => skill.name === 'qodo-review');
  const release = JSON.parse(readFileSync(
    join(repositoryRoot, 'releases', `v${expectedPackageVersion}.json`),
    'utf8',
  ));
  const claudeMarketplace = JSON.parse(readFileSync(join(repositoryRoot, '.claude-plugin', 'marketplace.json'), 'utf8'));
  const directBundlePath = join(repositoryRoot, 'distribution', 'qodo-skills-direct.json');
  const directBundleText = readFileSync(directBundlePath, 'utf8');
  const directBundle = JSON.parse(directBundleText);
  assert.equal(catalog.package.version, expectedPackageVersion);
  assert.equal(review.version, expectedReviewVersion);
  assert.equal(release.skills[0].version, expectedReviewVersion);
  assert.equal('version' in claudeMarketplace.plugins[0], false);
  assert.equal(directBundle.package.version, expectedPackageVersion);
  assert.equal(
    directBundle.skills.find((skill) => skill.name === 'qodo-review').version,
    expectedReviewVersion,
  );
  const directChecksum = readFileSync(`${directBundlePath}.sha256`, 'utf8').match(/^[a-f0-9]{64}/)?.[0];
  assert.equal(createHash('sha256').update(directBundleText).digest('hex'), directChecksum);
  const contentDigest = createHash('sha256');
  for (const installPackage of directBundle.packages) {
    contentDigest
      .update('package').update('\0')
      .update(installPackage.name).update('\0')
      .update(installPackage.default ? 'default' : 'optional').update('\0');
    for (const skillName of installPackage.skills) contentDigest.update(skillName).update('\0');
  }
  for (const skill of directBundle.skills) {
    for (const file of skill.files) {
      const fileDigest = createHash('sha256').update(file.content).digest('hex');
      assert.equal(fileDigest, file.sha256);
      contentDigest
        .update(skill.name).update('\0')
        .update(skill.version).update('\0')
        .update(file.path).update('\0')
        .update(file.sha256).update('\0');
    }
  }
  assert.equal(contentDigest.digest('hex'), directBundle.package.contentSha256);
  const releaseIndexPath = join(repositoryRoot, 'distribution', 'qodo-skills-index.json');
  const releaseIndexText = readFileSync(releaseIndexPath, 'utf8');
  const releaseIndex = JSON.parse(releaseIndexText);
  assert.equal(releaseIndex.packageVersion, expectedPackageVersion);
  assert.deepEqual(releaseIndex.skills['qodo-review'], {
    version: expectedReviewVersion,
    package: 'qodo',
  });
  const indexChecksum = readFileSync(`${releaseIndexPath}.sha256`, 'utf8').match(/^[a-f0-9]{64}/)?.[0];
  assert.equal(createHash('sha256').update(releaseIndexText).digest('hex'), indexChecksum);
  assert.match(
    readFileSync(join(repositoryRoot, 'skills', 'qodo-review', 'SKILL.md'), 'utf8'),
    new RegExp(`version: "${expectedReviewVersion.replaceAll('.', '\\.')}`),
  );
  execFileSync('git', ['add', '.'], { cwd: repositoryRoot });
  execFileSync('git', ['commit', '--quiet', '-m', 'release'], { cwd: repositoryRoot });
  execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'validate.mjs')], {
    cwd: repositoryRoot,
    stdio: 'pipe',
  });
  execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), base], {
    cwd: repositoryRoot,
    stdio: 'pipe',
  });

  const releaseCommit = execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: repositoryRoot,
    encoding: 'utf8',
  }).trim();
  appendFileSync(reviewPath, '\r\nUnversioned change.\r\n');
  execFileSync('git', ['add', '.'], { cwd: repositoryRoot });
  execFileSync('git', ['commit', '--quiet', '-m', 'invalid change'], { cwd: repositoryRoot });
  assert.throws(() => execFileSync(
    process.execPath,
    [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), releaseCommit],
    { cwd: repositoryRoot, stdio: 'pipe' },
  ));
  console.log('Release preparation test passed.');
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}

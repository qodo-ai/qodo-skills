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
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error('npm_execpath is unavailable; run this release test through npm test');

try {
  mkdirSync(repositoryRoot);
  for (const name of readdirSync(root)) {
    if (name === '.git' || name === 'node_modules') continue;
    cpSync(join(root, name), join(repositoryRoot, name), { recursive: true });
  }
  // Invoke npm's JavaScript entry point through Node. Spawning `npm.cmd`
  // directly is EINVAL on current Windows Node runners unless a shell is
  // enabled; avoiding the command wrapper is cross-platform and keeps shell
  // interpolation out of this isolated lockfile-install check.
  execFileSync(process.execPath, [
    npmCli,
    'ci',
    '--ignore-scripts',
    '--no-audit',
    '--no-fund',
  ], { cwd: repositoryRoot, stdio: 'pipe' });
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
  assert.throws(
    () => execFileSync(
      process.execPath,
      [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), 'not-a-commit'],
      { cwd: repositoryRoot, stdio: 'pipe' },
    ),
    (error) => {
      assert.match(String(error.stderr), /Base commit cannot be resolved: not-a-commit/);
      return true;
    },
  );
  const emptyTree = execFileSync('git', ['mktree'], {
    cwd: repositoryRoot,
    encoding: 'utf8',
    input: '',
  }).trim();
  const cataloglessBase = execFileSync(
    'git',
    ['commit-tree', emptyTree, '-m', 'catalogless base'],
    { cwd: repositoryRoot, encoding: 'utf8' },
  ).trim();
  assert.match(
    execFileSync(
      process.execPath,
      [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), cataloglessBase],
      { cwd: repositoryRoot, encoding: 'utf8' },
    ),
    /treating this as the initial release/,
  );
  assert.throws(
    () => execFileSync(process.execPath, [
      join(repositoryRoot, 'scripts', 'prepare-release.mjs'),
      '--summary', 'Invalid initial bump.',
      '--skill', 'qodo-review=initial',
    ], { cwd: repositoryRoot, stdio: 'pipe' }),
    (error) => {
      assert.match(String(error.stderr), /initial is only valid for a skill absent from the HEAD catalog/);
      return true;
    },
  );
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
  assert.equal(catalog.package.version, expectedPackageVersion);
  assert.equal(catalog.instructionMode, 'embedded');
  assert.equal(review.version, expectedReviewVersion);
  assert.equal(release.skills[0].version, expectedReviewVersion);
  assert.equal('version' in claudeMarketplace.plugins[0], false);
  const generatedReview = readFileSync(
    join(repositoryRoot, 'packages', 'qodo', 'skills', 'qodo-review', 'SKILL.md'),
    'utf8',
  );
  assert.match(generatedReview, /instruction_mode: "embedded"/);
  assert.match(generatedReview, /## Handle a skill update notice/);
  assert.doesNotMatch(generatedReview, /qodo help workflow/);
  assert.match(generatedReview, /--distribution marketplace --host claude-code/);
  const legacyResolver = readFileSync(
    join(repositoryRoot, 'packages', 'qodo', 'skills', 'qodo-pr-resolver', 'SKILL.md'),
    'utf8',
  );
  assert.match(legacyResolver, /^name: qodo-pr-resolver$/m);
  assert.match(legacyResolver, /Compatibility alias for explicit qodo-pr-resolver requests/);
  assert.match(legacyResolver, /--skill qodo-review-resolver .*--distribution marketplace --host claude-code/);
  const releaseIndexPath = join(repositoryRoot, 'distribution', 'qodo-skills-index.json');
  const releaseIndexText = readFileSync(releaseIndexPath, 'utf8');
  const releaseIndex = JSON.parse(releaseIndexText);
  assert.equal(releaseIndex.packageVersion, expectedPackageVersion);
  assert.equal(releaseIndex.instructionMode, 'embedded');
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

  const catalogPath = join(repositoryRoot, 'distribution', 'catalog.json');
  const validCatalogText = readFileSync(catalogPath, 'utf8');
  const schemaInvalidCatalog = JSON.parse(validCatalogText);
  delete schemaInvalidCatalog.package.description;
  writeFileSync(catalogPath, `${JSON.stringify(schemaInvalidCatalog, null, 2)}\n`);
  assert.throws(
    () => execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'validate.mjs')], {
      cwd: repositoryRoot,
      stdio: 'pipe',
    }),
    (error) => {
      assert.match(String(error.stderr), /catalog\.json: JSON Schema validation failed/);
      return true;
    },
  );
  writeFileSync(catalogPath, validCatalogText);

  for (const invalidVersion of ['01.0.3', '1.0.3-01']) {
    const invalidVersionCatalog = JSON.parse(validCatalogText);
    invalidVersionCatalog.package.version = invalidVersion;
    writeFileSync(catalogPath, `${JSON.stringify(invalidVersionCatalog, null, 2)}\n`);
    assert.throws(
      () => execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'validate.mjs')], {
        cwd: repositoryRoot,
        stdio: 'pipe',
      }),
      (error) => {
        assert.match(String(error.stderr), /catalog\.json: JSON Schema validation failed/);
        return true;
      },
    );
  }
  writeFileSync(catalogPath, validCatalogText);

  const releaseCommit = execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: repositoryRoot,
    encoding: 'utf8',
  }).trim();
  appendFileSync(reviewPath, '\r\nUnversioned change.\r\n');
  execFileSync('git', ['add', '.'], { cwd: repositoryRoot });
  execFileSync('git', ['commit', '--quiet', '-m', 'invalid change'], { cwd: repositoryRoot });
  assert.throws(
    () => execFileSync(
      process.execPath,
      [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), releaseCommit],
      { cwd: repositoryRoot, stdio: 'pipe' },
    ),
    (error) => {
      const lines = String(error.stderr).split(/\r?\n/).map((line) => line.trim());
      assert.ok(lines.includes(
        `- qodo-review version must increase from ${expectedReviewVersion}`,
      ));
      return true;
    },
  );

  const resetToRelease = () => {
    execFileSync('git', ['reset', '--hard', releaseCommit], { cwd: repositoryRoot, stdio: 'pipe' });
    execFileSync('git', ['clean', '-fd'], { cwd: repositoryRoot, stdio: 'pipe' });
  };
  const commitScenario = (message) => {
    execFileSync('git', ['add', '.'], { cwd: repositoryRoot });
    execFileSync('git', ['commit', '--quiet', '-m', message], { cwd: repositoryRoot });
  };
  const expectDiffFailure = (pattern) => assert.throws(
    () => execFileSync(
      process.execPath,
      [join(repositoryRoot, 'scripts', 'validate-diff.mjs'), releaseCommit],
      { cwd: repositoryRoot, stdio: 'pipe' },
    ),
    (error) => {
      assert.match(String(error.stderr), pattern);
      return true;
    },
  );

  resetToRelease();
  appendFileSync(join(repositoryRoot, 'scripts', 'sync-adapters.mjs'), '\n// packaging change\n');
  commitScenario('unversioned packaging change');
  expectDiffFailure(new RegExp(`package version must increase from ${expectedPackageVersion.replaceAll('.', '\\.')}`));

  resetToRelease();
  appendFileSync(join(repositoryRoot, 'scripts', 'prepare-release.mjs'), '\n// release generator change\n');
  commitScenario('unversioned release generator change');
  expectDiffFailure(new RegExp(`package version must increase from ${expectedPackageVersion.replaceAll('.', '\\.')}`));

  resetToRelease();
  appendFileSync(join(repositoryRoot, '.github', 'workflows', 'ship-marketplaces.yml'), '\n# release workflow change\n');
  commitScenario('unversioned marketplace workflow change');
  expectDiffFailure(new RegExp(`package version must increase from ${expectedPackageVersion.replaceAll('.', '\\.')}`));

  resetToRelease();
  const deletionCatalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  deletionCatalog.skills = deletionCatalog.skills.filter((skill) => skill.name !== 'qodo-review');
  for (const installPackage of deletionCatalog.installPackages) {
    installPackage.skills = installPackage.skills.filter((name) => name !== 'qodo-review');
  }
  writeFileSync(catalogPath, `${JSON.stringify(deletionCatalog, null, 2)}\n`);
  rmSync(join(repositoryRoot, 'skills', 'qodo-review'), { recursive: true, force: true });
  commitScenario('unsupported skill removal');
  expectDiffFailure(/qodo-review was removed without a supported immutable removal record/);

  resetToRelease();
  const catalogOnlyBump = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const catalogOnlyReview = catalogOnlyBump.skills.find((skill) => skill.name === 'qodo-review');
  catalogOnlyReview.version = incrementVersion(catalogOnlyReview.version, 'patch');
  writeFileSync(catalogPath, `${JSON.stringify(catalogOnlyBump, null, 2)}\n`);
  commitScenario('catalog-only skill bump');
  expectDiffFailure(new RegExp(`qodo-review must appear in the v${expectedPackageVersion.replaceAll('.', '\\.')} release record`));

  resetToRelease();
  const metadataOnlyChange = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const metadataOnlyReview = metadataOnlyChange.skills.find((skill) => skill.name === 'qodo-review');
  metadataOnlyReview.shortDescription = `${metadataOnlyReview.shortDescription} Updated.`;
  writeFileSync(catalogPath, `${JSON.stringify(metadataOnlyChange, null, 2)}\n`);
  commitScenario('unversioned skill metadata change');
  expectDiffFailure(new RegExp(`qodo-review version must increase from ${expectedReviewVersion.replaceAll('.', '\\.')}`));

  resetToRelease();
  execFileSync(process.execPath, [
    join(repositoryRoot, 'scripts', 'prepare-release.mjs'),
    '--summary', 'Exercise semantic change validation.',
    '--skill', 'qodo-review=minor',
  ], { cwd: repositoryRoot, stdio: 'pipe' });
  const mislabeledCatalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const mislabeledReleasePath = join(repositoryRoot, 'releases', `v${mislabeledCatalog.package.version}.json`);
  const mislabeledRelease = JSON.parse(readFileSync(mislabeledReleasePath, 'utf8'));
  mislabeledRelease.package.change = 'patch';
  mislabeledRelease.skills[0].change = 'patch';
  writeFileSync(mislabeledReleasePath, `${JSON.stringify(mislabeledRelease, null, 2)}\n`);
  commitScenario('mislabel semantic changes');
  expectDiffFailure(/release package\.change must be minor[\s\S]*qodo-review release change must be minor/);

  console.log('Release preparation test passed.');
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

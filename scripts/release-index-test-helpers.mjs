import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export function buildReleaseIndexFixture(sourceRoot, outputDirectory, sourceCommit) {
  execFileSync(process.execPath, [
    join(sourceRoot, 'scripts', 'build-release-index.mjs'),
    '--output-dir', outputDirectory,
    '--source-commit', sourceCommit,
  ], { cwd: sourceRoot, stdio: 'pipe' });
}

export function assertReleaseIndexWorkflowContract(workflow) {
  assert.match(workflow, /qodo-release-source\/scripts\/build-release-index\.mjs/);
  assert.match(workflow, /--source-commit "\$\{RELEASE_COMMIT\}"/);
  assert.match(workflow, /--release-index "\$\{RUNNER_TEMP\}\/qodo-release-index\/qodo-skills-index\.json"/);
  assert.ok(
    workflow.indexOf('build-release-index.mjs') < workflow.indexOf('build-enterprise-bundle.mjs'),
    'the enterprise manifest must consume the already-generated release index',
  );
  assert.match(workflow, /QODO_RELEASE_INDEX_DIR: \$\{\{ runner\.temp \}\}\/qodo-release-index/);
}

export function assertMismatchedReleaseIndexRejected({
  checkout, indexDirectory, publishEnvironment, publishPath, releaseSource, releaseCommit, runShell,
}) {
  const indexPath = join(indexDirectory, 'qodo-skills-index.json');
  const index = JSON.parse(readFileSync(indexPath, 'utf8'));
  index.sourceCommit = '0'.repeat(40);
  const text = `${JSON.stringify(index, null, 2)}\n`;
  writeFileSync(indexPath, text);
  writeFileSync(`${indexPath}.sha256`,
    `${createHash('sha256').update(text).digest('hex')}  qodo-skills-index.json\n`);
  assert.throws(() => runShell(checkout, publishPath, publishEnvironment),
    /release index sourceCommit does not match QODO_RELEASE_COMMIT/);
  buildReleaseIndexFixture(releaseSource, indexDirectory, releaseCommit);
}

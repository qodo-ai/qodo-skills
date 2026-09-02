import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export function assertDiscoveryPublisherSource(publisher) {
  assert.match(publisher, /if ! DISCOVERY_ASSET_ROWS="\$\(node -e/,
    'discovery inventory parsing must propagate producer failures');
  assert.match(publisher, /verify_discovery_digest "\$\{ENTERPRISE_DIR\}\/\$\{discovery_asset\}"/,
    'local discovery assets must match manifest digests before publication');
  assert.match(publisher, /verify_discovery_digest "\$\{directory\}\/\$\{discovery_asset\}"/,
    'downloaded discovery assets must match manifest digests');
}

export function assertDiscoveryManifestFailures({
  publisher,
  enterpriseDir,
  checkout,
  publishPath,
  publishEnv,
  releaseTag,
  run,
  runShell,
}) {
  assertDiscoveryPublisherSource(publisher);
  const manifestPath = join(enterpriseDir, 'qodo-enterprise-manifest.json');
  const checksumPath = `${manifestPath}.sha256`;
  const originalManifest = readFileSync(manifestPath);
  const originalChecksum = readFileSync(checksumPath);
  const writeManifest = (manifest) => {
    const payload = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`);
    writeFileSync(manifestPath, payload);
    writeFileSync(checksumPath,
      `${createHash('sha256').update(payload).digest('hex')}  qodo-enterprise-manifest.json\n`);
  };

  const invalidInventory = JSON.parse(originalManifest);
  invalidInventory.discovery.packages[0].index.name = '../escaped-index.json';
  writeManifest(invalidInventory);
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /Could not enumerate and validate the discovery asset inventory/);
  assert.equal(run(checkout, 'git', ['ls-remote', '--tags', 'origin', releaseTag]).trim(), '');

  const invalidDigest = JSON.parse(originalManifest);
  invalidDigest.discovery.packages[0].index.sha256 = '0'.repeat(64);
  writeManifest(invalidDigest);
  assert.throws(() => runShell(checkout, publishPath, publishEnv),
    /Discovery asset digest mismatch: qodo-agent-skills-core-index\.json/);
  assert.equal(run(checkout, 'git', ['ls-remote', '--tags', 'origin', releaseTag]).trim(), '');

  writeFileSync(manifestPath, originalManifest);
  writeFileSync(checksumPath, originalChecksum);
}

/** Verify deterministic enterprise release assets and package isolation. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { gunzipSync } from 'node:zlib';
import { buildEnterpriseBundle } from './build-enterprise-bundle.mjs';

const commit = '0123456789abcdef0123456789abcdef01234567';

function sha256(payload) {
  return createHash('sha256').update(payload).digest('hex');
}

function tarFiles(archive) {
  const tar = gunzipSync(archive);
  const files = new Map();
  for (let offset = 0; offset + 512 <= tar.length;) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every((byte) => byte === 0)) break;
    const text = (start, length) => header.subarray(start, start + length).toString().replace(/\0.*$/, '');
    const name = text(0, 100);
    const prefix = text(345, 155);
    const path = prefix ? `${prefix}/${name}` : name;
    const size = Number.parseInt(text(124, 12).trim() || '0', 8);
    const storedChecksum = Number.parseInt(text(148, 8).trim(), 8);
    const checksumHeader = Buffer.from(header);
    checksumHeader.fill(0x20, 148, 156);
    assert.equal(checksumHeader.reduce((sum, byte) => sum + byte, 0), storedChecksum, `${path}: tar checksum`);
    const start = offset + 512;
    files.set(path, tar.subarray(start, start + size));
    offset = start + Math.ceil(size / 512) * 512;
  }
  return files;
}

const firstRoot = mkdtempSync(join(tmpdir(), 'qodo-enterprise-first-'));
const secondRoot = mkdtempSync(join(tmpdir(), 'qodo-enterprise-second-'));
try {
  const first = buildEnterpriseBundle({ output: firstRoot, commit });
  const second = buildEnterpriseBundle({ output: secondRoot, commit });
  assert.equal(first.version, '1.0.6');
  assert.equal(first.archiveName, 'qodo-enterprise-bundle-v1.0.6.tar.gz');

  const firstArchive = readFileSync(join(firstRoot, first.archiveName));
  const secondArchive = readFileSync(join(secondRoot, second.archiveName));
  assert.deepEqual(firstArchive, secondArchive, 'enterprise archive must be byte-deterministic');
  assert.equal(first.archiveSha256, sha256(firstArchive));
  assert.equal(
    readFileSync(join(firstRoot, `${first.archiveName}.sha256`), 'utf8'),
    `${first.archiveSha256}  ${first.archiveName}\n`,
  );

  const manifestPayload = readFileSync(join(firstRoot, first.manifestName));
  const manifest = JSON.parse(manifestPayload);
  assert.equal(manifest.packageVersion, '1.0.6');
  assert.deepEqual(manifest.source, {
    repository: 'https://github.com/qodo-ai/qodo-skills',
    commit,
    tag: 'v1.0.6',
  });
  assert.deepEqual(manifest.archive, { name: first.archiveName, sha256: first.archiveSha256 });
  assert.equal(manifest.index.name, 'qodo-skills-index.json');
  assert.equal(
    readFileSync(join(firstRoot, `${first.manifestName}.sha256`), 'utf8'),
    `${sha256(manifestPayload)}  ${first.manifestName}\n`,
  );

  const files = tarFiles(firstArchive);
  assert.ok(files.has('qodo-enterprise/README.md'));
  assert.ok(files.has('qodo-enterprise/bundle.json'));
  assert.ok(![...files.keys()].some((path) => path.endsWith('/qodo.mjs')), 'CLI bytes must remain a separate release');
  assert.doesNotMatch(firstArchive.toString(), /BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY/);
  for (const provider of ['claude', 'codex', 'kiro', 'portable']) {
    assert.ok([...files.keys()].some((path) => path.startsWith(`qodo-enterprise/${provider}/qodo/`)));
    assert.ok([...files.keys()].some((path) => path.startsWith(`qodo-enterprise/${provider}/qodo-standards/`)));
  }
  const core = manifest.packages.find((entry) => entry.name === 'qodo');
  const standards = manifest.packages.find((entry) => entry.name === 'qodo-standards');
  assert.equal(core.default, true);
  assert.equal(standards.default, false);
  assert.ok(!core.skills.includes('qodo-get-rules'));
  assert.deepEqual(standards.skills.sort(), ['qodo-get-rules', 'qodo-manage-standards']);

  const skillFiles = [...files].filter(([path]) => path.endsWith('/SKILL.md'));
  assert.ok(skillFiles.length > 0);
  for (const [path, payload] of skillFiles) {
    const text = payload.toString();
    assert.match(text, /  distribution: "enterprise-bundle"/);
    assert.match(text, /--distribution enterprise-bundle/);
    assert.doesNotMatch(text, /--distribution (?:skills-sh|marketplace|kiro-power)(?:\s|$)/);
    assert.doesNotMatch(text, /  distribution: "(?:skills-sh|marketplace|kiro-power)"/);
    assert.ok(path.startsWith('qodo-enterprise/'));
  }
} finally {
  rmSync(firstRoot, { recursive: true, force: true });
  rmSync(secondRoot, { recursive: true, force: true });
}

console.log('Enterprise bundle tests passed.');

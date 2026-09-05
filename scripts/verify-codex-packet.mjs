/** Verify a downloaded Codex marketplace packet before portal upload. */
import {
  lstatSync,
  readFileSync,
  readdirSync,
  realpathSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { basename, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function readRegularFile(path) {
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`${path}: expected a regular file`);
  return { bytes: readFileSync(path), sizeBytes: stat.size };
}

function readJson(path) {
  const { bytes } = readRegularFile(path);
  try {
    return JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    throw new Error(`${path}: invalid JSON: ${error.message}`);
  }
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function artifactPath(value) {
  if (!/^bundles\/[a-z0-9][a-z0-9.-]*\.zip$/.test(value ?? '')) {
    throw new Error(`Unsafe Codex artifact path: ${value ?? '<missing>'}`);
  }
  return value;
}

function checksumRecords(path) {
  const { bytes } = readRegularFile(path);
  const records = new Map();
  for (const line of bytes.toString('utf8').trim().split('\n')) {
    const match = line.match(/^([0-9a-f]{64})  ([a-z0-9][a-z0-9.-]*\.zip)$/);
    if (!match) throw new Error(`${path}: invalid checksum record: ${line}`);
    if (records.has(match[2])) throw new Error(`${path}: duplicate checksum record for ${match[2]}`);
    records.set(match[2], match[1]);
  }
  if (records.size === 0) throw new Error(`${path}: checksum inventory is empty`);
  return records;
}

function sameJson(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function storedZipEntry(archive, targetName) {
  let offset = 0;
  let target;
  while (offset + 30 <= archive.length && archive.readUInt32LE(offset) === 0x04034b50) {
    const flags = archive.readUInt16LE(offset + 6);
    const method = archive.readUInt16LE(offset + 8);
    const compressedSize = archive.readUInt32LE(offset + 18);
    const uncompressedSize = archive.readUInt32LE(offset + 22);
    const nameLength = archive.readUInt16LE(offset + 26);
    const extraLength = archive.readUInt16LE(offset + 28);
    if ((flags & 0x0008) !== 0 || method !== 0 || compressedSize !== uncompressedSize) {
      throw new Error('Codex bundle must use deterministic stored ZIP entries');
    }
    const nameStart = offset + 30;
    const dataStart = nameStart + nameLength + extraLength;
    const dataEnd = dataStart + compressedSize;
    if (dataEnd > archive.length) throw new Error('Codex bundle contains a truncated ZIP entry');
    const name = archive.subarray(nameStart, nameStart + nameLength).toString('utf8');
    if (name === targetName) {
      if (target) throw new Error(`Codex bundle contains duplicate ${targetName} entries`);
      target = archive.subarray(dataStart, dataEnd);
    }
    offset = dataEnd;
  }
  if (offset + 4 > archive.length || archive.readUInt32LE(offset) !== 0x02014b50) {
    throw new Error('Codex bundle local entries do not end at a central directory');
  }
  if (!target) throw new Error(`Codex bundle is missing ${targetName}`);
  return target;
}

export function verifyCodexPacket(packetRoot) {
  const root = resolve(packetRoot);
  const release = readJson(join(root, 'release.json'));
  if (release.provider !== 'codex' || release.providerMode !== 'reviewed-portal-snapshot') {
    throw new Error('release.json is not a reviewed Codex portal packet');
  }
  if (!Array.isArray(release.listings) || release.listings.length === 0) {
    throw new Error('release.json has no Codex listings');
  }
  const listingIds = new Set();
  for (const listing of release.listings) {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(listing.id ?? '')) throw new Error('release.json has an invalid listing id');
    if (listingIds.has(listing.id)) throw new Error(`release.json has a duplicate listing: ${listing.id}`);
    listingIds.add(listing.id);
  }
  if (!Array.isArray(release.artifacts) || release.artifacts.length !== listingIds.size) {
    throw new Error('release.json must have exactly one artifact per Codex listing');
  }
  if (release.artifacts.length === 0) {
    throw new Error('release.json has no Codex upload artifacts');
  }
  const checksums = checksumRecords(join(root, 'bundles', 'SHA256SUMS'));
  const expectedArchives = new Set();
  const artifactListingIds = new Set();
  const verified = [];

  for (const artifact of release.artifacts) {
    if (!listingIds.has(artifact.listingId)) throw new Error(`Unknown listing artifact: ${artifact.listingId}`);
    if (artifactListingIds.has(artifact.listingId)) {
      throw new Error(`Duplicate artifact for Codex listing: ${artifact.listingId}`);
    }
    artifactListingIds.add(artifact.listingId);
    const relativePath = artifactPath(artifact.path);
    const archiveName = basename(relativePath);
    if (expectedArchives.has(archiveName)) throw new Error(`Duplicate Codex artifact: ${archiveName}`);
    expectedArchives.add(archiveName);
    const archive = readRegularFile(join(root, relativePath));
    const digest = sha256(archive.bytes);
    if (artifact.sha256 !== digest) throw new Error(`${archiveName}: release.json SHA-256 mismatch`);
    if (artifact.sizeBytes !== archive.sizeBytes) throw new Error(`${archiveName}: release.json size mismatch`);
    if (checksums.get(archiveName) !== digest) throw new Error(`${archiveName}: SHA256SUMS mismatch`);
    let plugin;
    try {
      plugin = JSON.parse(storedZipEntry(archive.bytes, '.codex-plugin/plugin.json').toString('utf8'));
    } catch (error) {
      throw new Error(`${archiveName}: invalid internal plugin manifest: ${error.message}`);
    }
    if (plugin.name !== artifact.listingId || plugin.version !== release.version) {
      throw new Error(`${archiveName}: internal plugin identity does not match ${artifact.listingId}@${release.version}`);
    }

    const submission = readJson(join(root, 'submissions', `${artifact.listingId}.json`));
    if (submission.listingId !== artifact.listingId || !sameJson(submission.artifact, artifact)) {
      throw new Error(`${artifact.listingId}: submission artifact metadata mismatch`);
    }
    if (!sameJson(submission.release, {
      tag: release.tag,
      commit: release.commit,
      version: release.version,
    })) {
      throw new Error(`${artifact.listingId}: submission release identity mismatch`);
    }
    verified.push({ listingId: artifact.listingId, path: relativePath, sha256: digest });
  }

  if ([...listingIds].some((listingId) => !artifactListingIds.has(listingId))) {
    throw new Error('release.json is missing a Codex listing artifact');
  }
  if (checksums.size !== expectedArchives.size) throw new Error('SHA256SUMS contains an undeclared archive');
  const actualArchives = readdirSync(join(root, 'bundles'), { withFileTypes: true })
    .filter((entry) => entry.name.endsWith('.zip'));
  if (actualArchives.some((entry) => !entry.isFile() || entry.isSymbolicLink())) {
    throw new Error('bundles contains a non-regular ZIP entry');
  }
  const actualNames = new Set(actualArchives.map((entry) => entry.name));
  if (actualNames.size !== expectedArchives.size || [...actualNames].some((name) => !expectedArchives.has(name))) {
    throw new Error('bundles contains an undeclared or missing ZIP archive');
  }
  return { provider: 'codex', tag: release.tag, commit: release.commit, verified };
}

if (realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(JSON.stringify(verifyCodexPacket(process.argv[2] ?? process.cwd())));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

/** Create a deterministic, uncompressed ZIP archive using only Node built-ins. */
import {
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, relative, resolve, sep } from 'node:path';

const UTF8_FLAG = 0x0800;
const STORED_METHOD = 0;
const DOS_TIME = 0;
const DOS_DATE = (1 << 5) | 1; // 1980-01-01, the earliest ZIP timestamp.
const UNIX_REGULAR_FILE_0644 = (0o100644 << 16) >>> 0;
const ZIP32_MAX = 0xffffffff;

function compareNames(left, right) {
  return left.name < right.name ? -1 : left.name > right.name ? 1 : 0;
}

const crcTable = Array.from({ length: 256 }, (_, value) => {
  let crc = value;
  for (let bit = 0; bit < 8; bit += 1) {
    crc = (crc & 1) === 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
  }
  return crc >>> 0;
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) crc = (crc >>> 8) ^ crcTable[(crc ^ byte) & 0xff];
  return (crc ^ 0xffffffff) >>> 0;
}

function archiveName(root, path) {
  const name = relative(root, path).split(sep).join('/');
  if (!name || name.startsWith('/') || name.split('/').includes('..') || name.includes('\\')) {
    throw new Error(`${path}: unsafe ZIP entry name`);
  }
  return name;
}

function collectFiles(root, directory = root, files = []) {
  const entries = readdirSync(directory, { withFileTypes: true })
    .sort(compareNames);
  for (const entry of entries) {
    const path = join(directory, entry.name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) throw new Error(`${path}: symbolic links are not allowed in provider bundles`);
    if (stat.isDirectory()) collectFiles(root, path, files);
    else if (stat.isFile()) files.push({ name: archiveName(root, path), path });
    else throw new Error(`${path}: unsupported filesystem entry in provider bundle`);
  }
  return files;
}

function localHeader(name, data, checksum) {
  const header = Buffer.alloc(30);
  header.writeUInt32LE(0x04034b50, 0);
  header.writeUInt16LE(20, 4);
  header.writeUInt16LE(UTF8_FLAG, 6);
  header.writeUInt16LE(STORED_METHOD, 8);
  header.writeUInt16LE(DOS_TIME, 10);
  header.writeUInt16LE(DOS_DATE, 12);
  header.writeUInt32LE(checksum, 14);
  header.writeUInt32LE(data.length, 18);
  header.writeUInt32LE(data.length, 22);
  header.writeUInt16LE(name.length, 26);
  return header;
}

function centralHeader(name, data, checksum, offset) {
  const header = Buffer.alloc(46);
  header.writeUInt32LE(0x02014b50, 0);
  header.writeUInt16LE(0x0314, 4); // ZIP 2.0, created on Unix.
  header.writeUInt16LE(20, 6);
  header.writeUInt16LE(UTF8_FLAG, 8);
  header.writeUInt16LE(STORED_METHOD, 10);
  header.writeUInt16LE(DOS_TIME, 12);
  header.writeUInt16LE(DOS_DATE, 14);
  header.writeUInt32LE(checksum, 16);
  header.writeUInt32LE(data.length, 20);
  header.writeUInt32LE(data.length, 24);
  header.writeUInt16LE(name.length, 28);
  header.writeUInt32LE(UNIX_REGULAR_FILE_0644, 38);
  header.writeUInt32LE(offset, 42);
  return header;
}

function endRecord(entryCount, centralSize, centralOffset) {
  const record = Buffer.alloc(22);
  record.writeUInt32LE(0x06054b50, 0);
  record.writeUInt16LE(entryCount, 8);
  record.writeUInt16LE(entryCount, 10);
  record.writeUInt32LE(centralSize, 12);
  record.writeUInt32LE(centralOffset, 16);
  return record;
}

/** Read only our deterministic ZIP32 format, validating both extractor inventories. */
export function readDeterministicZip(archive) {
  const entries = new Map();
  const centralParts = [];
  let offset = 0;
  let previousName;
  const invalid = (reason) => { throw new Error(`Invalid deterministic ZIP: ${reason}`); };
  while (offset + 4 <= archive.length && archive.readUInt32LE(offset) === 0x04034b50) {
    if (offset + 30 > archive.length) invalid('truncated local header');
    const nameLength = archive.readUInt16LE(offset + 26);
    const size = archive.readUInt32LE(offset + 18);
    const nameStart = offset + 30;
    const dataStart = nameStart + nameLength;
    const dataEnd = dataStart + size;
    if (dataEnd > archive.length) invalid('truncated local entry');
    const nameBytes = archive.subarray(nameStart, dataStart);
    const name = nameBytes.toString('utf8');
    if (!Buffer.from(name, 'utf8').equals(nameBytes) || /[\\\x00:]/.test(name) ||
        name.split('/').some((part) => !part || part === '.' || part === '..')) {
      invalid('unsafe or malformed entry name');
    }
    if (previousName !== undefined && name <= previousName) invalid('duplicate or unordered entry');
    const data = archive.subarray(dataStart, dataEnd);
    const checksum = crc32(data);
    if (!archive.subarray(offset, nameStart).equals(localHeader(nameBytes, data, checksum))) {
      invalid('local header, sizes or CRC do not match the stored entry');
    }
    centralParts.push(centralHeader(nameBytes, data, checksum, offset), nameBytes);
    entries.set(name, data);
    if (entries.size > 0xffff) invalid('too many ZIP32 entries');
    previousName = name;
    offset = dataEnd;
  }
  if (entries.size === 0) invalid('missing local entries');
  const central = Buffer.concat(centralParts);
  const centralEnd = offset + central.length;
  if (!archive.subarray(offset, centralEnd).equals(central)) {
    invalid('central directory does not match local entries');
  }
  if (!archive.subarray(centralEnd).equals(endRecord(entries.size, central.length, offset))) {
    invalid('end record, directory bounds or archive length do not match');
  }
  return entries;
}

export function createDeterministicZip(sourceRoot, outputPath) {
  const root = resolve(sourceRoot);
  const stat = lstatSync(root);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`${sourceRoot}: ZIP source must be a directory`);
  const files = collectFiles(root).sort(compareNames);
  if (files.length === 0) throw new Error(`${sourceRoot}: refusing to create an empty provider bundle`);
  if (files.length > 0xffff) throw new Error(`${sourceRoot}: too many files for a ZIP32 archive`);

  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const file of files) {
    const name = Buffer.from(file.name, 'utf8');
    const data = readFileSync(file.path);
    if (name.length > 0xffff || data.length > ZIP32_MAX) throw new Error(`${file.path}: too large for a ZIP32 archive`);
    const checksum = crc32(data);
    const local = localHeader(name, data, checksum);
    if (offset + local.length + name.length + data.length > ZIP32_MAX) {
      throw new Error(`${sourceRoot}: provider bundle exceeds the ZIP32 archive limit`);
    }
    localParts.push(local, name, data);
    centralParts.push(centralHeader(name, data, checksum, offset), name);
    offset += local.length + name.length + data.length;
  }

  const central = Buffer.concat(centralParts);
  if (central.length > ZIP32_MAX) throw new Error(`${sourceRoot}: ZIP central directory exceeds the ZIP32 limit`);
  const archive = Buffer.concat([...localParts, central, endRecord(files.length, central.length, offset)]);
  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, archive);
  return {
    files: files.map((file) => file.name),
    sha256: createHash('sha256').update(archive).digest('hex'),
    sizeBytes: archive.length,
  };
}

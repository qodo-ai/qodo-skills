import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { inputPath } from '../../scripts/eval-review-skill.mjs';

export const hashEvidence = (bytes) => createHash('sha256').update(bytes).digest('hex');

export function readEvidenceFile(root, path) {
  assert.ok(typeof path === 'string' && path && !path.includes('\\') && !path.includes(':')
    && !path.split('/').some((part) => ['', '.', '..'].includes(part)), 'Unsafe evidence path');
  return readFileSync(inputPath(root, join(root, path), 'file'));
}

function listFiles(root, path = '') {
  const directory = inputPath(root, join(root, path), 'directory');
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const name = path ? `${path}/${entry.name}` : entry.name;
    if (entry.isDirectory()) return listFiles(root, name);
    inputPath(root, join(root, name), 'file');
    return [name];
  }).sort();
}

export function assertArtifactArchive(root, entry, directory, label) {
  assert.ok(entry, `Missing required ${label} archive`);
  assert.equal(entry.path, `${directory}/archive.json`);
  assert.match(entry.sha256, /^[a-f0-9]{64}$/);
  const bytes = readEvidenceFile(root, entry.path);
  assert.equal(hashEvidence(bytes), entry.sha256, `Changed ${label} archive`);
  const archive = JSON.parse(bytes), paths = Object.keys(archive.artifacts);
  assert.ok(paths.length, 'Historical archive is empty');
  assert.deepEqual(paths.sort(), listFiles(root, directory).map((path) => path.slice(directory.length + 1))
    .filter((path) => path !== 'archive.json'), `Historical ${label} inventory changed`);
  for (const [path, expected] of Object.entries(archive.artifacts)) {
    assert.match(expected, /^[a-f0-9]{64}$/);
    assert.equal(hashEvidence(readEvidenceFile(root, `${directory}/${path}`)), expected,
      `Changed historical artifact: ${label}/${path}`);
  }
  return paths.length;
}

export function assertHistoryArchives(root, manifest) {
  return Object.fromEntries([6, 7, 8, 9, 10, 11, 12, 13, 14].map((iteration) => {
    const entry = manifest.history?.[`iteration_${iteration}`];
    assert.ok(entry, `Missing required iteration${iteration} history`);
    return [iteration, assertArtifactArchive(root, entry, `history/iteration-${iteration}`, `iteration${iteration}`)];
  }));
}

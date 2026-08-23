/** Enforce release versioning for pull-request changes to canonical skills. */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const base = process.argv[2];
if (!base) {
  console.error('Usage: node scripts/validate-diff.mjs <base-commit>');
  process.exit(1);
}

function git(...args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim();
}

function stableVersion(version) {
  const match = version?.match(/^(\d+)\.(\d+)\.(\d+)$/);
  return match ? match.slice(1).map(Number) : null;
}

function isGreater(current, prior) {
  const left = stableVersion(current);
  const right = stableVersion(prior);
  if (!left || !right) return false;
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] > right[index];
  }
  return false;
}

let baseCatalog;
try {
  baseCatalog = JSON.parse(git('show', `${base}:distribution/catalog.json`));
} catch {
  console.log('Base commit has no distribution catalog; treating this as the initial release.');
  process.exit(0);
}

const catalog = JSON.parse(readFileSync('distribution/catalog.json', 'utf8'));
const files = git('diff', '--name-only', `${base}...HEAD`).split('\n').filter(Boolean);
const statuses = git('diff', '--name-status', `${base}...HEAD`)
  .split('\n')
  .filter(Boolean)
  .map((line) => line.split('\t'));
const changedSkills = new Set(
  files.flatMap((path) => path.match(/^skills\/([^/]+)\//)?.[1] ?? []),
);
const catalogChanged = files.includes('distribution/catalog.json');
const changedReleaseRecords = statuses.filter(([, path]) => path?.startsWith('releases/'));
if (!changedSkills.size && !catalogChanged && !changedReleaseRecords.length) process.exit(0);

const errors = [];
if (!isGreater(catalog.package.version, baseCatalog.package.version)) {
  errors.push(`package version must increase from ${baseCatalog.package.version}`);
}
const release = JSON.parse(readFileSync(`releases/v${catalog.package.version}.json`, 'utf8'));
const expectedReleasePath = `releases/v${catalog.package.version}.json`;
for (const [status, path] of changedReleaseRecords) {
  if (status !== 'A' || path !== expectedReleasePath) {
    errors.push(`release records are immutable; only add ${expectedReleasePath}`);
  }
}
if (!statuses.some(([status, path]) => status === 'A' && path === expectedReleasePath)) {
  errors.push(`${expectedReleasePath} must be added with this release`);
}
for (const name of changedSkills) {
  const current = catalog.skills.find((skill) => skill.name === name);
  const prior = baseCatalog.skills.find((skill) => skill.name === name);
  if (!current) continue;
  if (prior && !isGreater(current.version, prior.version)) {
    errors.push(`${name} version must increase from ${prior.version}`);
  }
  if (!release.skills.some((skill) => skill.name === name && skill.version === current.version)) {
    errors.push(`${name} must appear in the v${catalog.package.version} release record`);
  }
}

if (errors.length) {
  console.error(`Release diff validation failed:\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(`Release diff is versioned as v${catalog.package.version}.`);

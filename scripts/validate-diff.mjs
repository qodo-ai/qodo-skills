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

function changeLevel(current, prior) {
  const left = stableVersion(current);
  const right = stableVersion(prior);
  if (!left || !right || !isGreater(current, prior)) return null;
  if (left[0] !== right[0]) return 'major';
  if (left[1] !== right[1]) return 'minor';
  return 'patch';
}

try {
  git('cat-file', '-e', `${base}^{commit}`);
} catch {
  console.error(`Base commit cannot be resolved: ${base}`);
  process.exit(1);
}

const baseCatalogPath = git(
  'ls-tree',
  '--name-only',
  base,
  '--',
  'distribution/catalog.json',
);
if (!baseCatalogPath) {
  console.log('Base commit has no distribution catalog; treating this as the initial release.');
  process.exit(0);
}

let baseCatalog;
try {
  baseCatalog = JSON.parse(git('show', `${base}:distribution/catalog.json`));
} catch (error) {
  console.error(`Base distribution catalog is unreadable or invalid: ${error.message}`);
  process.exit(1);
}

const catalog = JSON.parse(readFileSync('distribution/catalog.json', 'utf8'));
const files = git('diff', '--name-only', `${base}...HEAD`).split('\n').filter(Boolean);
const statuses = git('diff', '--name-status', `${base}...HEAD`)
  .split('\n')
  .filter(Boolean)
  .map((line) => line.split('\t'));
const changedSkills = new Set(
  files.flatMap((path) => {
    const match = path.match(/^skills\/([^/]+)\/(.+)$/);
    return match && !match[2].startsWith('agents/') ? match[1] : [];
  }),
);
const currentSkills = new Map((catalog.skills ?? []).map((skill) => [skill.name, skill]));
const priorSkills = new Map((baseCatalog.skills ?? []).map((skill) => [skill.name, skill]));
for (const [name, current] of currentSkills) {
  const prior = priorSkills.get(name);
  if (!prior || current.version !== prior.version) changedSkills.add(name);
}
const catalogChanged = files.includes('distribution/catalog.json');
const changedReleaseRecords = statuses.filter(([, path]) => path?.startsWith('releases/'));
const versionedPackagePaths = [
  /^\.github\/workflows\/ship-marketplaces\.yml$/,
  /^\.agents\/plugins\//,
  /^\.claude-plugin\//,
  /^codex-packages\//,
  /^kiro-power(?:-standards)?\//,
  /^packages\//,
  /^distribution\/(?:codex-submissions|marketplaces)(?:\.schema)?\.json$/,
  /^scripts\/(?:build-release-index|marketplace-release|skill-provenance|sync-adapters)\.mjs$/,
  /^scripts\/verify-kiro-release-source\.sh$/,
];
const packagingChanged = files.some((path) => versionedPackagePaths.some((pattern) => pattern.test(path)));
if (!changedSkills.size && !catalogChanged && !changedReleaseRecords.length && !packagingChanged) {
  process.exit(0);
}

const errors = [];
for (const name of priorSkills.keys()) {
  if (!currentSkills.has(name)) {
    errors.push(`${name} was removed without a supported immutable removal record`);
  }
}
if (!isGreater(catalog.package.version, baseCatalog.package.version)) {
  errors.push(`package version must increase from ${baseCatalog.package.version}`);
}
const expectedReleasePath = `releases/v${catalog.package.version}.json`;
let release = { package: {}, skills: [] };
try {
  release = JSON.parse(readFileSync(expectedReleasePath, 'utf8'));
} catch (error) {
  errors.push(`${expectedReleasePath} must exist and contain valid JSON: ${error.message}`);
}
for (const [status, path] of changedReleaseRecords) {
  if (status !== 'A' || path !== expectedReleasePath) {
    errors.push(`release records are immutable; only add ${expectedReleasePath}`);
  }
}
if (!statuses.some(([status, path]) => status === 'A' && path === expectedReleasePath)) {
  errors.push(`${expectedReleasePath} must be added with this release`);
}
const packageChange = changeLevel(catalog.package.version, baseCatalog.package.version);
if (packageChange && release.package?.change !== packageChange) {
  errors.push(`release package.change must be ${packageChange} for ${baseCatalog.package.version} -> ${catalog.package.version}`);
}
for (const name of changedSkills) {
  const current = currentSkills.get(name);
  const prior = priorSkills.get(name);
  if (!current) continue;
  if (prior && !isGreater(current.version, prior.version)) {
    errors.push(`${name} version must increase from ${prior.version}`);
  }
  const releaseEntry = release.skills?.find((skill) => skill.name === name);
  if (!releaseEntry || releaseEntry.version !== current.version) {
    errors.push(`${name} must appear in the v${catalog.package.version} release record`);
    continue;
  }
  const expectedChange = prior ? changeLevel(current.version, prior.version) : 'initial';
  if (expectedChange && releaseEntry.change !== expectedChange) {
    errors.push(`${name} release change must be ${expectedChange} for ${prior?.version ?? '<new>'} -> ${current.version}`);
  }
}
for (const releaseEntry of release.skills ?? []) {
  if (!changedSkills.has(releaseEntry.name)) {
    errors.push(`${releaseEntry.name} appears in the release record without a skill version change`);
  }
}

if (errors.length) {
  console.error(`Release diff validation failed:\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(`Release diff is versioned as v${catalog.package.version}.`);

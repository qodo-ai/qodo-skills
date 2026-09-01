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

function gitRaw(...args) {
  return execFileSync('git', args, { encoding: 'utf8' });
}

function nameStatusRecords(raw) {
  const tokens = raw.split('\0');
  if (tokens.at(-1) === '') tokens.pop();
  const records = [];
  for (let index = 0; index < tokens.length;) {
    const status = tokens[index++];
    const sourcePath = /^[RC]/.test(status) ? tokens[index++] : undefined;
    const path = tokens[index++];
    if (!path) throw new Error(`Malformed NUL-delimited git status record: ${status}`);
    records.push({ status, path, sourcePath });
  }
  return records;
}

function parsedVersion(version) {
  const match = version?.match(/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/);
  return match ? { core: match.slice(1, 4), prerelease: match[4]?.split('.') ?? [] } : null;
}

function compareNumericIdentifiers(left, right) {
  if (left.length !== right.length) return left.length > right.length ? 1 : -1;
  if (left === right) return 0;
  return left > right ? 1 : -1;
}

function compareVersions(current, prior) {
  const left = parsedVersion(current);
  const right = parsedVersion(prior);
  if (!left || !right) return null;
  for (let index = 0; index < left.core.length; index += 1) {
    const precedence = compareNumericIdentifiers(left.core[index], right.core[index]);
    if (precedence) return precedence;
  }
  if (!left.prerelease.length || !right.prerelease.length) {
    return left.prerelease.length === right.prerelease.length ? 0 : left.prerelease.length ? -1 : 1;
  }
  for (let index = 0; index < Math.max(left.prerelease.length, right.prerelease.length); index += 1) {
    const leftPart = left.prerelease[index];
    const rightPart = right.prerelease[index];
    if (leftPart === undefined || rightPart === undefined) return leftPart === undefined ? -1 : 1;
    if (leftPart === rightPart) continue;
    const leftNumeric = /^\d+$/.test(leftPart);
    const rightNumeric = /^\d+$/.test(rightPart);
    if (leftNumeric && rightNumeric) return compareNumericIdentifiers(leftPart, rightPart);
    if (leftNumeric !== rightNumeric) return leftNumeric ? -1 : 1;
    return leftPart > rightPart ? 1 : -1;
  }
  return 0;
}

function isGreater(current, prior) {
  return compareVersions(current, prior) === 1;
}

function changeLevel(current, prior) {
  const left = parsedVersion(current)?.core;
  const right = parsedVersion(prior)?.core;
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
const files = gitRaw('diff', '--name-only', '-z', `${base}...HEAD`).split('\0').filter(Boolean);
const statuses = nameStatusRecords(gitRaw('diff', '--name-status', '-z', `${base}...HEAD`));
const changedSkills = new Set(
  files.flatMap((path) => {
    const match = path.match(/^skills\/([^/]+)\/(.+)$/);
    return match ? match[1] : [];
  }),
);
const currentSkills = new Map((catalog.skills ?? []).map((skill) => [skill.name, skill]));
const priorSkills = new Map((baseCatalog.skills ?? []).map((skill) => [skill.name, skill]));
const publishedSkillMetadata = (skill) => JSON.stringify({
  recommended: skill?.recommended,
  displayName: skill?.displayName,
  shortDescription: skill?.shortDescription,
  defaultPrompt: skill?.defaultPrompt,
});
for (const [name, current] of currentSkills) {
  const prior = priorSkills.get(name);
  if (
    !prior
    || current.version !== prior.version
    || publishedSkillMetadata(current) !== publishedSkillMetadata(prior)
  ) changedSkills.add(name);
}
const catalogChanged = files.includes('distribution/catalog.json');
const changedReleaseRecords = statuses.flatMap(({ status, path, sourcePath }) =>
  [sourcePath, path].filter((candidate) => candidate?.startsWith('releases/'))
    .map((candidate) => [status, candidate]));
const versionedPackagePaths = [
  /^\.github\/workflows\/(?:release|ship-marketplaces)\.yml$/,
  /^\.agents\/plugins\//,
  /^\.claude-plugin\//,
  /^codex-packages\//,
  /^kiro-power(?:-standards)?\//,
  /^packages\//,
  /^distribution\/(?:(?:catalog|codex-submissions|marketplaces)\.schema|codex-submissions|marketplaces)\.json$/,
  /^scripts\/(?:build-cli-managed-bundle|build-enterprise-bundle|build-release-index|marketplace-release(?:-lock)?|prepare-release|release-notes|skill-provenance|sync-adapters|validate-diff)\.mjs$/,
  /^scripts\/(?:publish-release|verify-kiro-release-source|verify-release-prerequisites)\.(?:cmd|sh)$/,
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
const releaseSkills = Array.isArray(release.skills) ? release.skills : [];
if (!Array.isArray(release.skills)) errors.push(`${expectedReleasePath}: skills must be an array`);
for (const [status, path] of changedReleaseRecords) {
  if (status !== 'A' || path !== expectedReleasePath) {
    errors.push(`release records are immutable; only add ${expectedReleasePath}`);
  }
}
if (!statuses.some(({ status, path }) => status === 'A' && path === expectedReleasePath)) {
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
  const releaseEntry = releaseSkills.find((skill) => skill.name === name);
  if (!releaseEntry || releaseEntry.version !== current.version) {
    errors.push(`${name} must appear in the v${catalog.package.version} release record`);
    continue;
  }
  const expectedChange = prior ? changeLevel(current.version, prior.version) : 'initial';
  if (expectedChange && releaseEntry.change !== expectedChange) {
    errors.push(`${name} release change must be ${expectedChange} for ${prior?.version ?? '<new>'} -> ${current.version}`);
  }
}
for (const releaseEntry of releaseSkills) {
  if (!changedSkills.has(releaseEntry.name)) {
    errors.push(`${releaseEntry.name} appears in the release record without a skill version change`);
  }
}

if (errors.length) {
  console.error(`Release diff validation failed:\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(`Release diff is versioned as v${catalog.package.version}.`);

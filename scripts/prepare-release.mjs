/** Prepare one atomic Qodo skills release in the current pull request. */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const bumps = new Map([['patch', 0], ['minor', 1], ['major', 2]]);

export function incrementVersion(version, bump) {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)$/);
  if (!match) throw new Error(`Cannot bump non-stable semantic version: ${version}`);
  const parts = match.slice(1).map(Number);
  if (bump === 'major') return `${parts[0] + 1}.0.0`;
  if (bump === 'minor') return `${parts[0]}.${parts[1] + 1}.0`;
  if (bump === 'patch') return `${parts[0]}.${parts[1]}.${parts[2] + 1}`;
  throw new Error(`Unsupported bump: ${bump}`);
}

function strongerBump(left, right) {
  if (!bumps.has(left) || !bumps.has(right)) throw new Error('Bumps must be patch, minor, or major');
  return bumps.get(left) >= bumps.get(right) ? left : right;
}

function parseArguments(argv) {
  const options = { skills: new Map() };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!['--summary', '--skill', '--package'].includes(flag) || !value) {
      throw new Error(`Unknown or incomplete argument: ${flag}`);
    }
    index += 1;
    if (flag === '--summary') options.summary = value.trim();
    if (flag === '--package') options.packageBump = value;
    if (flag === '--skill') {
      const match = value.match(/^([a-z][a-z0-9-]*)=(initial|patch|minor|major)$/);
      if (!match) throw new Error(`Invalid --skill value: ${value}; use name=initial|patch|minor|major`);
      const prior = options.skills.get(match[1]);
      if (prior && (prior === 'initial' || match[2] === 'initial') && prior !== match[2]) {
        throw new Error(`Cannot combine initial and version bumps for ${match[1]}`);
      }
      options.skills.set(
        match[1],
        prior && prior !== 'initial' ? strongerBump(prior, match[2]) : match[2],
      );
    }
  }
  if (!options.summary) throw new Error('--summary is required');
  if (!options.skills.size && !options.packageBump) {
    throw new Error('Provide at least one --skill or a --package bump');
  }
  if (options.packageBump && !bumps.has(options.packageBump)) {
    throw new Error('--package must be patch, minor, or major');
  }
  return options;
}

function updateFrontmatterVersion(path, version) {
  const original = readFileSync(path, 'utf8');
  const newline = original.includes('\r\n') ? '\r\n' : '\n';
  const text = original.replace(/\r\n/g, '\n');
  const end = text.indexOf('\n---', 4);
  if (!text.startsWith('---\n') || end < 0) throw new Error(`${path}: invalid frontmatter`);
  const frontmatter = text.slice(0, end);
  const matches = frontmatter.match(/^  version:\s*.+$/gm) ?? [];
  if (matches.length !== 1) throw new Error(`${path}: expected one metadata version`);
  const updated = `${frontmatter.replace(/^  version:\s*.+$/m, `  version: "${version}"`)}${text.slice(end)}`;
  return newline === '\n' ? updated : updated.replace(/\n/g, newline);
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

export function prepareRelease(argv, repositoryRoot = root) {
  const options = parseArguments(argv);
  const catalogPath = join(repositoryRoot, 'distribution', 'catalog.json');
  const packagePath = join(repositoryRoot, 'package.json');
  const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
  let packageBump = options.packageBump ?? 'patch';
  for (const bump of options.skills.values()) {
    packageBump = strongerBump(packageBump, bump === 'initial' ? 'minor' : bump);
  }

  const nextPackageVersion = incrementVersion(catalog.package.version, packageBump);
  const releasePath = join(repositoryRoot, 'releases', `v${nextPackageVersion}.json`);
  if (existsSync(releasePath)) throw new Error(`Release v${nextPackageVersion} already exists`);

  const knownSkills = new Set(catalog.skills.map((skill) => skill.name));
  const unknownSkills = [...options.skills.keys()].filter((name) => !knownSkills.has(name));
  if (unknownSkills.length) throw new Error(`Unknown skills: ${unknownSkills.join(', ')}`);

  const changes = [];
  for (const skill of catalog.skills) {
    const bump = options.skills.get(skill.name);
    if (!bump) continue;
    const version = bump === 'initial' ? skill.version : incrementVersion(skill.version, bump);
    const skillPath = join(repositoryRoot, 'skills', skill.name, 'SKILL.md');
    skill.version = version;
    changes.push({ name: skill.name, version, change: bump });
    writeFileSync(skillPath, updateFrontmatterVersion(skillPath, version));
  }

  catalog.package.version = nextPackageVersion;
  packageJson.version = nextPackageVersion;
  writeJson(catalogPath, catalog);
  writeJson(packagePath, packageJson);
  writeJson(releasePath, {
    version: nextPackageVersion,
    summary: options.summary,
    package: { change: packageBump },
    runtimeProtocolVersion: catalog.runtime.protocolVersion,
    skills: changes,
  });

  execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'sync-adapters.mjs')], {
    cwd: repositoryRoot,
    stdio: 'inherit',
  });
  return { version: nextPackageVersion, changes };
}

if (realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const release = prepareRelease(process.argv.slice(2));
    console.log(`Prepared Qodo skills v${release.version} with ${release.changes.length} skill change(s).`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

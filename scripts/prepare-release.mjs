/** Prepare one atomic Qodo skills release in the current pull request. */
import { execFileSync } from 'node:child_process';
import {
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
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
  const body = text.slice(end).replace(
    /--skill-version\s+\S+(?=\s+--distribution)/g,
    `--skill-version ${version}`,
  );
  const updated = `${frontmatter.replace(/^  version:\s*.+$/m, `  version: "${version}"`)}${body}`;
  return newline === '\n' ? updated : updated.replace(/\n/g, newline);
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

const releaseMutationPaths = [
  '.agents/plugins',
  '.claude-plugin',
  '.codex-plugin',
  'codex-packages',
  'distribution',
  'gemini-extension.json',
  'kiro-power',
  'kiro-power-standards',
  'package-lock.json',
  'package.json',
  'packages',
  'plugin.json',
  'releases',
  'skills',
];

function assertNoSymlinks(path, relativePath) {
  let stat;
  try {
    stat = lstatSync(path);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  if (stat.isSymbolicLink()) {
    throw new Error(`Release mutation path must not be a symlink: ${relativePath}`);
  }
  if (!stat.isDirectory()) return;
  for (const entry of readdirSync(path)) {
    assertNoSymlinks(join(path, entry), join(relativePath, entry));
  }
}

export function releaseTransaction(repositoryRoot, options = {}) {
  const copy = options.copy ?? cpSync;
  const remove = options.remove ?? rmSync;
  for (const relativePath of releaseMutationPaths) {
    assertNoSymlinks(join(repositoryRoot, relativePath), relativePath);
  }
  const backupRoot = mkdtempSync(join(options.backupParent ?? tmpdir(), 'qodo-skills-release-transaction-'));
  let states;
  try {
    states = releaseMutationPaths.map((relativePath, index) => {
      const source = join(repositoryRoot, relativePath);
      const backup = join(backupRoot, String(index));
      let existed = false;
      try {
        lstatSync(source);
        existed = true;
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      if (existed) {
        mkdirSync(dirname(backup), { recursive: true });
        copy(source, backup, { recursive: true, verbatimSymlinks: true });
      }
      return { relativePath, backup, existed };
    });
  } catch (error) {
    try {
      remove(backupRoot, { recursive: true, force: true });
    } catch (cleanupError) {
      throw new AggregateError(
        [error, cleanupError],
        `Release snapshot failed and its partial backup remains at ${backupRoot}: ${cleanupError.message}`,
      );
    }
    throw error;
  }
  return {
    backupRoot,
    rollback() {
      for (const { relativePath, backup, existed } of states) {
        const target = join(repositoryRoot, relativePath);
        remove(target, { recursive: true, force: true });
        if (existed) {
          mkdirSync(dirname(target), { recursive: true });
          copy(backup, target, { recursive: true, verbatimSymlinks: true });
        }
      }
    },
    close() {
      remove(backupRoot, { recursive: true, force: true });
    },
  };
}

export function executeReleaseTransaction(repositoryRoot, operation, options) {
  const transaction = releaseTransaction(repositoryRoot, options);
  let result;
  try {
    result = operation();
  } catch (error) {
    try {
      transaction.rollback();
    } catch (rollbackError) {
      throw new AggregateError(
        [error, rollbackError],
        `Release preparation failed and rollback was incomplete; recovery backup retained at ${transaction.backupRoot}: ${rollbackError.message}`,
      );
    }
    try {
      transaction.close();
    } catch (cleanupError) {
      throw new AggregateError(
        [error, cleanupError],
        `Release preparation failed; repository state was restored but backup cleanup failed at ${transaction.backupRoot}: ${cleanupError.message}`,
      );
    }
    throw error;
  }
  try {
    transaction.close();
  } catch (cleanupError) {
    throw new Error(
      `Release preparation succeeded but backup cleanup failed at ${transaction.backupRoot}: ${cleanupError.message}`,
      { cause: cleanupError },
    );
  }
  return result;
}

export function prepareRelease(argv, repositoryRoot = root) {
  const options = parseArguments(argv);
  const catalogPath = join(repositoryRoot, 'distribution', 'catalog.json');
  const packagePath = join(repositoryRoot, 'package.json');
  const lockPath = join(repositoryRoot, 'package-lock.json');
  const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
  const packageLock = existsSync(lockPath) ? JSON.parse(readFileSync(lockPath, 'utf8')) : undefined;
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
  let headCatalog = { skills: [] };
  let hasHead = false;
  try {
    execFileSync('git', ['rev-parse', '--verify', 'HEAD'], {
      cwd: repositoryRoot,
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    hasHead = true;
  } catch (error) {
    if (error.code === 'ENOENT') throw error;
  }
  if (hasHead) {
    let hasHeadCatalog = false;
    try {
      execFileSync('git', ['cat-file', '-e', 'HEAD:distribution/catalog.json'], {
        cwd: repositoryRoot,
        stdio: ['ignore', 'ignore', 'pipe'],
      });
      hasHeadCatalog = true;
    } catch (error) {
      if (error.code === 'ENOENT') throw error;
    }
    if (hasHeadCatalog) {
      const headCatalogText = execFileSync(
        'git',
        ['show', 'HEAD:distribution/catalog.json'],
        { cwd: repositoryRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
      );
      try {
        headCatalog = JSON.parse(headCatalogText);
      } catch (error) {
        throw new Error(`HEAD distribution/catalog.json is invalid: ${error.message}`);
      }
    }
  }
  const headSkills = new Set((headCatalog.skills ?? []).map((skill) => skill.name));
  for (const [name, bump] of options.skills) {
    if (bump === 'initial' && headSkills.has(name)) {
      throw new Error(`${name}=initial is only valid for a skill absent from the HEAD catalog`);
    }
  }

  return executeReleaseTransaction(repositoryRoot, () => {
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
    if (packageLock) {
      packageLock.version = nextPackageVersion;
      if (packageLock.packages?.['']) packageLock.packages[''].version = nextPackageVersion;
    }
    writeJson(catalogPath, catalog);
    writeJson(packagePath, packageJson);
    if (packageLock) writeJson(lockPath, packageLock);
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
    execFileSync(process.execPath, [join(repositoryRoot, 'scripts', 'build-release-index.mjs')], {
      cwd: repositoryRoot,
      stdio: 'inherit',
    });
    return { version: nextPackageVersion, changes };
  });
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

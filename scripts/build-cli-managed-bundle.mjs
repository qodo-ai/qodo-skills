/** Build the deterministic data-only bundle used by the CLI-managed compatibility channel. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  lstatSync,
  readFileSync,
  readdirSync,
  realpathSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const BUNDLE_NAME = 'qodo-cli-managed-bundle.json';
const DISTRIBUTION = 'qodo-cli-managed';
const MAX_FILE_BYTES = 512 * 1024;
const PRIVATE_KEY_PEM = /-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY(?: BLOCK)?-----/;

function sha256(payload) {
  return createHash('sha256').update(payload).digest('hex');
}

function bytewise(left, right) {
  return Buffer.compare(Buffer.from(left), Buffer.from(right));
}

function normalizedPath(path) {
  return path.split(sep).join('/');
}

export function assertSafeRelativePath(path) {
  if (
    !path || path.startsWith('/') || path.includes('\\')
    || path.split('/').some((part) => !part || part === '.' || part === '..')
  ) throw new Error(`Unsafe CLI-managed bundle path: ${path}`);
}

function cliManagedSkillMarkdown(text, sourcePath) {
  const metadata = /^  distribution: "(?:skills-sh|marketplace|kiro-power)"$/m;
  const calls = /--distribution (?:skills-sh|marketplace|kiro-power)(?=$|[^A-Za-z0-9_-])/g;
  if (!metadata.test(text) || !calls.test(text)) {
    throw new Error(`${sourcePath}: skill has no recognized distribution provenance`);
  }
  calls.lastIndex = 0;
  return text
    .replace(metadata, `  distribution: "${DISTRIBUTION}"`)
    .replace(calls, `--distribution ${DISTRIBUTION}`);
}

function collectFiles(repositoryRoot, skillName) {
  const sourceRoot = join(repositoryRoot, 'skills', skillName);
  const files = [];
  const walk = (directory, prefix = '') => {
    for (const entry of readdirSync(directory, { withFileTypes: true })
      .sort((left, right) => bytewise(left.name, right.name))) {
      if (entry.name === '.DS_Store') continue;
      const source = join(directory, entry.name);
      const path = prefix ? `${prefix}/${entry.name}` : entry.name;
      assertSafeRelativePath(path);
      const state = lstatSync(source);
      if (state.isSymbolicLink()) throw new Error(`${source}: CLI-managed bundles do not permit symlinks`);
      if (state.isDirectory()) walk(source, path);
      else if (state.isFile()) {
        let content = readFileSync(source);
        if (content.length > MAX_FILE_BYTES) throw new Error(`${source}: exceeds ${MAX_FILE_BYTES} bytes`);
        if (PRIVATE_KEY_PEM.test(content.toString())) throw new Error(`${source}: private keys are forbidden`);
        if (path === 'SKILL.md') {
          content = Buffer.from(cliManagedSkillMarkdown(
            content.toString('utf8'),
            normalizedPath(relative(repositoryRoot, source)),
          ));
        }
        files.push({
          path,
          sha256: sha256(content),
          encoding: 'base64',
          content: content.toString('base64'),
        });
      } else throw new Error(`${source}: CLI-managed bundles permit regular files only`);
    }
  };
  walk(sourceRoot);
  if (!files.some((file) => file.path === 'SKILL.md')) {
    throw new Error(`${skillName}: SKILL.md is required`);
  }
  return files;
}

export function buildCliManagedBundle(repositoryRoot = root) {
  const catalog = JSON.parse(readFileSync(join(repositoryRoot, 'distribution', 'catalog.json'), 'utf8'));
  const packageBySkill = new Map();
  for (const installPackage of catalog.installPackages) {
    for (const skill of installPackage.skills) {
      if (packageBySkill.has(skill)) throw new Error(`${skill}: belongs to multiple packages`);
      packageBySkill.set(skill, installPackage.name);
    }
  }
  const skills = Object.fromEntries([...catalog.skills]
    .sort((left, right) => bytewise(left.name, right.name))
    .map((skill) => {
      const packageName = packageBySkill.get(skill.name);
      if (!packageName) throw new Error(`${skill.name}: missing install package`);
      return [skill.name, {
        version: skill.version,
        package: packageName,
        recommended: skill.recommended,
        files: collectFiles(repositoryRoot, skill.name),
      }];
    }));
  const bundle = {
    schemaVersion: 1,
    distribution: DISTRIBUTION,
    instructionMode: catalog.instructionMode,
    packageVersion: catalog.package.version,
    minimumCliVersion: catalog.runtime.minimumCliVersion,
    source: {
      repository: catalog.package.repository,
      tag: `v${catalog.package.version}`,
    },
    aliases: Object.fromEntries(
      catalog.installPackages.flatMap((installPackage) => Object.entries(installPackage.compatibilityAliases)),
    ),
    skills,
  };
  const output = `${JSON.stringify(bundle, null, 2)}\n`;
  const checksum = `${sha256(output)}  ${BUNDLE_NAME}\n`;
  return { output, checksum, bundle };
}

export function writeCliManagedBundle({ check = false } = {}, repositoryRoot = root) {
  const { output, checksum, bundle } = buildCliManagedBundle(repositoryRoot);
  const bundlePath = join(repositoryRoot, 'distribution', BUNDLE_NAME);
  const checksumPath = `${bundlePath}.sha256`;
  if (check) {
    assert.equal(readFileSync(bundlePath, 'utf8').replace(/\r\n/g, '\n'), output,
      'CLI-managed bundle is stale; run npm run cli-managed:build');
    assert.equal(readFileSync(checksumPath, 'utf8').replace(/\r\n/g, '\n'), checksum,
      'CLI-managed bundle checksum is stale; run npm run cli-managed:build');
  } else {
    writeFileSync(bundlePath, output);
    writeFileSync(checksumPath, checksum);
  }
  return bundle;
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const bundle = writeCliManagedBundle({ check: process.argv.includes('--check') });
  console.log(`${process.argv.includes('--check') ? 'Verified' : 'Built'} CLI-managed bundle ${bundle.packageVersion}.`);
}

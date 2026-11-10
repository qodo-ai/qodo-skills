import { parseSkillFrontmatter } from './skill-frontmatter.mjs';
/** Data-only opt-in skill catalog; independent of legacy bundles and provider projections. */
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { resourcePathKeys, windowsResourceKey } from './resource-path-keys.mjs';
import { createHash } from 'node:crypto';
import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
export const REPOSITORY_CATALOG_NAME = 'qodo-repository-catalog.json';
const MAX_FILE_BYTES = 512 * 1024;
const MAX_CONTENT_BYTES = 40 * 1024 * 1024;
const MAX_FILES = 4096;
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const schema = JSON.parse(readFileSync(join(root, 'distribution/catalog.schema.json'), 'utf8'));
const ajv = new Ajv2020({ allErrors: true }); addFormats(ajv);
const validateCatalog = ajv.compile(schema);
const semver = new RegExp(`(?:${schema.properties.package.properties.version.pattern})(?![\\s\\S])`);
const bytewise = (a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b));

function catalogMinimumCliVersion(runtimeMinimum) {
  if (!semver.test(runtimeMinimum)) throw new Error('Invalid catalog minimum CLI version');
  const source = runtimeMinimum.split('+')[0].split('-')[0].split('.').map(Number);
  const floor = [2, 3, 0];
  for (let i = 0; i < floor.length; i++) {
    if (source[i] > floor[i]) return runtimeMinimum;
    if (source[i] < floor[i]) return '2.3.0';
  }
  return '2.3.0';
}

export function buildRepositoryCatalog(repositoryRoot, sourceCommit) {
  if (!/^[a-f0-9]{40}$/.test(sourceCommit)) throw new Error('Repository catalog requires an immutable source commit');
  const metadata = readFileSync(join(repositoryRoot, 'distribution/catalog.json'));
  if (metadata.length > 1024 * 1024) throw new Error('Repository catalog metadata exceeds its budget');
  const catalog = JSON.parse(metadata.toString('utf8'));
  if (!validateCatalog(catalog) || !semver.test(catalog.package.version) || catalog.skills.length > 500 || catalog.installPackages.length > 100 || catalog.package.repository !== 'https://github.com/qodo-ai/qodo-skills') throw new Error('Invalid canonical repository catalog metadata');
  const packageBySkill = new Map();
  const packageNames = new Set();
  const aliases = new Set();
  for (const pkg of catalog.installPackages) {
    if (packageNames.has(pkg.name)) throw new Error('Duplicate repository package name');
    packageNames.add(pkg.name);
    for (const [alias, target] of Object.entries(pkg.compatibilityAliases)) {
      if (aliases.has(alias) || !pkg.skills.includes(target)) throw new Error('Invalid repository compatibility alias');
      aliases.add(alias);
    }
    for (const name of pkg.skills) {
    if (!/^qodo(?:-[a-z0-9-]+)?$/.test(pkg.name) || packageBySkill.has(name)) throw new Error('Invalid repository package membership');
    packageBySkill.set(name, pkg.name);
    }
  }
  const registered = new Set(catalog.skills.map((skill) => skill.name));
  for (const entry of readdirSync(join(repositoryRoot, 'skills'), { withFileTypes: true })) {
    if ((entry.isDirectory() || entry.isSymbolicLink()) && !registered.has(entry.name)) throw new Error('Uncatalogued repository skill directory');
  }
  let contentBytes = 0;
  let fileCount = 0;
  const names = new Set();
  const skills = [...catalog.skills].sort((a, b) => bytewise(a.name, b.name)).map((skill) => {
    if (!semver.test(skill.version)) throw new Error('Invalid repository skill version');
    if (!/^qodo-[a-z0-9-]+$/.test(skill.name) || names.has(skill.name) || !packageBySkill.has(skill.name)) throw new Error('Invalid repository skill identity');
    names.add(skill.name);
    const files = [];
    const walk = (directory, prefix = '', depth = 0) => {
      if (depth > 64 || lstatSync(directory).isSymbolicLink()) throw new Error('Unsafe repository skill directory');
      const portableNames = new Set();
      for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => bytewise(a.name, b.name))) {
        if (resourcePathKeys(entry.name).some((key) => portableNames.has(key))) throw new Error('Case-colliding repository skill resource');
        resourcePathKeys(entry.name).forEach((key) => portableNames.add(key));
        if (entry.name === '.DS_Store') continue;
        if (/[\uD800-\uDFFF]/u.test(entry.name)) throw new Error('Unsafe repository skill resource path: invalid Unicode');
        if (!entry.name || /[\\\u0000-\u001f:<>"|?*]/.test(entry.name) || ['.', '..', '.GIT', 'NODE_MODULES'].includes(windowsResourceKey(entry.name)) || /^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?$/.test(windowsResourceKey(entry.name)) || /[. ]$/.test(entry.name)) throw new Error('Unsafe repository skill resource path');
        const source = join(directory, entry.name);
        const path = prefix ? `${prefix}/${entry.name}` : entry.name;
        const info = lstatSync(source);
        if (info.isSymbolicLink()) throw new Error('Repository catalog forbids symlinks');
        if (info.isDirectory()) walk(source, path, depth + 1);
        else if (info.isFile()) {
          if (info.size > MAX_FILE_BYTES || ++fileCount > MAX_FILES) throw new Error('Repository skill resource exceeds its budget');
          const content = readFileSync(source); contentBytes += content.length;
          if (contentBytes > MAX_CONTENT_BYTES || /-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY(?: BLOCK)?-----/.test(content.toString())) throw new Error('Repository skill payload exceeds its budget or contains a private key');
          files.push({ path, sha256: digest(content), encoding: 'base64', executable: Boolean(info.mode & 0o111), content: content.toString('base64') });
        } else throw new Error('Repository catalog permits regular files only');
      }
    };
    walk(join(repositoryRoot, 'skills', skill.name));
    if (!files.some((file) => file.path === 'SKILL.md')) throw new Error('Repository skill has no SKILL.md');
    const meta = parseSkillFrontmatter(Buffer.from(files.find((file) => file.path === 'SKILL.md').content, 'base64').toString('utf8'));
    const recommended = meta?.metadata.recommended === undefined ? true : meta.metadata.recommended === 'true';
    if (!meta || !meta.description?.trim() || meta.owner !== 'Qodo' || meta.metadata.vendor !== 'qodo' || meta.metadata.distribution !== 'skills-sh'
      || (meta.metadata.recommended !== undefined && !['true', 'false'].includes(meta.metadata.recommended)) || meta.name !== skill.name || meta.metadata.version !== skill.version
      || recommended !== skill.recommended || meta.metadata.package !== packageBySkill.get(skill.name)) {
      throw new Error(`Repository skill frontmatter differs from catalog: ${skill.name}`);
    }
    return { ...skill, package: packageBySkill.get(skill.name), files };
  });
  if (packageBySkill.size !== skills.length) throw new Error('Repository package contains an undeclared skill');
  return { schemaVersion: 1, distribution: 'qodo-repository', repository: catalog.package.repository,
    sourceCommit, packageVersion: catalog.package.version, minimumCliVersion: catalogMinimumCliVersion(catalog.runtime.minimumCliVersion),
    installPackages: catalog.installPackages, skills };
}

export function writeRepositoryCatalog(repositoryRoot, sourceCommit, outputDirectory) {
  const payload = Buffer.from(`${JSON.stringify(buildRepositoryCatalog(repositoryRoot, sourceCommit), null, 2)}\n`);
  if (payload.length > 64 * 1024 * 1024) throw new Error('Repository catalog exceeds its encoded budget');
  mkdirSync(outputDirectory, { recursive: true });
  writeFileSync(join(outputDirectory, REPOSITORY_CATALOG_NAME), payload);
  writeFileSync(join(outputDirectory, `${REPOSITORY_CATALOG_NAME}.sha256`), `${digest(payload)}  ${REPOSITORY_CATALOG_NAME}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const value = (flag) => { const index = process.argv.indexOf(flag); if (index < 0 || !process.argv[index + 1] || process.argv[index + 1].startsWith('--')) throw new Error(`${flag} requires a value`); return process.argv[index + 1]; };
  writeRepositoryCatalog(root, value('--source-commit'), resolve(value('--output-dir')));
}

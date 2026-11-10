/** Data-only opt-in skill catalog; independent of legacy bundles and provider projections. */
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
const bytewise = (a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b));

function catalogMinimumCliVersion(runtimeMinimum) {
  if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(runtimeMinimum)) throw new Error('Invalid catalog minimum CLI version');
  const source = runtimeMinimum.split('-')[0].split('.').map(Number);
  const floor = [2, 3, 0];
  for (let i = 0; i < floor.length; i++) {
    if (source[i] > floor[i]) return runtimeMinimum;
    if (source[i] < floor[i]) return '2.3.0';
  }
  return '2.3.0';
}

export function buildRepositoryCatalog(repositoryRoot, sourceCommit) {
  if (!/^[a-f0-9]{40}$/.test(sourceCommit)) throw new Error('Repository catalog requires an immutable source commit');
  const catalog = JSON.parse(readFileSync(join(repositoryRoot, 'distribution/catalog.json'), 'utf8'));
  const packageBySkill = new Map();
  for (const pkg of catalog.installPackages) for (const name of pkg.skills) {
    if (!/^qodo(?:-[a-z0-9]+)*$/.test(pkg.name) || packageBySkill.has(name)) throw new Error('Invalid repository package membership');
    packageBySkill.set(name, pkg.name);
  }
  let contentBytes = 0;
  let fileCount = 0;
  const names = new Set();
  const skills = [...catalog.skills].sort((a, b) => bytewise(a.name, b.name)).map((skill) => {
    if (!/^qodo-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(skill.name) || names.has(skill.name) || !packageBySkill.has(skill.name)) throw new Error('Invalid repository skill identity');
    names.add(skill.name);
    const files = [];
    const walk = (directory, prefix = '', depth = 0) => {
      if (depth > 64 || lstatSync(directory).isSymbolicLink()) throw new Error('Unsafe repository skill directory');
      for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => bytewise(a.name, b.name))) {
        if (entry.name === '.DS_Store') continue;
        if (!entry.name || /[\\\u0000-\u001f:<>"|?*]/.test(entry.name) || ['.', '..', '.git', 'node_modules'].includes(entry.name) || /[. ]$/.test(entry.name)) throw new Error('Unsafe repository skill resource path');
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

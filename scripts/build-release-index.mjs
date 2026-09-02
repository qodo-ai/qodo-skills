/** Build the compact, checksummed skill-version index consumed by the Qodo CLI. */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const check = process.argv.includes('--check');
function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0) return undefined;
  const value = process.argv[index + 1];
  if (!value || value.startsWith('--')) throw new Error(`${name} requires a value`);
  return value;
}
const sourceCommit = argument('--source-commit');
if (sourceCommit && !/^[a-f0-9]{40}$/.test(sourceCommit)) {
  throw new Error('--source-commit must be a full lowercase commit SHA');
}
const outputDirectory = resolve(argument('--output-dir') ?? join(root, 'distribution'));
if (check && (sourceCommit || argument('--output-dir'))) {
  throw new Error('--check cannot be combined with release output options');
}
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const indexPath = join(outputDirectory, 'qodo-skills-index.json');
const checksumPath = `${indexPath}.sha256`;

const packageBySkill = new Map();
for (const installPackage of catalog.installPackages) {
  for (const skillName of installPackage.skills) packageBySkill.set(skillName, installPackage.name);
}

const skills = Object.fromEntries(catalog.skills.map((skill) => {
  const packageName = packageBySkill.get(skill.name);
  if (!packageName) throw new Error(`${skill.name}: missing install package`);
  return [skill.name, { version: skill.version, package: packageName }];
}));
const index = {
  schemaVersion: sourceCommit ? 2 : 1,
  instructionMode: catalog.instructionMode,
  packageVersion: catalog.package.version,
  minimumCliVersion: catalog.runtime.minimumCliVersion,
  repository: catalog.package.repository,
  ...(sourceCommit ? { sourceCommit } : {}),
  skills,
};
const output = `${JSON.stringify(index, null, 2)}\n`;
const digest = createHash('sha256').update(output).digest('hex');
const checksum = `${digest}  qodo-skills-index.json\n`;

if (check) {
  if (
    readFileSync(indexPath, 'utf8').replace(/\r\n/g, '\n') !== output ||
    readFileSync(checksumPath, 'utf8').replace(/\r\n/g, '\n') !== checksum
  ) throw new Error('Skill release index is stale; run npm run index:build');
} else {
  mkdirSync(outputDirectory, { recursive: true });
  writeFileSync(indexPath, output);
  writeFileSync(checksumPath, checksum);
}

console.log(`${check ? 'Verified' : 'Built'} skill release index ${catalog.package.version}.`);

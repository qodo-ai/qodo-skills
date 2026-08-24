/** Build the immutable direct-connect artifact for agents without a marketplace. */
import { createHash } from 'node:crypto';
import {
  lstatSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { stampSkillProvenance } from './skill-provenance.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const check = process.argv.includes('--check');
const bundlePath = join(root, 'distribution', 'qodo-skills-direct.json');
const checksumPath = `${bundlePath}.sha256`;
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function walk(directory) {
  const files = [];
  for (const name of readdirSync(directory).sort()) {
    const path = join(directory, name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) throw new Error(`Direct bundles may not contain symlinks: ${path}`);
    if (stat.isDirectory()) files.push(...walk(path));
    else if (stat.isFile()) files.push(path);
  }
  return files;
}

const contentDigest = createHash('sha256');
const packages = catalog.installPackages.map((entry) => {
  contentDigest
    .update('package').update('\0')
    .update(entry.name).update('\0')
    .update(entry.default ? 'default' : 'optional').update('\0');
  for (const skillName of entry.skills) contentDigest.update(skillName).update('\0');
  return {
    name: entry.name,
    displayName: entry.displayName,
    description: entry.description,
    default: entry.default,
    skills: entry.skills,
  };
});
const skills = catalog.skills.map((entry) => {
  const skillRoot = join(root, 'skills', entry.name);
  const packageName = catalog.installPackages.find((candidate) => candidate.skills.includes(entry.name))?.name;
  if (!packageName) throw new Error(`${entry.name}: missing install package`);
  const files = walk(skillRoot).map((path) => {
    const filePath = relative(skillRoot, path).split(sep).join('/');
    const source = readFileSync(path, 'utf8');
    const content = filePath === 'SKILL.md'
      ? stampSkillProvenance(source, {
        name: entry.name,
        version: entry.version,
        packageName,
        distribution: 'qodo-direct',
      })
      : source;
    const digest = sha256(content);
    contentDigest
      .update(entry.name).update('\0')
      .update(entry.version).update('\0')
      .update(filePath).update('\0')
      .update(digest).update('\0');
    return { path: filePath, sha256: digest, content };
  });
  return {
    name: entry.name,
    version: entry.version,
    recommended: entry.recommended,
    files,
  };
});

const bundle = {
  schemaVersion: 2,
  package: {
    name: catalog.package.name,
    version: catalog.package.version,
    repository: catalog.package.repository,
    contentSha256: contentDigest.digest('hex'),
  },
  packages,
  skills,
};
const output = `${JSON.stringify(bundle, null, 2)}\n`;
const checksum = `${sha256(output)}  qodo-skills-direct.json\n`;

if (check) {
  const current = readFileSync(bundlePath, 'utf8').replace(/\r\n/g, '\n');
  const currentChecksum = readFileSync(checksumPath, 'utf8').replace(/\r\n/g, '\n');
  if (current !== output || currentChecksum !== checksum) {
    throw new Error('Direct-connect distribution artifacts are stale; run npm run direct:build');
  }
} else {
  writeFileSync(bundlePath, output);
  writeFileSync(checksumPath, checksum);
}

console.log(
  `${check ? 'Verified' : 'Built'} direct-connect bundle ${catalog.package.version} (${skills.length} skills).`,
);

/** Build the immutable, distribution-neutral playbook artifact consumed by the Qodo CLI. */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const check = process.argv.includes('--check');
const bundlePath = join(root, 'distribution', 'qodo-playbooks.json');
const checksumPath = `${bundlePath}.sha256`;
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function canonicalBody(skill) {
  const path = join(root, 'skills', skill.name, 'SKILL.md');
  const source = readFileSync(path, 'utf8').replace(/\r\n/g, '\n');
  const delimiter = '\n---\n';
  const end = source.indexOf(delimiter, 4);
  if (!source.startsWith('---\n') || end < 0) {
    throw new Error(`${skill.name}: invalid SKILL.md frontmatter`);
  }
  const frontmatter = source.slice(0, end);
  if (!new RegExp(`^name:\\s*${skill.name}$`, 'm').test(frontmatter)) {
    throw new Error(`${skill.name}: SKILL.md name does not match catalog`);
  }
  if (!new RegExp(`^  version:\\s*["']?${skill.version}["']?$`, 'm').test(frontmatter)) {
    throw new Error(`${skill.name}: SKILL.md version does not match catalog`);
  }
  const installPackage = catalog.installPackages.find((entry) => entry.skills.includes(skill.name));
  if (!installPackage) throw new Error(`${skill.name}: missing install package`);
  const body = source.slice(end + delimiter.length);
  if (!body.trim() || !/^#\s+/m.test(body)) throw new Error(`${skill.name}: empty playbook body`);
  return { body, packageName: installPackage.name };
}

const contentDigest = createHash('sha256');
for (const installPackage of catalog.installPackages) {
  contentDigest
    .update('package').update('\0')
    .update(installPackage.name).update('\0')
    .update(installPackage.default ? 'default' : 'optional').update('\0');
  for (const skillName of installPackage.skills) contentDigest.update(skillName).update('\0');
}

const workflows = catalog.skills.map((skill) => {
  const { body, packageName } = canonicalBody(skill);
  const contentSha256 = sha256(body);
  contentDigest
    .update(skill.name).update('\0')
    .update(skill.version).update('\0')
    .update(packageName).update('\0')
    .update(skill.recommended ? 'default' : 'optional').update('\0')
    .update(contentSha256).update('\0');
  return {
    name: skill.name,
    version: skill.version,
    package: packageName,
    recommended: skill.recommended,
    contentSha256,
    content: body,
  };
});

const bundle = {
  schemaVersion: 1,
  package: {
    name: catalog.package.name,
    version: catalog.package.version,
    repository: catalog.package.repository,
    contentSha256: contentDigest.digest('hex'),
  },
  packages: catalog.installPackages.map((entry) => ({
    name: entry.name,
    default: entry.default,
    skills: entry.skills,
  })),
  workflows,
};
const output = `${JSON.stringify(bundle, null, 2)}\n`;
const checksum = `${sha256(output)}  qodo-playbooks.json\n`;

if (check) {
  const current = readFileSync(bundlePath, 'utf8').replace(/\r\n/g, '\n');
  const currentChecksum = readFileSync(checksumPath, 'utf8').replace(/\r\n/g, '\n');
  if (current !== output || currentChecksum !== checksum) {
    throw new Error('Playbook distribution artifacts are stale; run npm run playbooks:build');
  }
} else {
  writeFileSync(bundlePath, output);
  writeFileSync(checksumPath, checksum);
}

console.log(
  `${check ? 'Verified' : 'Built'} CLI playbook bundle ${catalog.package.version} (${workflows.length} workflows).`,
);

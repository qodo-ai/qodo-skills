/** Export the canonical skills as qodo-in-cli's explicit offline fallback. */
import { createHash } from 'node:crypto';
import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const outputArg = process.argv[2];
if (!outputArg) {
  console.error('Usage: node scripts/export-cli-bundle.mjs <output.ts>');
  process.exit(2);
}
const output = isAbsolute(outputArg) ? outputArg : resolve(process.cwd(), outputArg);
const catalogText = readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8');
const catalog = JSON.parse(catalogText);

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir).sort()) {
    const path = join(dir, name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) throw new Error(`Refusing to bundle symlink: ${relative(root, path)}`);
    if (stat.isDirectory()) files.push(...walk(path));
    else if (stat.isFile()) files.push(path);
  }
  return files;
}

const digest = createHash('sha256');
digest.update(catalogText);
const skills = catalog.skills.map((entry) => {
  const skillRoot = join(root, 'skills', entry.name);
  const files = walk(skillRoot).map((path) => {
    const content = readFileSync(path, 'utf8');
    const name = relative(skillRoot, path).split(/[\\/]/).join('/');
    digest.update(entry.name).update('\0').update(name).update('\0').update(content).update('\0');
    return { path: name, content };
  });
  return { name: entry.name, recommended: entry.recommended, files };
});

const provenance = {
  repository: catalog.package.repository,
  packageVersion: catalog.package.version,
  contentSha256: digest.digest('hex'),
};
const generated = `// AUTO-GENERATED from qodo-ai/qodo-skills — do not edit.
// Source package: ${provenance.packageVersion}; content sha256: ${provenance.contentSha256}

export interface BundledSkillFile {
  readonly path: string;
  readonly content: string;
}
export interface BundledSkill {
  readonly name: string;
  /** Included in the legacy/offline fallback's default selection. */
  readonly recommended: boolean;
  readonly files: readonly BundledSkillFile[];
}
export const BUNDLED_SKILLS_SOURCE = ${JSON.stringify(provenance, null, 2)} as const;
export const BUNDLED_SKILLS: readonly BundledSkill[] = ${JSON.stringify(skills, null, 2)};
`;

mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, generated);
console.log(`Exported ${skills.length} skills from qodo-skills ${catalog.package.version} to ${output}.`);

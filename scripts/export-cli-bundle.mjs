/** Export the generated qodo-direct projection as qodo-in-cli's offline fallback. */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const outputArg = process.argv[2];
if (!outputArg) {
  console.error('Usage: node scripts/export-cli-bundle.mjs <output.ts>');
  process.exit(2);
}
const output = isAbsolute(outputArg) ? outputArg : resolve(process.cwd(), outputArg);
const bundle = JSON.parse(
  readFileSync(join(root, 'distribution', 'qodo-skills-direct.json'), 'utf8'),
);
const skills = bundle.skills.map((entry) => ({
  name: entry.name,
  recommended: entry.recommended,
  files: entry.files.map(({ path, content }) => ({ path, content })),
}));

const provenance = {
  repository: bundle.package.repository,
  packageVersion: bundle.package.version,
  contentSha256: bundle.package.contentSha256,
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
console.log(`Exported ${skills.length} qodo-direct skills from qodo-skills ${bundle.package.version} to ${output}.`);

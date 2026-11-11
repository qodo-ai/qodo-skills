/** Release provenance for optional, unlisted skill/package renames.
 * This records a name change; it does not migrate installed client receipts.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export function declaredSkillRenames(root) {
  const path = join(root, 'distribution/skill-renames.json');
  if (!existsSync(path)) return [];
  const record = JSON.parse(readFileSync(path, 'utf8'));
  if (record.schemaVersion !== 1 || !Array.isArray(record.renames)) throw new Error('Invalid skill rename record');
  const sources = new Set(), targets = new Set();
  for (const rename of record.renames) {
    if (!rename || ['from', 'to', 'fromPackage', 'toPackage'].some((key) =>
      typeof rename[key] !== 'string' || !/^qodo-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(rename[key]))
      || rename.from === rename.to || sources.has(rename.from) || targets.has(rename.to)) {
      throw new Error('Invalid or ambiguous skill rename record');
    }
    sources.add(rename.from); targets.add(rename.to);
  }
  return record.renames;
}

export function activeSkillRenames(root, prior, current) {
  const declared = declaredSkillRenames(root), before = new Map(prior.skills.map((s) => [s.name, s]));
  const after = new Map(current.skills.map((s) => [s.name, s]));
  const optional = (pkg) => pkg && pkg.default === false && pkg.managed === false && pkg.providerListed === false;
  return [...before.keys()].filter((name) => !after.has(name)).sort().map((name) => {
    const rename = declared.find((entry) => entry.from === name);
    if (!rename) throw new Error(`Skill removal: ${name} was removed without a supported immutable removal record`);
    const oldPackage = prior.installPackages.find((pkg) => pkg.skills.includes(name));
    const newPackage = current.installPackages.find((pkg) => pkg.skills.includes(rename.to));
    if (!after.has(rename.to) || before.has(rename.to) || !optional(oldPackage) || !optional(newPackage)
      || oldPackage.name !== rename.fromPackage || newPackage.name !== rename.toPackage) {
      throw new Error(`Skill rename must replace an optional, unlisted skill with a new identity: ${name}`);
    }
    return rename;
  });
}

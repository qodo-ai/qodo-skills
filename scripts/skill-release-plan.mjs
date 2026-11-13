/** Collect unreleased canonical changes without changing contributor branches. */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { prepareRelease } from './prepare-release.mjs';
import { activeSkillRenames } from './skill-renames.mjs';
import { git, catalogAt, releaseBaseline } from './release-baseline.mjs';
export { git, catalogAt, releaseBaseline } from './release-baseline.mjs';

export const readJson = (root, path) => JSON.parse(readFileSync(join(root, path), 'utf8'));

const generated = /^(?:\.agents\/plugins\/|\.claude-plugin\/|\.codex-plugin\/|antigravity-plugins\/|codex-packages\/|kiro-power(?:-[a-z0-9-]+)?\/|packages\/|plugin\.json$|gemini-extension\.json$|distribution\/qodo-(?:skills-index|cli-managed-bundle)\.json(?:\.sha256)?$|skills\/[^/]+\/agents\/openai\.yaml$)/;
const packaging = [
  /^\.github\/workflows\/ship-marketplaces\.yml$/,
  /^distribution\//,
  /^scripts\/(?:build-cli-managed-bundle|build-enterprise-bundle|build-release-index|build-repository-catalog|deterministic-zip|package-projections|marketplace-release(?:-lock)?|prepare-release|release-baseline|skill-renames|release-notes|skill-provenance|sync-adapters|verify-codex-packet)\.mjs$/,
  /^\.github\/workflows\/release\.yml$/,
  /^scripts\/(?:audit-release-protections|publish-release|verify-release-prerequisites)\.(?:cmd|sh)$/,
];

function assertSourceVersions(root, prior, catalog, renames) {
  if (catalog.package.version !== prior.package.version) throw new Error('Source changes must leave package versions to the release PR.');
  const manifest = readJson(root, 'package.json');
  const lock = readJson(root, 'package-lock.json');
  if ([manifest.version, lock.version, lock.packages?.['']?.version].some((v) => v !== prior.package.version)) {
    throw new Error('Source changes must leave package and lockfile versions to the release PR.');
  }
  const oldSkills = new Map(prior.skills.map((skill) => [skill.name, skill]));
  for (const skill of catalog.skills) {
    if (!/^qodo-[a-z0-9-]+$/.test(skill.name)) throw new Error('Invalid canonical skill name.');
    if (oldSkills.has(skill.name) && skill.version !== oldSkills.get(skill.name).version) {
      throw new Error(`${skill.name}: leave version changes to the release PR.`);
    }
    const text = readFileSync(join(root, 'skills', skill.name, 'SKILL.md'), 'utf8').replace(/\r\n/g, '\n');
    const end = text.indexOf('\n---', 4);
    const versions = text.slice(0, end).match(/^  version:\s*[^\n]+$/gm) ?? [];
    const version = versions[0]?.replace(/^  version:\s*/, '').replace(/^["']|["']$/g, '').trim();
    if (!text.startsWith('---\n') || end < 0 || versions.length !== 1 || version !== skill.version) {
      throw new Error(`${skill.name}: metadata.version must match the catalog before preparation.`);
    }
    for (const match of text.matchAll(/--skill-version\s+(\S+)(?=\s+--distribution)/g)) {
      if (match[1] !== skill.version) throw new Error(`${skill.name}: provenance version must match the catalog.`);
    }
    oldSkills.delete(skill.name);
  }
  for (const rename of renames) oldSkills.delete(rename.from);
  if (oldSkills.size) throw new Error(`Skill removal needs a supported immutable removal record: ${[...oldSkills.keys()].join(', ')}`);
}

export function planSkillRelease(root, baseline = releaseBaseline(root)) {
  const prior = catalogAt(root, baseline);
  const catalog = readJson(root, 'distribution/catalog.json');
  const renames = activeSkillRenames(root, prior, catalog);
  const paths = git(root, 'diff', '--name-only', '--no-renames', '-z', baseline, 'HEAD').split('\0').filter(Boolean);
  // The old canonical UI metadata is deleted with the source folder; the
  // release generates the new file from the new canonical catalog entry.
  const retiredMetadata = new Set(renames.map(({ from }) => `skills/${from}/agents/openai.yaml`)
    .filter((path) => !existsSync(join(root, path))));
  const forbidden = paths.filter((path) => (generated.test(path) && !retiredMetadata.has(path)) || path.startsWith('releases/'));
  if (forbidden.length) throw new Error(`Generated files and release records belong in the release PR: ${forbidden.join(', ')}`);
  assertSourceVersions(root, prior, catalog, renames);
  const oldSkills = new Map(prior.skills.map((skill) => [skill.name, skill]));
  const changedNames = new Set(paths.flatMap((path) => path.match(/^skills\/([^/]+)\//)?.[1] ?? []));
  for (const rename of renames) changedNames.delete(rename.from);
  for (const skill of catalog.skills) {
    if (JSON.stringify(skill) !== JSON.stringify(oldSkills.get(skill.name))) changedNames.add(skill.name);
  }
  const known = new Set(catalog.skills.map((skill) => skill.name));
  for (const name of changedNames) {
    if (!known.has(name)) throw new Error(`Canonical skill ${name} must be registered in the catalog.`);
  }
  const skills = [...changedNames].sort().map((name) => ({ name, change: oldSkills.has(name) ? 'patch' : 'initial' }));
  const pending = skills.length > 0 || paths.some((path) => packaging.some((pattern) => pattern.test(path)));
  const subjects = pending ? git(root, 'log', '--first-parent', '--reverse', '--format=%s', `${baseline}..HEAD`)
    .split('\n').filter(Boolean) : [];
  const summary = ['Update Qodo skills and marketplace packages.', ...subjects.map((subject) => `- ${subject}`)].join('\n');
  return { baseline, pending, skills, summary };
}

export function prepareSkillRelease(root, plan = planSkillRelease(root)) {
  if (!plan.pending) return null;
  return prepareRelease(['--summary', plan.summary, '--package', 'patch',
    ...plan.skills.flatMap(({ name, change }) => ['--skill', `${name}=${change}`])], root, { baseCommit: plan.baseline });
}

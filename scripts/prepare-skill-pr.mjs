/** Prepare existing skill edits using trusted base tooling; never check out PR code. */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { incrementVersion, prepareRelease, releaseTransaction } from './prepare-release.mjs';

const shaPattern = /^[a-f0-9]{40}$/;
const generatedPath = /^(?:\.agents\/plugins\/|\.claude-plugin\/|codex-packages\/|kiro-power(?:-standards)?\/|packages\/|distribution\/(?:catalog\.json|qodo-skills-index\.json(?:\.sha256)?|qodo-cli-managed-bundle\.json(?:\.sha256)?)$|package(?:-lock)?\.json$|plugin\.json$|gemini-extension\.json$|releases\/v\d+\.\d+\.\d+\.json$|skills\/[^/]+\/agents\/openai\.yaml$)/;

function git(root, ...args) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
}

function names(raw) {
  return raw.split('\0').filter(Boolean);
}

function file(root, ref, path) {
  const entry = git(root, 'ls-tree', '-z', ref, '--', path);
  if (!entry.startsWith('100644 blob ') || entry.split('\t')[1] !== `${path}\0`) {
    throw new Error(`${path} must be an existing regular non-executable file.`);
  }
  const bytes = execFileSync('git', ['show', `${ref}:${path}`], { cwd: root, maxBuffer: 1024 * 1024 });
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

function normalizeVersion(text, version) {
  const normalized = text.replace(/\r\n/g, '\n');
  const end = normalized.indexOf('\n---', 4);
  if (!normalized.startsWith('---\n') || end < 0) throw new Error('Skill frontmatter is missing.');
  const frontmatter = normalized.slice(0, end);
  if ((frontmatter.match(/^  version:\s*.+$/gm) ?? []).length !== 1) {
    throw new Error('Skill must have exactly one metadata.version field.');
  }
  return frontmatter.replace(/^  version:\s*.+$/m, `  version: "${version}"`)
    + normalized.slice(end).replace(/--skill-version\s+\S+(?=\s+--distribution)/g, `--skill-version ${version}`);
}

function withoutVersions(catalog) {
  const copy = structuredClone(catalog);
  delete copy.package.version;
  for (const skill of copy.skills) delete skill.version;
  return JSON.stringify(copy);
}

function packageWithoutVersion(text) {
  const value = JSON.parse(text);
  delete value.version;
  if (value.packages?.['']) delete value.packages[''].version;
  return JSON.stringify(value);
}

function previousGeneratedPaths(root, base, catalog, release, summary) {
  const known = new Map(catalog.skills.map((skill) => [skill.name, skill]));
  if (release.version !== incrementVersion(catalog.package.version, 'patch')
    || release.package?.change !== 'patch' || !Array.isArray(release.skills) || !release.skills.length
    || new Set(release.skills.map(({ name }) => name)).size !== release.skills.length
    || release.skills.some((skill) => !known.has(skill.name) || skill.change !== 'patch'
      || skill.version !== incrementVersion(known.get(skill.name).version, 'patch'))) {
    throw new Error('The previous automatic release is not a patch of the current base; maintainer reconciliation is required.');
  }
  // Reproduce only its ownership from trusted base content, never old PR code or metadata.
  const snapshot = releaseTransaction(root);
  try {
    prepareRelease(['--summary', summary, ...release.skills.flatMap(({ name }) => ['--skill', `${name}=patch`])], root);
    return new Set([
      ...names(git(root, 'diff', '--name-only', '-z', base)),
      ...names(git(root, 'ls-files', '--others', '--exclude-standard', '-z')),
    ]);
  } finally {
    snapshot.rollback();
    snapshot.close();
  }
}

export function prepareSkillPullRequest({ root, base, head, number }) {
  if (!shaPattern.test(base) || !shaPattern.test(head) || !Number.isSafeInteger(number) || number < 1) {
    throw new Error('Expected full base/head commit SHAs and a positive PR number.');
  }
  if (git(root, 'rev-parse', 'HEAD').trim() !== base || git(root, 'status', '--porcelain').trim()) {
    throw new Error('Preparation requires a clean checkout of the trusted base commit.');
  }
  const catalog = JSON.parse(file(root, base, 'distribution/catalog.json'));
  const known = new Map(catalog.skills.map((skill) => [`skills/${skill.name}/SKILL.md`, skill]));
  const changed = names(git(root, 'diff', '--name-only', '--no-renames', '-z', `${base}...${head}`));
  const sourcePaths = changed.filter((path) => known.has(path));
  if (!sourcePaths.length) return { status: 'skipped', reason: 'No existing skill instructions changed.' };
  const unsupported = changed.filter((path) => !known.has(path) && !generatedPath.test(path));
  if (unsupported.length) {
    return { status: 'skipped', reason: `Maintainer preparation required for mixed or structural changes: ${unsupported.join(', ')}` };
  }
  const removed = sourcePaths.filter((path) => !git(root, 'ls-tree', '--name-only', head, '--', path).trim());
  if (removed.length) {
    return { status: 'skipped', reason: `Removed skills require maintainer preparation: ${removed.join(', ')}` };
  }
  if (git(root, 'merge-base', base, head).trim() !== base) {
    throw new Error('This PR is behind main. Use Update branch in GitHub, resolve any conflicts, and preparation will run again.');
  }
  const headCatalog = JSON.parse(file(root, head, 'distribution/catalog.json'));
  if (withoutVersions(headCatalog) !== withoutVersions(catalog)) {
    return { status: 'skipped', reason: 'Catalog metadata changes require maintainer preparation.' };
  }
  for (const path of ['package.json', 'package-lock.json']) {
    if (changed.includes(path)
      && packageWithoutVersion(file(root, head, path)) !== packageWithoutVersion(file(root, base, path))) {
      return { status: 'skipped', reason: `${path} has non-version changes requiring maintainer preparation.` };
    }
  }
  const summary = `Update skill instructions (PR #${number})`;
  let previous = new Set();
  if (headCatalog.package.version !== catalog.package.version) {
    const releasePath = `releases/v${headCatalog.package.version}.json`;
    const release = JSON.parse(file(root, head, releasePath));
    if (release.summary !== summary) {
      return { status: 'skipped', reason: 'This PR already contains a maintainer-prepared release.' };
    }
    previous = previousGeneratedPaths(root, base, catalog, release, summary);
  }
  const edits = sourcePaths.flatMap((path) => {
    const skill = known.get(path);
    const text = normalizeVersion(file(root, head, path), skill.version);
    return text === normalizeVersion(file(root, base, path), skill.version) ? [] : [{ path, skill, text }];
  });
  if (!edits.length && !previous.size) return { status: 'skipped', reason: 'No skill behavior changes remain.' };
  for (const { path, text } of edits) writeFileSync(join(root, path), text);
  const release = edits.length ? prepareRelease([
    '--summary', summary,
    ...edits.flatMap(({ skill }) => ['--skill', `${skill.name}=patch`]),
  ], root) : null;
  git(root, 'add', '--all');
  const generated = new Set(names(git(root, 'diff', '--cached', '--name-only', '-z', base)));
  // Only replace files actually owned by this generation, never a broad directory tree.
  const owned = new Set([...generated, ...previous]);
  const unexpected = changed.filter((path) => !owned.has(path));
  if (unexpected.length) throw new Error(`Preparation would discard unrelated edits: ${unexpected.join(', ')}`);
  const updates = names(git(root, 'diff', '--cached', '--name-only', '-z', head));
  const deletions = [];
  const additions = updates.flatMap((path) => {
    if (!owned.has(path)) throw new Error(`Refusing to write a file outside the generated change: ${path}`);
    if (!git(root, 'ls-files', '--', path).trim()) {
      deletions.push({ path });
      return [];
    }
    const content = readFileSync(join(root, path));
    return [{ path, contents: content.toString('base64') }];
  });
  return { status: updates.length ? 'prepared' : 'unchanged', version: release?.version ?? null, additions, deletions };
}

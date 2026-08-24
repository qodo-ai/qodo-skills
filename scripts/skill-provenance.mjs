/** Stamp generated skill copies with their lifecycle owner. */

const DISTRIBUTIONS = new Set(['skills-sh', 'marketplace', 'kiro-power', 'qodo-direct']);

export function stampSkillProvenance(content, provenance) {
  const { name, version, packageName, distribution } = provenance;
  if (!DISTRIBUTIONS.has(distribution)) throw new Error(`${name}: unsupported distribution ${distribution}`);

  const normalized = content.replace(/\r\n/g, '\n');
  const end = normalized.indexOf('\n---', 4);
  if (!normalized.startsWith('---\n') || end < 0) throw new Error(`${name}: invalid SKILL.md frontmatter`);

  const frontmatter = normalized.slice(0, end);
  if (!new RegExp(`^name:\\s*${name}$`, 'm').test(frontmatter)) {
    throw new Error(`${name}: SKILL.md name does not match catalog`);
  }
  if (!new RegExp(`^  version:\\s*["']?${version}["']?$`, 'm').test(frontmatter)) {
    throw new Error(`${name}: SKILL.md version does not match catalog`);
  }

  let stampedFrontmatter = frontmatter
    .replace(/^  package:\s*.+$/m, `  package: "${packageName}"`)
    .replace(/^  distribution:\s*.+$/m, `  distribution: "${distribution}"`);
  if (!/^  package:/m.test(stampedFrontmatter)) {
    stampedFrontmatter = stampedFrontmatter.replace(
      /^  recommended:\s*.+$/m,
      (line) => `${line}\n  package: "${packageName}"`,
    );
  }
  if (!/^  distribution:/m.test(stampedFrontmatter)) {
    stampedFrontmatter = stampedFrontmatter.replace(
      /^  package:\s*.+$/m,
      (line) => `${line}\n  distribution: "${distribution}"`,
    );
  }

  const body = normalized.slice(end).replace(
    /--skill-version\s+[0-9A-Za-z.-]+\s+--distribution\s+[a-z0-9-]+/g,
    `--skill-version ${version} --distribution ${distribution}`,
  );
  if (!body.includes(`--skill ${name} --skill-version ${version} --distribution ${distribution}`)) {
    throw new Error(`${name}: no provenance-bearing Qodo invocation found`);
  }
  return `${stampedFrontmatter}${body}`;
}

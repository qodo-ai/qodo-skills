/** Stamp generated skill copies with their lifecycle owner and instruction mode. */

const DISTRIBUTIONS = new Set(['skills-sh', 'marketplace', 'kiro-power']);

export function stampSkillProvenance(content, provenance) {
  const { name, version, packageName, distribution, host } = provenance;
  if (!DISTRIBUTIONS.has(distribution)) throw new Error(`${name}: unsupported distribution ${distribution}`);
  if (host !== undefined && !/^[a-z0-9][a-z0-9-]{0,63}$/.test(host)) {
    throw new Error(`${name}: invalid host ${host}`);
  }

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
  if (/^  instruction_mode:/m.test(stampedFrontmatter)) {
    stampedFrontmatter = stampedFrontmatter.replace(
      /^  instruction_mode:\s*.+$/m,
      '  instruction_mode: "embedded"',
    );
  } else {
    stampedFrontmatter = stampedFrontmatter.replace(
      /^  distribution:\s*.+$/m,
      (line) => `${line}\n  instruction_mode: "embedded"`,
    );
  }

  let body = normalized.slice(end).replace(
    /--skill-version\s+[0-9A-Za-z.-]+\s+--distribution\s+[a-z0-9-]+/g,
    `--skill-version ${version} --distribution ${distribution}`,
  );
  if (host) {
    body = body.replace(
      new RegExp(`(--skill ${name} --skill-version ${version} --distribution ${distribution})(?: --host [a-z0-9-]+)?`, 'g'),
      `$1 --host ${host}`,
    );
  }
  if (!body.includes(`--skill ${name} --skill-version ${version} --distribution ${distribution}`)) {
    throw new Error(`${name}: no provenance-bearing Qodo invocation found`);
  }
  return `${stampedFrontmatter}${body}`;
}

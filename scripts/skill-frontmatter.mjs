/** Shared canonical scalar-frontmatter parsing; no YAML execution or new dependency. */
export function parseSkillFrontmatter(text) {
  const match = text.replace(/\r\n/g, '\n').match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const result = { metadata: {} };
  let section = '';
  for (const line of match[1].split('\n')) {
    const field = line.match(/^([a-z_-]+):(?:\s*(.*))?$/);
    if (field) {
      section = field[1];
      if (field[2]) result[field[1]] = field[2].replace(/^['"]|['"]$/g, '');
      continue;
    }
    const nested = line.match(/^  ([a-z_-]+):\s*(.+)\s*$/);
    if (section === 'metadata' && nested) {
      result.metadata[nested[1]] = nested[2].replace(/^['"]|['"]$/g, '');
    }
  }
  return result;
}

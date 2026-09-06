/** Structural checks only; prose quality and attribution accuracy require review. */
export function validateSkillDelivery(text, heading) {
  const sections = [];
  let section;
  let fence;
  for (const line of text.replace(/\r\n/g, '\n').split('\n')) {
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
    if (fence) {
      section?.push(line);
      if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length
        && !marker[2].trim()) fence = undefined;
      continue;
    }
    if (marker) {
      fence = marker[1];
      section?.push(line);
      continue;
    }
    const title = line.match(/^## (.+)$/);
    if (title) {
      // A response heading outside a fence must not escape the preceding section's check.
      if (section && /\bQodo\b/.test(title[1])) section.push(line);
      section = title[1] === heading ? [] : undefined;
      if (section) sections.push(section);
    } else {
      section?.push(line);
    }
  }

  const errors = [];
  if (!heading || sections.length !== 1 || !/\bQodo\b/.test(sections[0].join('\n'))) {
    errors.push('expected one delivery section with Qodo attribution');
  }
  if (sections.some((lines) => /^\s*(?:>\s*)?#{1,6}\s+.*\bQodo\b/m.test(lines.join('\n')))) {
    errors.push('delivery examples must not use branded Markdown headings');
  }
  return errors;
}

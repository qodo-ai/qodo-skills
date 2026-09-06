import assert from 'node:assert/strict';
import test from 'node:test';
import { validateSkillDelivery } from '../scripts/skill-delivery.mjs';

const check = (text) => validateSkillDelivery(text, 'Deliver');

test('accepts natural attribution and issue titles without prescribing wording', () => {
  for (const attribution of ['I checked the worker through Qodo.', 'Qodo reported no findings.']) {
    assert.deepEqual(check(`# Set up Qodo\n\n## Deliver\n${attribution}\n### Timeout recovery\nEvidence.\n## Configuration\nSettings.`), []);
  }
});

test('requires a registered, unique delivery section with attribution inside it', () => {
  assert.match(validateSkillDelivery('## Deliver\nQodo.', undefined).join(), /expected one delivery section/);
  for (const text of ['# Qodo\nNo delivery section.', '## Deliver\nDone.\n## Configuration\nQodo.', '## Deliver\nQodo.\n## Deliver\nQodo.']) {
    assert.match(check(text).join(), /expected one delivery section/);
  }
});

test('rejects branded response headings at every Markdown level', () => {
  for (let level = 1; level <= 6; level += 1) {
    const title = `${'#'.repeat(level)} Qodo Review`;
    for (const example of [title, `> ${title}`, `\`\`\`markdown\n${title}\n\`\`\``]) {
      assert.match(check(`## Deliver\nUse Qodo attribution.\n${example}\n## Configuration\nSettings.`).join(), /branded Markdown headings/);
    }
  }
});

test('fenced level-two example headings do not hide later branded banners', () => {
  for (const fence of ['```', '~~~~']) {
    const text = `## Deliver\nQodo attribution.\n${fence}\n## Findings\n# 🔍 Qodo Pre-PR Review\n${fence}\n## Configuration\nSettings.`;
    assert.match(check(text).join(), /branded Markdown headings/);
    assert.match(check(text.replace(/\n/g, '\r\n')).join(), /branded Markdown headings/);
  }
});

test('example headings cannot satisfy or duplicate the actual delivery section', () => {
  assert.match(check('```\n## Deliver\nQodo.\n```').join(), /expected one delivery section/);
  assert.deepEqual(check('## Deliver\nQodo.\n````markdown\n```\n## Deliver\nA nested example.\n```\n````\n## Configuration\nSettings.'), []);
});

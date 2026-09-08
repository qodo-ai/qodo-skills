import assert from 'node:assert/strict';
import test from 'node:test';
import { validateKiroPowerContract } from '../scripts/kiro-power-contract.mjs';

const validManifest = {
  $schema: 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
  name: 'qodo',
  version: '1.1.0',
  description: 'Qodo review workflows for local coding agents.',
  author: { name: 'Qodo' },
  keywords: ['qodo', 'code-review'],
  license: 'MIT',
};

const validate = (manifest = validManifest, entries = ['plugin.json', 'skills/qodo-review/SKILL.md']) => (
  validateKiroPowerContract({ manifest, entries }, 'kiro-power')
);

test('accepts the Agent Plugins layout used by the Kiro Power', () => {
  assert.deepEqual(validate(), []);
});

test('rejects legacy Kiro Power files', () => {
  assert.match(validate(validManifest, ['plugin.json', 'POWER.md', 'skills/qodo-review/SKILL.md']).join('\n'), /POWER\.md is forbidden/);
  assert.match(validate(validManifest, ['plugin.json', 'steering/review.md', 'skills/qodo-review/SKILL.md']).join('\n'), /steering\/ is forbidden/);
});

test('rejects displayName and other fields outside Agent Plugins 1.0', () => {
  assert.match(validate({ ...validManifest, displayName: 'Qodo Code Review' }).join('\n'), /unsupported Agent Plugins field displayName/);
});

test('requires the manifest name to match the Kiro listing id', () => {
  const errors = validateKiroPowerContract({
    manifest: validManifest,
    entries: ['plugin.json', 'skills/qodo-review/SKILL.md'],
    expectedName: 'qodo-standards',
  }, 'kiro-power-standards');
  assert.match(errors.join('\n'), /name must match Kiro listing id qodo-standards/);
});

test('requires Kiro publication metadata and a packaged skill', () => {
  const manifest = { ...validManifest, description: '', author: {}, keywords: [] };
  const errors = validate(manifest, ['plugin.json']).join('\n');
  assert.match(errors, /description must be a non-empty string/);
  assert.match(errors, /author\.name must be a non-empty string/);
  assert.match(errors, /keywords must contain non-empty strings/);
  assert.match(errors, /expected at least one skills\/<name>\/SKILL\.md/);
});

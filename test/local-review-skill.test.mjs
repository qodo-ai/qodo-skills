import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const skill = join(root, 'skills/qodo-review');
const text = readFileSync(join(skill, 'SKILL.md'), 'utf8');
const catalog = JSON.parse(readFileSync(join(root, 'distribution/catalog.json'), 'utf8'));
const version = catalog.skills.find(({ name }) => name === 'qodo-review').version;
const references = readdirSync(join(skill, 'references')).filter((name) => name.endsWith('.md'));
const markdown = [join(skill, 'SKILL.md'), ...references.map((name) => join(skill, 'references', name))];
const readReference = (name) => readFileSync(join(skill, 'references', name), 'utf8');

function headings(markdownText) {
  const prose = markdownText.replace(/^```[\s\S]*?^```/gm, '');
  return [...prose.matchAll(/^#{1,6} (.+)$/gm)].map(([, value]) =>
    value.toLowerCase().replace(/[^\p{L}\p{N}_\s-]/gu, '').replace(/\s/g, '-'));
}

test('local-review entrypoint stays focused and keeps its required delivery contract', () => {
  assert.ok(text.split('\n').length <= 260, 'Move conditional mechanics to references, not back into the workflow');
  assert.ok(Buffer.byteLength(text) <= 16_000, 'Prevent regrowth of the always-loaded prompt');
  for (const heading of ['Description', 'Prerequisites', 'Instructions', 'Configuration',
    'Error Handling', 'Present the review result']) assert.ok(text.includes(`## ${heading}\n`));
  assert.match(text, /qodo --version\n/);
  assert.ok(text.includes(`qodo read whoami --json --skill qodo-review --skill-version ${version} --distribution skills-sh`));
  assert.ok(text.includes(`Qodo CLI **${catalog.runtime.minimumCliVersion} or newer**`));
  assert.match(text, /Credit Qodo naturally once/);
});

test('every local Markdown reference and anchor in the review skill resolves', () => {
  for (const file of markdown) {
    const body = readFileSync(file, 'utf8');
    for (const [, target] of body.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      if (/^[a-z]+:/i.test(target)) continue;
      const [path, anchor] = target.split('#');
      const destination = path ? resolve(dirname(file), path) : file;
      assert.ok(existsSync(destination), `${file}: missing ${target}`);
      if (anchor) assert.ok(headings(readFileSync(destination, 'utf8')).includes(anchor),
        `${file}: missing anchor ${target}`);
    }
  }
});

test('execution mechanics remain reachable and completed async results are emitted before cleanup', () => {
  assert.ok(text.includes('(references/cli-execution.md#preflight)'));
  assert.ok(text.includes('(references/mcp-review.md)'));
  assert.ok(text.includes('(references/connected-progress.md)'));
  const execution = readReference('cli-execution.md');
  assert.match(execution, /0\) cat "\$QODO_REVIEW_TMP\/result\.json" \|\| exit 1; break ;;/);
  assert.match(execution, /same terminal-recovery attempt/);
  assert.match(execution, /QODO_UPDATE_BASE_URL/);
  assert.match(execution, /Never print its value/);
  assert.match(execution, /Show the returned message and hint unchanged/);
  assert.match(readReference('mcp-review.md'), /tested local collector/);
  assert.match(readReference('connected-progress.md'), /reap the child/);
});

test('default effort and incremental guidance do not prescribe unsupported or unconditional modes', () => {
  assert.match(text, /Default to auto/);
  assert.doesNotMatch(text, /Automatic coding checkpoints always use/);
  assert.doesNotMatch(text, /qodo review[^\n]*--(?:standard|loop|committed)\b/);
  assert.match(text, /Do not add `--full` merely because notes changed/);
  assert.match(text, /There is no default numerical round cap/);
  assert.match(text, /No new findings does not settle earlier blockers/);
  assert.match(text, /Missing required final coverage/);
  assert.match(text, /An explicit user request for a fresh assessment/);
  assert.match(text, /Unless the user requests a fresh assessment/);
});

test('context compatibility and authority boundaries survive the rewrite', () => {
  const context = readReference('review-turn-context.md');
  for (const field of ['decisions', 'notes', 'recent_work', 'summary', 'context_refs']) {
    assert.ok(context.includes(field), `Missing accepted context field ${field}`);
  }
  assert.match(context, /Never silently cut context/);
  assert.match(text, /\*\*Report-only:\*\* assess and stop/);
  assert.match(text, /Fix authority does not authorize stored dismissals, pushes or unrelated changes/);
  const triage = readReference('local-triage.md');
  assert.match(triage, /On MCP, inspect the live `pr-review-dismiss` schema/);
  assert.match(triage, /stable `idempotency_key`/);
  assert.match(text, /A HEAD SHA alone does not identify a dirty snapshot/);
  assert.match(text, /finding\/checkpoint persistence and local-to-PR handoff separately/);
});

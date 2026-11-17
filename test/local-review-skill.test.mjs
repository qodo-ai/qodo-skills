import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { main, prepareReviewEvaluation } from '../scripts/eval-review-skill.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const skill = join(root, 'skills/qodo-review');
const text = readFileSync(join(skill, 'SKILL.md'), 'utf8');
const catalog = JSON.parse(readFileSync(join(root, 'distribution/catalog.json'), 'utf8'));
const version = catalog.skills.find(({ name }) => name === 'qodo-review').version;
const references = readdirSync(join(skill, 'references')).filter((name) => name.endsWith('.md'));
const markdown = [join(skill, 'SKILL.md'), ...references.map((name) => join(skill, 'references', name))];
const readReference = (name) => readFileSync(join(skill, 'references', name), 'utf8');

function evaluatedReleaseStamps(body, currentVersion, evaluatedVersion) {
  // Release preparation changes only these two stamps; the evidence keeps its original raw hash.
  assert.ok(body.includes(`  version: "${currentVersion}"`), 'Current metadata must match the release catalog');
  return body.replace(`  version: "${currentVersion}"`, `  version: "${evaluatedVersion}"`)
    .replaceAll(`--skill-version ${currentVersion} --distribution`,
      `--skill-version ${evaluatedVersion} --distribution`);
}

function headings(markdownText) {
  const prose = markdownText.replace(/^```[\s\S]*?^```/gm, '');
  return [...prose.matchAll(/^#{1,6} (.+)$/gm)].map(([, value]) =>
    value.toLowerCase().replace(/[^\p{L}\p{N}_\s-]/gu, '').replace(/\s/g, '-'));
}

test('local-review entrypoint stays focused and keeps its required delivery contract', () => {
  assert.ok(text.split('\n').length <= 320, 'Keep canonical policy here and conditional command mechanics in references');
  assert.ok(Buffer.byteLength(text) <= 21_000, 'Prevent regrowth of the always-loaded prompt');
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
  assert.match(execution, /Run the resolved invocation with only `--version`/);
  assert.match(execution, /After fallback succeeds, do not return to the unavailable bare command/);
  assert.match(execution, /If neither installed invocation works, report the missing CLI and stop/);
  assert.match(execution, /Never invent a digest or pipe an installer into a shell/);
  assert.match(execution, /For every updater route, first require its supported check/);
  assert.match(execution, /A failed check, no update or an incompatible target means stop/);
  assert.match(execution, /If user\/task instructions or the returned error forbid automatic retries, stop/);
  assert.match(text, /In every command example, replace `qodo` with that resolved invocation/);
  assert.match(readReference('mcp-review.md'), /tested local collector/);
  assert.match(readReference('connected-progress.md'), /reap the child/);
  for (const name of ['cli-execution.md', 'mcp-review.md', 'local-triage.md']) {
    assert.match(readReference(name), /SKILL\.md#execution-and-recovery-policy/);
  }
  for (const gate of [
    'Every updater route, including ordinary update, needs a successful check',
    'User/task no-auto-retry instructions',
    'Installation requires covering approval',
    'Never substitute a run ID or PR URL',
    'possible sandbox',
  ]) assert.ok(text.toLowerCase().includes(gate.toLowerCase()), `Canonical policy missing: ${gate}`);
});

test('default effort and incremental guidance do not prescribe unsupported or unconditional modes', () => {
  assert.match(text, /Default to auto/);
  assert.doesNotMatch(text, /Automatic coding checkpoints always use/);
  assert.doesNotMatch(text, /qodo review[^\n]*--(?:standard|loop|committed)\b/);
  assert.match(text, /Do not add `--full` merely because notes changed/);
  assert.match(text, /There is no default numerical round cap/);
  assert.match(text, /No new findings does not settle earlier blockers/);
  assert.match(text, /Use a known base SHA literally or explicitly bind its shell variable/);
  assert.match(text, /A resolved finding alone does not establish overall readiness/);
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
  assert.match(text, /“Tested” does not mean “tests passed.”/);
  assert.match(text, /\*\*Report-only:\*\* assess and stop/);
  assert.match(text, /Fix authority does not authorize stored dismissals, pushes or unrelated changes/);
  const triage = readReference('local-triage.md');
  assert.match(triage, /On MCP, inspect the live `pr-review-dismiss` schema/);
  assert.match(triage, /stable `idempotency_key`/);
  assert.match(text, /A HEAD SHA alone does not identify a dirty snapshot/);
  assert.match(text, /finding\/checkpoint persistence and local-to-PR handoff separately/);
  for (const group of ['compatibility-boundaries', 'followup-and-finding-state',
    'milestone-and-final-scope', 'recovery-and-readiness', 'fallback-invocation', 'recovery-policy-guards']) {
    const prompt = readFileSync(join(root, 'evals/qodo-review', group, 'prompt.md'), 'utf8');
    assert.match(prompt, /allowed_tools: \[Read, Glob, Grep, Skill\]/);
    assert.doesNotMatch(prompt.split('---', 3)[1], /\b(?:Write|Edit|Bash)\b/);
  }
});

test('opt-in behavior evaluation stages the actual instructions and every version fixture without model execution', () => {
  for (const args of [['--ref'], ['--output-parent'], ['--ref', '--run']]) {
    assert.throws(() => main(args), /requires a value/);
  }
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-stage-test-'));
  try {
    const staged = prepareReviewEvaluation({ root, parent });
    assert.equal(readFileSync(join(staged.plugin, 'skills/qodo-review/SKILL.md'), 'utf8'), text);
    assert.equal(statSync(join(staged.plugin, 'skills/qodo-review/SKILL.md')).mode & 0o222, 0);
    assert.equal(staged.manifest.source_kind, 'current working instruction bytes');
    assert.equal(staged.manifest.cases.length, 6);
    assert.equal(Object.values(staged.manifest.assertions).reduce((sum, count) => sum + count, 0), 29);
    assert.ok(staged.args.includes('--no-publish') && staged.args.includes('--no-scaffold'));
    assert.ok(!staged.args.includes('--allow-real-servers') && !staged.args.includes('--trust-plugin'));
    const boundary = readFileSync(join(staged.plugin, 'evals/compatibility-boundaries/prompt.md'), 'utf8');
    for (const version of ['1.6.0', '"custom build"', '2.0.0', '2.3.1']) assert.ok(boundary.includes(version));
    assert.ok(boundary.includes('summary, not notes') && boundary.includes('decisions=['));
    assert.throws(() => prepareReviewEvaluation({ root, parent: root }), /outside the source repository/);
    assert.equal(existsSync(join(staged.directory, 'result.json')), false, 'Staging must not run a model');
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test('recorded behavior evidence covers current instructions and every assertion, with inspectable passing candidate results', () => {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-behavior');
  const manifest = JSON.parse(readFileSync(join(evidenceRoot, 'manifest.json'), 'utf8'));
  const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.method, 'fresh-native-agents-with-anonymous-final-answer-grading');
  assert.equal(manifest.cases.length, 6);
  assert.deepEqual(Object.keys(manifest.snapshots.candidate.fingerprints).sort(),
    ['SKILL.md', ...references.map((name) => `references/${name}`)].sort());
  assert.deepEqual(manifest.cases.map((item) => item.name).sort(),
    readdirSync(join(root, 'evals/qodo-review'), { withFileTypes: true })
      .filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort());
  for (const [name, expected] of Object.entries(manifest.snapshots.candidate.fingerprints)) {
    const current = readFileSync(join(skill, name));
    const evaluated = name === 'SKILL.md' ? evaluatedReleaseStamps(current.toString('utf8'),
      version, manifest.snapshots.candidate.release_metadata_version) : current;
    assert.equal(sha256(evaluated), expected, `Stale instruction evidence: ${name}`);
  }
  const releaseOnly = text.replace(`  version: "${version}"`, '  version: "999.0.0"')
    .replaceAll(`--skill-version ${version} --distribution`, '--skill-version 999.0.0 --distribution');
  assert.equal(evaluatedReleaseStamps(releaseOnly, '999.0.0', version), text);
  assert.notEqual(evaluatedReleaseStamps(`${releaseOnly}\nChanged behavior.\n`, '999.0.0', version), text);
  let assertionCount = 0, candidatePasses = 0;
  for (const item of manifest.cases) {
    const fixture = join(root, 'evals/qodo-review', item.name);
    assert.equal(sha256(readFileSync(join(fixture, 'prompt.md'))), item.prompt_sha256);
    const graders = readdirSync(join(fixture, 'graders')).filter((name) => name.endsWith('.md')).sort();
    assert.deepEqual(item.assertions.map((entry) => entry.file), graders);
    for (const grader of item.assertions) {
      assert.equal(sha256(readFileSync(join(fixture, 'graders', grader.file))), grader.sha256);
    }
    assertionCount += graders.length;
    for (const configuration of ['candidate', 'baseline']) {
      const run = item.runs[configuration];
      assert.deepEqual(Object.keys(run.artifacts).sort(), [run.response, run.grading, run.provenance].sort());
      for (const [path, hash] of Object.entries(run.artifacts)) {
        assert.ok(!path.includes('..') && !path.startsWith('/'), 'Evidence paths stay inside the fixture');
        assert.equal(sha256(readFileSync(join(evidenceRoot, path))), hash, path);
      }
      const grade = JSON.parse(readFileSync(join(evidenceRoot, run.grading), 'utf8'));
      assert.deepEqual(grade.expectations.map((entry) => entry.text), graders.map((file) =>
        readFileSync(join(fixture, 'graders', file), 'utf8').replace(/^---\n[\s\S]*?\n---\n/, '').trim()));
      const provenance = JSON.parse(readFileSync(join(evidenceRoot, run.provenance), 'utf8'));
      assert.deepEqual(provenance.fingerprints, manifest.snapshots[configuration].fingerprints);
      assert.equal(provenance.response_sha256, sha256(readFileSync(join(evidenceRoot, run.response))));
      assert.equal(grade.expectations.length, graders.length);
      assert.equal(grade.summary.passed, grade.expectations.filter((expectation) => expectation.passed).length);
      assert.equal(grade.summary.total, graders.length);
      assert.ok(grade.expectations.every((expectation) => expectation.evidence.trim()));
      if (configuration === 'candidate') {
        candidatePasses += grade.summary.passed;
        assert.ok(grade.expectations.every((expectation) => expectation.passed), `Behavior evidence failed: ${item.name}`);
      }
    }
  }
  assert.equal(assertionCount, 29);
  assert.equal(candidatePasses, 29);
});

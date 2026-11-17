import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { assertFixtureProvenance, assertGrade, assertRunIdentity, assertRunPaths, createEvaluationRepository } from './helpers/review-evaluation-fixtures.mjs';
import { assertHistoryArchives, hashEvidence, readEvidenceFile } from './helpers/review-evidence-archives.mjs';
import { prepareReviewEvaluation } from '../scripts/eval-review-skill.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const json = (directory, path) => JSON.parse(readEvidenceFile(directory, path));
const assertionText = (bytes) => bytes.toString('utf8').replace(/^---\n[\s\S]*?\n---\n/, '').trim();

test('historical evidence requires all archives and rejects removed, changed or extra artifacts', () => {
  const directory = mkdtempSync(join(tmpdir(), 'qodo-required-history-'));
  const manifest = { history: {} };
  try {
    for (const iteration of [6, 7, 8, 9, 10, 11, 12, 13]) {
      const path = `history/iteration-${iteration}`;
      mkdirSync(join(directory, path), { recursive: true });
      writeFileSync(join(directory, path, 'response.md'), 'Original response\n');
      const archive = `${JSON.stringify({ artifacts: { 'response.md': hashEvidence('Original response\n') } })}\n`;
      writeFileSync(join(directory, path, 'archive.json'), archive);
      manifest.history[`iteration_${iteration}`] = { path: `${path}/archive.json`, sha256: hashEvidence(archive) };
    }
    assert.deepEqual(assertHistoryArchives(directory, manifest), { 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1, 13: 1 });
    for (const iteration of [6, 7, 8, 9, 10, 11, 12, 13]) {
      const changed = structuredClone(manifest);
      delete changed.history[`iteration_${iteration}`];
      assert.throws(() => assertHistoryArchives(directory, changed), /Missing required/);
      const file = join(directory, `history/iteration-${iteration}/response.md`);
      writeFileSync(file, 'Edited response\n');
      assert.throws(() => assertHistoryArchives(directory, manifest), /Changed historical artifact/);
      rmSync(file);
      assert.throws(() => assertHistoryArchives(directory, manifest), /inventory changed/);
      writeFileSync(file, 'Original response\n');
      const extra = join(directory, `history/iteration-${iteration}/unlisted.md`);
      writeFileSync(extra, 'Unlisted evidence\n');
      assert.throws(() => assertHistoryArchives(directory, manifest), /inventory changed/);
      rmSync(extra);
    }
    assert.deepEqual(assertHistoryArchives(directory, manifest), { 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1, 13: 1 });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('grade validation rejects empty cases for candidate and baseline', () => {
  for (const candidate of [false, true]) for (const pass_rate of [NaN, null]) {
    const grade = { expectations: [], summary: { passed: 0, failed: 0, total: 0, pass_rate } };
    assert.throws(() => assertGrade(grade, [], candidate), /at least one assertion/);
  }
});

test('assertion evidence needs a matching response citation with a valid line range', () => {
  const make = (evidence) => ({ expectations: [{ text: 'Check', passed: true, evidence }],
    summary: { passed: 1, failed: 0, total: 1, pass_rate: 1 } });
  const context = { response: 'First line\nSecond line\n', label: 'B' };
  for (const candidate of [false, true]) {
    for (const evidence of ['passed', 'prompt.md:1', 'A.md:1', 'B.md:0', 'B.md:3', 'B.md:2-1', 'B.md:1–3'])
      assert.throws(() => assertGrade(make(evidence), ['Check'], candidate, context), /citation/);
    for (const evidence of ['B.md:1–2 supports this', 'response.md:2 supports this'])
      assert.equal(assertGrade(make(evidence), ['Check'], candidate, context), 1);
    assert.throws(() => assertGrade(make('response.md:1'), ['Check'], candidate), /Recorded response text/);
  }
});

test('malformed case and grader layouts fail for untracked, ignored and committed inputs', () => {
  for (const path of ['SmokeCase/prompt.md', 'smoke_case/case.yaml',
    'compatibility-boundaries/graders/nested/check.md', 'compatibility-boundaries/graders/bad name.md',
    'compatibility-boundaries/graders/check.txt', 'nested/case/prompt.md', 'case.yaml']) {
    const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-layout-'));
    try {
      const { source, git, commit } = createEvaluationRepository(parent,
        join(root, 'skills/qodo-review'), join(root, 'evals/qodo-review'));
      const relative = `evals/qodo-review/${path}`, target = join(source, relative);
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, 'Recognizable malformed input\n');
      const stage = () => prepareReviewEvaluation({ root: source, parent });
      assert.throws(stage, /Invalid evaluation input layout/);
      writeFileSync(join(source, '.git/info/exclude'), `${relative}\n`);
      assert.equal(git(['check-ignore', relative]), relative);
      assert.throws(stage, /Invalid evaluation input layout/);
      git(['add', '--force', '--', relative]);
      commit();
      assert.throws(stage, /Invalid evaluation input layout/);
      writeFileSync(target, 'Dirty malformed input\n');
      assert.throws(stage, /Invalid evaluation input layout/);
    } finally { rmSync(parent, { recursive: true, force: true }); }
  }
});

test('run paths cannot reuse another case or configuration artifact namespace', () => {
  const make = (name, configuration) => Object.fromEntries(Object.entries({
    response: 'response.md', grading: 'grading.json', provenance: 'provenance.json',
  }).map(([key, file]) => [key, `${name}/${configuration}/${file}`]));
  const original = make('case-a', 'candidate');
  assertRunPaths(original, 'case-a', 'candidate');
  for (const replacement of [make('case-b', 'candidate'), make('case-a', 'baseline')])
    for (const key of Object.keys(original))
      assert.throws(() => assertRunPaths({ ...original, [key]: replacement[key] }, 'case-a', 'candidate'), /case and configuration/);
  const provenance = { evaluated_case: 'case-a', configuration: 'candidate' };
  assertRunIdentity(provenance, 'case-a', 'candidate');
  assert.throws(() => assertRunIdentity(provenance, 'case-b', 'candidate'), /case identity/);
  assert.throws(() => assertRunIdentity(provenance, 'case-a', 'baseline'), /configuration/);
});

test('historical focused MCP evidence matches its retained inputs, instructions and original judgments', () => {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-mcp-collection');
  const manifest = json(evidenceRoot, 'manifest.json');
  const primary = json(join(root, 'test/fixtures/qodo-review-behavior'), 'manifest.json');
  const archiveRoot = join(root, 'test/fixtures/qodo-review-behavior/history/iteration-9');
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.method, 'fresh-native-agents-with-anonymous-final-answer-grading');
  assert.deepEqual(manifest.evaluated_cases, ['mcp-collection']);
  assert.deepEqual(manifest.cases.map(({ name }) => name), manifest.evaluated_cases);
  assert.equal(manifest.input_cases.length, 8);
  assert.deepEqual(manifest.input_cases.map(({ name }) => name).sort(),
    readdirSync(join(archiveRoot, 'inputs'), { withFileTypes: true })
      .filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort());
  for (const item of manifest.input_cases) {
    const directory = join(archiveRoot, 'inputs', item.name);
    assert.equal(hashEvidence(readEvidenceFile(directory, 'case.yaml')), item.case_sha256);
    assert.equal(hashEvidence(readEvidenceFile(directory, 'prompt.md')), item.prompt_sha256);
    assert.deepEqual(item.assertions.map(({ file }) => file),
      readdirSync(join(directory, 'graders')).filter((name) => name.endsWith('.md')).sort());
    for (const grader of item.assertions)
      assert.equal(hashEvidence(readEvidenceFile(directory, `graders/${grader.file}`)), grader.sha256);
  }
  assert.deepEqual(manifest.snapshots.baseline.fingerprints, primary.snapshots.baseline.fingerprints);
  assert.equal(manifest.snapshots.baseline.source_commit, primary.snapshots.baseline.source_commit);
  const skill = join(archiveRoot, 'instructions'), snapshot = manifest.snapshots.candidate;
  assert.deepEqual(Object.keys(snapshot.fingerprints).sort(),
    ['SKILL.md', ...readdirSync(join(skill, 'references')).filter((name) => name.endsWith('.md'))
      .map((name) => `references/${name}`)].sort());
  for (const [path, expected] of Object.entries(snapshot.fingerprints)) {
    assert.equal(hashEvidence(readEvidenceFile(skill, path)), expected, `Changed historical instruction: ${path}`);
  }
  const item = manifest.cases[0], fixture = join(archiveRoot, 'inputs', item.name);
  assert.deepEqual(item, { ...manifest.input_cases.find(({ name }) => name === item.name), runs: item.runs });
  assert.match(readEvidenceFile(fixture, 'prompt.md').toString(), /allowed_tools: \[Read, Glob, Grep, Skill\]/);
  const assertions = item.assertions.map(({ file }) =>
    assertionText(readEvidenceFile(fixture, `graders/${file}`)));
  assert.equal(assertions.length, 5);
  const scores = {};
  for (const configuration of ['candidate', 'baseline']) {
    const run = item.runs[configuration];
    assertRunPaths(run, item.name, configuration);
    assert.deepEqual(Object.keys(run.artifacts).sort(), [run.response, run.grading, run.provenance].sort());
    for (const [path, hash] of Object.entries(run.artifacts))
      assert.equal(hashEvidence(readEvidenceFile(evidenceRoot, path)), hash, path);
    const grade = json(evidenceRoot, run.grading);
    // Original iteration9 labels are retained in its unchanged anonymous judgments.
    scores[configuration] = { passed: assertGrade(grade, assertions, configuration === 'candidate', {
      response: readEvidenceFile(evidenceRoot, run.response).toString('utf8'), label: configuration === 'candidate' ? 'A' : 'B',
    }), total: 5 };
    const provenance = json(evidenceRoot, run.provenance);
    assertFixtureProvenance(provenance, { fixture_source_commit: manifest.fixture_source_commit, cases: manifest.input_cases });
    assert.deepEqual(provenance.fixture_fingerprints, manifest.fixture_fingerprints);
    assert.equal(provenance.source_commit, manifest.snapshots[configuration].source_commit);
    assert.deepEqual(provenance.fingerprints, manifest.snapshots[configuration].fingerprints);
    assert.equal(provenance.response_sha256, hashEvidence(readEvidenceFile(evidenceRoot, run.response)));
  }
  assert.deepEqual(manifest.scores, scores);
});

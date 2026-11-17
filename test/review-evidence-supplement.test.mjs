import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { assertFixtureProvenance, assertGrade, evaluatedReleaseStamps } from './helpers/review-evaluation-fixtures.mjs';
import { assertHistoryArchives, hashEvidence, readEvidenceFile } from './helpers/review-evidence-archives.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const json = (directory, path) => JSON.parse(readEvidenceFile(directory, path));
const assertionText = (bytes) => bytes.toString('utf8').replace(/^---\n[\s\S]*?\n---\n/, '').trim();

test('historical evidence requires both archives and rejects removed, changed or extra artifacts', () => {
  const directory = mkdtempSync(join(tmpdir(), 'qodo-required-history-'));
  const manifest = { history: {} };
  try {
    for (const iteration of [6, 7]) {
      const path = `history/iteration-${iteration}`;
      mkdirSync(join(directory, path), { recursive: true });
      writeFileSync(join(directory, path, 'response.md'), 'Original response\n');
      const archive = `${JSON.stringify({ artifacts: { 'response.md': hashEvidence('Original response\n') } })}\n`;
      writeFileSync(join(directory, path, 'archive.json'), archive);
      manifest.history[`iteration_${iteration}`] = { path: `${path}/archive.json`, sha256: hashEvidence(archive) };
    }
    assert.deepEqual(assertHistoryArchives(directory, manifest), { 6: 1, 7: 1 });
    for (const iteration of [6, 7]) {
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
    assert.deepEqual(assertHistoryArchives(directory, manifest), { 6: 1, 7: 1 });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('focused MCP collection evidence matches its explicit scope, immutable inputs and original judgments', () => {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-mcp-collection');
  const manifest = json(evidenceRoot, 'manifest.json');
  const primary = json(join(root, 'test/fixtures/qodo-review-behavior'), 'manifest.json');
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.method, 'fresh-native-agents-with-anonymous-final-answer-grading');
  assert.deepEqual(manifest.evaluated_cases, ['mcp-collection']);
  assert.deepEqual(manifest.cases.map(({ name }) => name), manifest.evaluated_cases);
  assert.equal(manifest.input_cases.length, 8);
  assert.deepEqual(manifest.input_cases.map(({ name }) => name).sort(),
    readdirSync(join(root, 'evals/qodo-review'), { withFileTypes: true })
      .filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort());
  for (const item of manifest.input_cases) {
    const directory = join(root, 'evals/qodo-review', item.name);
    assert.equal(hashEvidence(readEvidenceFile(directory, 'case.yaml')), item.case_sha256);
    assert.equal(hashEvidence(readEvidenceFile(directory, 'prompt.md')), item.prompt_sha256);
    assert.deepEqual(item.assertions.map(({ file }) => file),
      readdirSync(join(directory, 'graders')).filter((name) => name.endsWith('.md')).sort());
    for (const grader of item.assertions)
      assert.equal(hashEvidence(readEvidenceFile(directory, `graders/${grader.file}`)), grader.sha256);
  }
  assert.deepEqual(manifest.snapshots.baseline.fingerprints, primary.snapshots.baseline.fingerprints);
  assert.equal(manifest.snapshots.baseline.source_commit, primary.snapshots.baseline.source_commit);
  const version = json(root, 'distribution/catalog.json').skills.find(({ name }) => name === 'qodo-review').version;
  const skill = join(root, 'skills/qodo-review'), snapshot = manifest.snapshots.candidate;
  assert.deepEqual(Object.keys(snapshot.fingerprints).sort(),
    ['SKILL.md', ...readdirSync(join(skill, 'references')).filter((name) => name.endsWith('.md'))
      .map((name) => `references/${name}`)].sort());
  for (const [path, expected] of Object.entries(snapshot.fingerprints)) {
    const bytes = readEvidenceFile(skill, path);
    const evaluated = path === 'SKILL.md'
      ? evaluatedReleaseStamps(bytes.toString('utf8'), version, snapshot.release_metadata_version) : bytes;
    assert.equal(hashEvidence(evaluated), expected, `Stale supplemental instruction: ${path}`);
  }
  const item = manifest.cases[0], fixture = join(root, 'evals/qodo-review', item.name);
  assert.deepEqual(item, { ...manifest.input_cases.find(({ name }) => name === item.name), runs: item.runs });
  assert.match(readEvidenceFile(fixture, 'prompt.md').toString(), /allowed_tools: \[Read, Glob, Grep, Skill\]/);
  const assertions = item.assertions.map(({ file }) =>
    assertionText(readEvidenceFile(fixture, `graders/${file}`)));
  assert.equal(assertions.length, 5);
  const scores = {};
  for (const configuration of ['candidate', 'baseline']) {
    const run = item.runs[configuration];
    assert.deepEqual(Object.keys(run.artifacts).sort(), [run.response, run.grading, run.provenance].sort());
    for (const [path, hash] of Object.entries(run.artifacts))
      assert.equal(hashEvidence(readEvidenceFile(evidenceRoot, path)), hash, path);
    const grade = json(evidenceRoot, run.grading);
    scores[configuration] = { passed: assertGrade(grade, assertions, configuration === 'candidate'), total: 5 };
    const provenance = json(evidenceRoot, run.provenance);
    assertFixtureProvenance(provenance, { fixture_source_commit: manifest.fixture_source_commit, cases: manifest.input_cases });
    assert.deepEqual(provenance.fixture_fingerprints, manifest.fixture_fingerprints);
    assert.equal(provenance.source_commit, manifest.snapshots[configuration].source_commit);
    assert.deepEqual(provenance.fingerprints, manifest.snapshots[configuration].fingerprints);
    assert.equal(provenance.response_sha256, hashEvidence(readEvidenceFile(evidenceRoot, run.response)));
  }
  assert.deepEqual(manifest.scores, scores);
});

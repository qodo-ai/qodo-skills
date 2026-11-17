import assert from 'node:assert/strict';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { assertFixtureProvenance, fixtureFingerprints } from './helpers/review-evaluation-fixtures.mjs';
import { assertHistoryArchives, hashEvidence, readEvidenceFile } from './helpers/review-evidence-archives.mjs';
import { assertEvidenceScopes, caseInputs } from './helpers/review-evidence-scopes.mjs';

function fixture() {
  const makeCase = (name, stamp) => ({ name, case_sha256: stamp.repeat(64), prompt_sha256: stamp.repeat(64),
    assertions: [{ file: '01-check.md', sha256: stamp.repeat(64) }],
    runs: Object.fromEntries(['candidate', 'baseline'].map((configuration) => [configuration, {
      response: `${name}/${configuration}/response.md`, grading: `${name}/${configuration}/grading.json`,
      provenance: `${name}/${configuration}/provenance.json`, artifacts: { identity: stamp.repeat(64) },
    }])) });
  const snapshots = Object.fromEntries(['candidate', 'baseline'].map((configuration, index) => [configuration,
    { source_commit: String(index + 1).repeat(40), fingerprints: { 'SKILL.md': String(index + 1).repeat(64) } }]));
  const alpha = makeCase('alpha', 'a'), betaOld = makeCase('beta', 'b'), betaNew = makeCase('beta', 'c');
  const record = (stamp, cases, input_cases = cases) => ({ schema_version: 1,
    method: 'fresh-native-agents-with-anonymous-final-answer-grading', snapshots: structuredClone(snapshots),
    fixture_source_commit: stamp.repeat(40), cases, input_cases: input_cases.map(caseInputs),
    fixture_fingerprints: fixtureFingerprints(input_cases),
    configuration_labels: { candidate: 'with_skill', baseline: 'old_skill' },
    anonymous_grading_labels: Object.fromEntries(cases.map(({ name }) => [name, { candidate: 'A', baseline: 'B' }])),
  });
  const records = { retained: record('3', [alpha, betaOld]), focused: record('4', [betaNew], [alpha, betaNew]) };
  const manifest = { schema_version: 2, method: 'scoped-native-agents-with-anonymous-final-answer-grading',
    snapshots, cases: [structuredClone({ ...alpha, evidence_scope: 'retained' }),
      structuredClone({ ...betaNew, evidence_scope: 'focused' })],
    evidence_scopes: [
      { id: 'retained', cases: ['alpha'], record: { path: 'retained', sha256: '1'.repeat(64) },
        archive: { path: 'retained/archive.json', sha256: '1'.repeat(64) } },
      { id: 'focused', cases: ['beta'], record: { path: 'focused', sha256: '2'.repeat(64) },
        archive: { path: 'focused/archive.json', sha256: '2'.repeat(64) } },
    ] };
  return { records, manifest, check: () => assertEvidenceScopes(manifest, ({ path }) => records[path]) };
}

test('disjoint scopes retain original full inputs while selected cases match current fixtures', () => {
  const { records, manifest, check } = fixture(), selected = check();
  assert.deepEqual([...selected.keys()].sort(), ['alpha', 'beta']);
  assert.notDeepEqual(records.retained.input_cases[1], manifest.cases[1]);
  assert.equal(selected.get('alpha').record.fixture_source_commit, '3'.repeat(40));
  assert.equal(selected.get('beta').record.fixture_source_commit, '4'.repeat(40));
});

test('scoped coverage rejects gaps, overlaps, duplicates and unsupported memberships', () => {
  const changes = [
    ({ manifest }) => manifest.evidence_scopes.pop(),
    ({ manifest }) => manifest.evidence_scopes[1].cases.push('alpha'),
    ({ manifest }) => manifest.evidence_scopes[0].cases.push('alpha'),
    ({ manifest }) => manifest.evidence_scopes[0].cases.push('unknown'),
    ({ manifest }) => { manifest.evidence_scopes[0].cases = []; },
    ({ manifest }) => { manifest.evidence_scopes = []; },
    ({ manifest }) => { manifest.evidence_scopes[1].id = 'retained'; },
    ({ manifest }) => { manifest.cases[0].evidence_scope = 'focused'; },
    ({ manifest }) => manifest.cases.push(structuredClone(manifest.cases[0])),
    ({ manifest }) => { manifest.fixture_source_commit = '5'.repeat(40); },
    ({ manifest }) => { delete manifest.evidence_scopes[0].archive; },
  ];
  for (const change of changes) {
    const value = fixture();
    change(value);
    assert.throws(value.check);
  }
});

test('scopes reject stale selected inputs, changed instructions, relabeled runs and missing input maps', () => {
  const changes = [
    ({ manifest }) => { manifest.cases[0].prompt_sha256 = '0'.repeat(64); },
    ({ records }) => { records.retained.snapshots.candidate.source_commit = '5'.repeat(40); },
    ({ records }) => { records.retained.snapshots.baseline.fingerprints['SKILL.md'] = '0'.repeat(64); },
    ({ records }) => { records.retained.cases = records.retained.cases.filter(({ name }) => name !== 'alpha'); },
    ({ manifest }) => { manifest.cases[0].runs.candidate.response = 'beta/candidate/response.md'; },
    ({ manifest }) => { manifest.cases[0].runs.baseline.artifacts.identity = '0'.repeat(64); },
    ({ records }) => { delete records.retained.fixture_fingerprints['beta/prompt.md']; },
    ({ records }) => { records.retained.input_cases.pop(); },
    ({ records }) => { records.focused.anonymous_grading_labels.beta.baseline = 'A'; },
    ({ records }) => { records.focused.configuration_labels.candidate = 'baseline'; },
  ];
  for (const change of changes) {
    const value = fixture();
    change(value);
    assert.throws(value.check);
  }
});

test('trimming unselected captured inputs cannot rebind old provenance to a scoped selection', () => {
  const { records, check } = fixture(), record = records.retained;
  const provenance = { fixture_source_commit: record.fixture_source_commit,
    fixture_fingerprints: structuredClone(record.fixture_fingerprints) };
  assertFixtureProvenance(provenance, record);
  record.input_cases.pop();
  record.fixture_fingerprints = fixtureFingerprints(record.input_cases);
  check(); // The selected alpha is unchanged, but the actual capture still contains beta.
  assert.throws(() => assertFixtureProvenance(provenance, record), /Recorded fixture inputs/);
});

test('original iteration12 failure and full captured maps remain mandatory and inspectable', () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const directory = join(root, 'test/fixtures/qodo-review-behavior');
  const json = (path) => JSON.parse(readEvidenceFile(directory, path));
  assert.equal(assertHistoryArchives(directory, json('manifest.json'))[12], 147);
  const record = json('history/iteration-12/manifest.json');
  assert.deepEqual(record.scores, { candidate: { passed: 40, total: 41 }, baseline: { passed: 40, total: 41 } });
  assert.equal(Object.keys(record.fixture_fingerprints).length, 57);
  assert.deepEqual(record.fixture_fingerprints, fixtureFingerprints(record.cases));
  for (const [configuration, failedCase] of Object.entries({
    candidate: 'followup-and-finding-state', baseline: 'compatibility-boundaries',
  })) {
    const run = record.cases.find(({ name }) => name === failedCase).runs[configuration];
    const base = 'history/iteration-12/';
    const grade = json(base + run.grading), provenance = json(base + run.provenance);
    assert.equal(grade.summary.failed, 1);
    assertFixtureProvenance(provenance, record);
    assert.equal(provenance.response_sha256, hashEvidence(readEvidenceFile(directory, base + run.response)));
  }
});

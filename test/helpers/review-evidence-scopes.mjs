import assert from 'node:assert/strict';
import { fixtureFingerprints } from './review-evaluation-fixtures.mjs';

export const caseInputs = ({ name, case_sha256, prompt_sha256, assertions }) =>
  ({ name, case_sha256, prompt_sha256, assertions });

// Records retain the full captured inputs, including unselected historical cases.
// Only the selected cases must match today's fixtures; their runs must remain exact.
export function assertEvidenceScopes(manifest, loadRecord) {
  assert.equal(manifest.schema_version, 2);
  assert.equal(manifest.method, 'scoped-native-agents-with-anonymous-final-answer-grading');
  assert.equal(manifest.fixture_source_commit, undefined, 'Scoped evidence has no unified fixture commit');
  const current = new Map(manifest.cases.map((item) => [item.name, item]));
  assert.equal(current.size, manifest.cases.length, 'Duplicate current case');
  assert.ok(current.size, 'Current cases are required');
  assert.ok(Array.isArray(manifest.evidence_scopes) && manifest.evidence_scopes.length, 'Evidence scopes are required');
  const scopes = new Set(), selected = new Map();
  for (const scope of manifest.evidence_scopes) {
    assert.match(scope.id, /^[a-z][a-z0-9-]*$/);
    assert.ok(!scopes.has(scope.id), 'Duplicate evidence scope');
    scopes.add(scope.id);
    assert.ok(Array.isArray(scope.cases) && scope.cases.length, 'Empty evidence scope');
    assert.match(scope.record.sha256, /^[a-f0-9]{64}$/);
    const record = loadRecord(scope.record);
    assert.equal(record.schema_version, 1);
    assert.equal(record.method, 'fresh-native-agents-with-anonymous-final-answer-grading');
    assert.match(record.fixture_source_commit, /^[a-f0-9]{40}$/);
    for (const configuration of ['candidate', 'baseline']) {
      assert.deepEqual(record.snapshots[configuration], manifest.snapshots[configuration],
        'Scope instructions differ from selected instructions');
    }
    assert.deepEqual(record.configuration_labels, { candidate: 'with_skill', baseline: 'old_skill' });
    assert.deepEqual(record.fixture_fingerprints, fixtureFingerprints(record.input_cases ?? record.cases),
      'Scope must retain the complete captured input map');
    const recorded = new Map(record.cases.map((item) => [item.name, item]));
    assert.equal(recorded.size, record.cases.length, 'Duplicate recorded case');
    const captured = new Map((record.input_cases ?? record.cases).map((item) => [item.name, item]));
    for (const name of scope.cases) {
      assert.ok(current.has(name), 'Scope selects an unknown current case');
      assert.ok(!selected.has(name), 'Overlapping evidence scopes');
      const item = current.get(name), original = recorded.get(name);
      assert.ok(original, 'Selected case is absent from its original record');
      assert.equal(item.evidence_scope, scope.id, 'Current case names the wrong scope');
      assert.deepEqual(caseInputs(original), caseInputs(captured.get(name)), 'Recorded inputs differ from captured inputs');
      assert.deepEqual(caseInputs(item), caseInputs(original), 'Selected current inputs differ from their original scope');
      assert.deepEqual(item.runs, original.runs, 'Selected run/artifact identities differ from their original scope');
      const labels = record.anonymous_grading_labels[name];
      assert.ok(labels && ['A', 'B'].includes(labels.candidate) && ['A', 'B'].includes(labels.baseline)
        && labels.candidate !== labels.baseline, 'Invalid anonymous grading labels');
      selected.set(name, { record, reference: scope.record });
    }
  }
  assert.deepEqual([...selected.keys()].sort(), [...current.keys()].sort(), 'Missing current case coverage');
  return selected;
}

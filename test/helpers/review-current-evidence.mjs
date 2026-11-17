import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { inputPath } from '../../scripts/eval-review-skill.mjs';
import { assertFixtureProvenance, assertGrade, assertRunIdentity, assertRunPaths, evaluatedReleaseStamps } from './review-evaluation-fixtures.mjs';
import { assertArtifactArchive, assertHistoryArchives, hashEvidence as sha256 } from './review-evidence-archives.mjs';
import { assertEvidenceScopes } from './review-evidence-scopes.mjs';

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

export function fixtureFile(directory, path, boundary = repository) {
  assert.ok(typeof path === 'string' && path && !path.includes('\\') && !path.includes(':')
    && !path.split('/').some((part) => ['', '.', '..'].includes(part)), 'Unsafe evidence path');
  return readFileSync(inputPath(boundary, join(directory, path), 'file'));
}

export function assertCaseInputs(directory, item, boundary = repository) {
  assert.equal(sha256(fixtureFile(directory, 'case.yaml', boundary)), item.case_sha256, `Stale case setup: ${item.name}`);
  assert.equal(sha256(fixtureFile(directory, 'prompt.md', boundary)), item.prompt_sha256, `Stale case prompt: ${item.name}`);
}

export function assertBaselineSnapshot(evidenceRoot, snapshot) {
  assert.match(snapshot.source_commit, /^[a-f0-9]{40}$/);
  const bytes = fixtureFile(evidenceRoot, snapshot.git_objects.path);
  assert.equal(sha256(bytes), snapshot.git_objects.sha256, 'Baseline object snapshot changed');
  const archive = JSON.parse(bytes);
  assert.equal(archive.schema_version, 1);
  assert.equal(archive.source_commit, snapshot.source_commit);
  const temporary = mkdtempSync(join(tmpdir(), 'qodo-evidence-baseline-'));
  try {
    // Only a temporary object store is written; user refs/hooks/signing are untouched.
    const git = (args, input, encoding = 'utf8') => execFileSync('git', args, {
      cwd: temporary, input, encoding, stdio: ['pipe', 'pipe', 'pipe'],
      env: Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^GIT_/i.test(name))),
    });
    git(['init', '--bare', '--quiet']);
    for (const object of archive.objects) {
      assert.ok(['commit', 'tree', 'blob'].includes(object.type));
      assert.match(object.sha1, /^[a-f0-9]{40}$/);
      const content = object.type === 'tree' ? Buffer.concat(object.entries.map((entry) => {
        assert.match(entry.mode, /^(?:040000|100644|100755|120000|160000)$/);
        assert.ok(entry.name && !/[/\0]/.test(entry.name));
        assert.match(entry.sha1, /^[a-f0-9]{40}$/);
        return Buffer.concat([Buffer.from(`${entry.mode.replace(/^0+/, '')} ${entry.name}\0`),
          Buffer.from(entry.sha1, 'hex')]);
      })) : Buffer.from(object.content_utf8);
      assert.equal(git(['hash-object', '-w', '-t', object.type, '--stdin'], content).trim(), object.sha1,
        'Baseline Git object identity changed');
    }
    const commit = snapshot.source_commit;
    assert.equal(git(['rev-parse', '--verify', `${commit}^{commit}`]).trim(), commit);
    const prefix = 'skills/qodo-review/';
    const entries = git(['ls-tree', '-r', '-z', commit, '--', prefix]).split('\0').filter(Boolean);
    const actual = {};
    for (const entry of entries) {
      const [header, path] = entry.split('\t');
      const name = path.slice(prefix.length);
      if (name !== 'SKILL.md' && !(name.startsWith('references/') && name.endsWith('.md'))) continue;
      assert.match(header, /^100(?:644|755) blob [a-f0-9]+$/, 'Baseline inputs must be regular Git files');
      actual[name] = sha256(git(['show', `${commit}:${path}`], undefined, 'buffer'));
    }
    assert.ok(actual['SKILL.md'], 'Baseline commit must contain the selected Skill');
    assert.deepEqual(snapshot.fingerprints, actual, 'Baseline fingerprints do not match its immutable commit');
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

export function assertCurrentEvidence(root, { skill, version, references, text }) {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-behavior');
  const manifest = JSON.parse(fixtureFile(evidenceRoot, 'manifest.json'));
  assert.equal(manifest.cases.length, 8);
  assertBaselineSnapshot(evidenceRoot, manifest.snapshots.baseline);
  assert.deepEqual(assertHistoryArchives(evidenceRoot, manifest),
    { 6: 40, 7: 96, 8: 104, 9: 74, 10: 121, 11: 122, 12: 147 });
  for (const artifactMap of [manifest.adjudication?.artifacts, manifest.grading_evidence?.artifacts]) {
    for (const [path, hash] of Object.entries(artifactMap ?? {}))
      assert.equal(sha256(fixtureFile(evidenceRoot, path)), hash, path);
  }
  assert.deepEqual(Object.keys(manifest.snapshots.candidate.fingerprints).sort(),
    ['SKILL.md', ...references.map((name) => `references/${name}`)].sort());
  assert.deepEqual(manifest.cases.map((item) => item.name).sort(),
    readdirSync(join(root, 'evals/qodo-review'), { withFileTypes: true })
      .filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort());
  for (const [name, expected] of Object.entries(manifest.snapshots.candidate.fingerprints)) {
    const current = fixtureFile(skill, name);
    const evaluated = name === 'SKILL.md' ? evaluatedReleaseStamps(current.toString('utf8'),
      version, manifest.snapshots.candidate.release_metadata_version) : current;
    assert.equal(sha256(evaluated), expected, `Stale instruction evidence: ${name}`);
  }
  const releaseOnly = text.replace(`  version: "${version}"`, '  version: "999.0.0"')
    .replaceAll(`--skill-version ${version} --distribution`, '--skill-version 999.0.0 --distribution');
  assert.equal(evaluatedReleaseStamps(releaseOnly, '999.0.0', version), text);
  assert.notEqual(evaluatedReleaseStamps(`${releaseOnly}\nChanged behavior.\n`, '999.0.0', version), text);
  const selections = assertEvidenceScopes(manifest, (reference) => {
    const scope = manifest.evidence_scopes.find((entry) => entry.record === reference);
    assertArtifactArchive(evidenceRoot, scope.archive, dirname(reference.path), scope.id);
    const bytes = fixtureFile(evidenceRoot, reference.path);
    assert.equal(sha256(bytes), reference.sha256, 'Scope record identity changed');
    return JSON.parse(bytes);
  });
  const scores = { candidate: { passed: 0, total: 0 }, baseline: { passed: 0, total: 0 } };
  let assertionCount = 0;
  for (const item of manifest.cases) {
    const fixture = join(root, 'evals/qodo-review', item.name);
    assertCaseInputs(fixture, item);
    const graders = readdirSync(inputPath(root, join(fixture, 'graders'), 'directory')).sort();
    assert.deepEqual(item.assertions.map((entry) => entry.file), graders);
    for (const grader of item.assertions)
      assert.equal(sha256(fixtureFile(join(fixture, 'graders'), grader.file)), grader.sha256);
    const assertions = graders.map((file) => fixtureFile(join(fixture, 'graders'), file)
      .toString('utf8').replace(/^---\n[\s\S]*?\n---\n/, '').trim());
    assertionCount += assertions.length;
    const { record, reference } = selections.get(item.name);
    const originalDirectory = dirname(join(evidenceRoot, reference.path));
    for (const configuration of ['candidate', 'baseline']) {
      const run = item.runs[configuration];
      assertRunPaths(run, item.name, configuration);
      assert.deepEqual(Object.keys(run.artifacts).sort(), [run.response, run.grading, run.provenance].sort());
      for (const [path, hash] of Object.entries(run.artifacts)) {
        const bytes = fixtureFile(evidenceRoot, path);
        assert.equal(sha256(bytes), hash, path);
        assert.deepEqual(bytes, fixtureFile(originalDirectory, path), 'Selected captured artifact bytes changed');
      }
      const response = fixtureFile(evidenceRoot, run.response);
      const grade = JSON.parse(fixtureFile(evidenceRoot, run.grading));
      const provenance = JSON.parse(fixtureFile(evidenceRoot, run.provenance));
      const passed = assertGrade(grade, assertions, configuration === 'candidate', {
        response: response.toString('utf8'), label: record.anonymous_grading_labels[item.name][configuration],
      });
      assertRunIdentity(provenance, item.name, record.configuration_labels[configuration]);
      assertFixtureProvenance(provenance, record);
      assert.deepEqual(provenance.fixture_fingerprints, record.fixture_fingerprints);
      assert.equal(provenance.source_commit, manifest.snapshots[configuration].source_commit);
      assert.deepEqual(provenance.fingerprints, manifest.snapshots[configuration].fingerprints);
      assert.equal(provenance.response_sha256, sha256(response));
      assert.match(provenance.session_id, /^ses_[a-zA-Z0-9]+$/);
      assert.match(grade.grader_provenance.session_id, /^ses_[a-zA-Z0-9]+$/);
      scores[configuration].passed += passed;
      scores[configuration].total += assertions.length;
    }
  }
  assert.equal(assertionCount, 41);
  assert.equal(scores.candidate.passed, 41);
  assert.deepEqual(manifest.scores, scores);
}

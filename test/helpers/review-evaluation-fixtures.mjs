import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

export function assertFixtureProvenance(provenance, manifest) {
  assert.match(manifest.fixture_source_commit, /^[a-f0-9]{40}$/);
  assert.equal(provenance.fixture_source_commit, manifest.fixture_source_commit);
  const inputs = Object.fromEntries(manifest.cases.flatMap((item) => [
    [`${item.name}/case.yaml`, item.case_sha256], [`${item.name}/prompt.md`, item.prompt_sha256],
    ...item.assertions.map(({ file, sha256 }) => [`${item.name}/graders/${file}`, sha256]),
  ]));
  assert.deepEqual(provenance.fixture_fingerprints, inputs, 'Recorded fixture inputs differ from current evidence');
}

export function assertGrade(grade, assertions, candidate = false) {
  assert.deepEqual(grade.expectations.map((entry) => entry.text), assertions);
  assert.ok(grade.expectations.every((entry) => typeof entry.passed === 'boolean'),
    'Every assertion verdict must be a boolean');
  const passed = grade.expectations.filter((entry) => entry.passed === true).length;
  assert.deepEqual(grade.summary, { passed, failed: assertions.length - passed,
    total: assertions.length, pass_rate: passed / assertions.length });
  assert.ok(grade.expectations.every((entry) => typeof entry.evidence === 'string' && entry.evidence.trim()));
  if (candidate) assert.ok(grade.expectations.every((entry) => entry.passed === true), 'Candidate evidence failed');
  return passed;
}

export function evaluatedReleaseStamps(body, currentVersion, evaluatedVersion) {
  // Release preparation changes only these two stamps; original fingerprints remain unchanged.
  assert.ok(body.includes(`  version: "${currentVersion}"`), 'Current metadata must match the release catalog');
  return body.replace(`  version: "${currentVersion}"`, `  version: "${evaluatedVersion}"`)
    .replaceAll(`--skill-version ${currentVersion} --distribution`,
      `--skill-version ${evaluatedVersion} --distribution`);
}

export function createEvaluationRepository(parent, skill, evaluations) {
  const source = join(parent, 'source');
  mkdirSync(join(source, 'skills'), { recursive: true });
  mkdirSync(join(source, 'evals'));
  cpSync(skill, join(source, 'skills/qodo-review'), { recursive: true });
  cpSync(evaluations, join(source, 'evals/qodo-review'), { recursive: true });
  const git = (args, input) => execFileSync('git', args, { cwd: source, encoding: 'utf8', input,
    stdio: ['pipe', 'pipe', 'pipe'] }).trim();
  git(['init', '--quiet']);
  const commit = () => {
    git(['add', '--all']);
    const tree = git(['write-tree']);
    // Synthetic test object only; no user commit or signing configuration is changed.
    const sha = git(['hash-object', '-w', '-t', 'commit', '--stdin'],
      `tree ${tree}\nauthor Fixture <fixture@qodo.invalid> 0 +0000\ncommitter Fixture <fixture@qodo.invalid> 0 +0000\n\nEvaluation fixture\n`);
    git(['update-ref', 'HEAD', sha]);
    return sha;
  };
  return { source, git, commit, head: commit() };
}

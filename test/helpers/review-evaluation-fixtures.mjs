import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

export function assertFixtureProvenance(provenance, manifest) {
  assert.match(manifest.fixture_source_commit, /^[a-f0-9]{40}$/);
  assert.equal(provenance.fixture_source_commit, manifest.fixture_source_commit);
  const inputs = Object.fromEntries((manifest.input_cases ?? manifest.cases).flatMap((item) => [
    [`${item.name}/case.yaml`, item.case_sha256], [`${item.name}/prompt.md`, item.prompt_sha256],
    ...item.assertions.map(({ file, sha256 }) => [`${item.name}/graders/${file}`, sha256]),
  ]));
  assert.deepEqual(provenance.fixture_fingerprints, inputs, 'Recorded fixture inputs differ from current evidence');
}

export function assertGrade(grade, assertions, candidate = false, { response, label = 'response' } = {}) {
  assert.ok(Array.isArray(assertions) && assertions.length > 0, 'Every evaluated case needs at least one assertion');
  assert.deepEqual(grade.expectations.map((entry) => entry.text), assertions);
  assert.ok(grade.expectations.every((entry) => typeof entry.passed === 'boolean'),
    'Every assertion verdict must be a boolean');
  const passed = grade.expectations.filter((entry) => entry.passed === true).length;
  assert.deepEqual(grade.summary, { passed, failed: assertions.length - passed,
    total: assertions.length, pass_rate: passed / assertions.length });
  assert.ok(typeof response === 'string' && response.trim(), 'Recorded response text is required for citation validation');
  assert.ok(['response', 'A', 'B'].includes(label), 'Unknown response citation label');
  const lineCount = response.trimEnd().split(/\r?\n/).length;
  for (const entry of grade.expectations) {
    assert.ok(typeof entry.evidence === 'string' && entry.evidence.trim(), 'Every assertion needs evidence');
    const citations = [...entry.evidence.matchAll(/\b(response|[AB])\.md:(\d+)(?:[-–](\d+))?/g)]
      .filter((match) => match[1] === 'response' || match[1] === label);
    assert.ok(citations.length, 'Every assertion needs a citation to its recorded response');
    for (const [, , start, end = start] of citations) {
      assert.ok(Number(start) >= 1 && Number(start) <= Number(end) && Number(end) <= lineCount,
        'Response citation line range is invalid');
    }
  }
  if (candidate) assert.ok(grade.expectations.every((entry) => entry.passed === true), 'Candidate evidence failed');
  return passed;
}

export function assertRunPaths(run, caseName, configuration) {
  assert.match(caseName, /^[a-z][a-z0-9-]*$/);
  assert.ok(['candidate', 'baseline'].includes(configuration));
  const prefix = `${caseName}/${configuration}`;
  for (const [key, file] of Object.entries({ response: 'response.md', grading: 'grading.json', provenance: 'provenance.json' }))
    assert.equal(run[key], `${prefix}/${file}`, 'Artifact path must match its case and configuration');
}

export function assertRunIdentity(provenance, caseName, configuration) {
  assert.equal(provenance.evaluated_case, caseName, 'Recorded case identity differs');
  assert.equal(provenance.configuration, configuration, 'Recorded configuration differs');
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

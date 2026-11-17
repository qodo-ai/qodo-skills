import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, renameSync,
  rmSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { inputPath, main, prepareReviewEvaluation, readGitEvaluationFiles,
  requireEvaluationSupport } from '../scripts/eval-review-skill.mjs';
import { assertFixtureProvenance, assertGrade, assertRunIdentity, assertRunPaths, createEvaluationRepository, evaluatedReleaseStamps } from './helpers/review-evaluation-fixtures.mjs';
import { assertHistoryArchives } from './helpers/review-evidence-archives.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const skill = join(root, 'skills/qodo-review');
const text = readFileSync(join(skill, 'SKILL.md'), 'utf8');
const catalog = JSON.parse(readFileSync(join(root, 'distribution/catalog.json'), 'utf8'));
const version = catalog.skills.find(({ name }) => name === 'qodo-review').version;
const references = readdirSync(join(skill, 'references')).filter((name) => name.endsWith('.md'));
const markdown = [join(skill, 'SKILL.md'), ...references.map((name) => join(skill, 'references', name))];
const readReference = (name) => readFileSync(join(skill, 'references', name), 'utf8');
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const evaluationRepository = (parent) => createEvaluationRepository(parent, skill, join(root, 'evals/qodo-review'));

function fixtureFile(directory, path, boundary = root) {
  assert.ok(typeof path === 'string' && path && !path.includes('\\') && !path.includes(':')
    && !path.split('/').some((part) => ['', '.', '..'].includes(part)), 'Unsafe evidence path');
  return readFileSync(inputPath(boundary, join(directory, path), 'file'));
}

function assertCaseInputs(directory, item, boundary = root) {
  assert.equal(sha256(fixtureFile(directory, 'case.yaml', boundary)), item.case_sha256, `Stale case setup: ${item.name}`);
  assert.equal(sha256(fixtureFile(directory, 'prompt.md', boundary)), item.prompt_sha256, `Stale case prompt: ${item.name}`);
}

function assertBaselineSnapshot(evidenceRoot, snapshot) {
  assert.match(snapshot.source_commit, /^[a-f0-9]{40}$/);
  const bytes = fixtureFile(evidenceRoot, snapshot.git_objects.path);
  assert.equal(sha256(bytes), snapshot.git_objects.sha256, 'Baseline object snapshot changed');
  const archive = JSON.parse(bytes);
  assert.equal(archive.schema_version, 1);
  assert.equal(archive.source_commit, snapshot.source_commit);
  const temporary = mkdtempSync(join(tmpdir(), 'qodo-evidence-baseline-'));
  try {
    // Readable Git objects keep the exact signed source inspectable after squash merges.
    // Only this temporary object store is written; no refs, hooks or signing settings are changed.
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
  assert.match(text, /not another retry per symptom/);
  assert.match(text, /QODO_UPDATE_BASE_URL/);
  assert.match(text, /never print its value/);
  assert.match(text, /show the returned message and hint unchanged/);
  assert.match(execution, /Run the resolved invocation with only `--version`/);
  assert.match(text, /If neither installed invocation works, stop the CLI path/);
  assert.match(text, /Never invent a digest, pipe an installer into a shell/);
  assert.match(text, /Every updater route, including ordinary update, needs a successful check/);
  assert.match(text, /Failure, no update or an incompatible target stops/);
  assert.match(text, /In every command example, replace `qodo` with that resolved invocation/);
  assert.match(readReference('mcp-review.md'), /tested local collector/);
  assert.match(text, /Reject mismatched operation\/snapshot associations and incomplete or noncontiguous result pages/);
  for (const field of ['operation_id', 'offset_bytes', 'total_chunks', 'next_cursor'])
    assert.ok(readReference('mcp-review.md').includes(field));
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
  assert.match(triage, /_meta\["io\.qodo\/idempotency-key"\]/);
  assert.match(triage, /do not submit an unprotected write/);
  assert.match(text, /A HEAD SHA alone does not identify a dirty snapshot/);
  assert.match(text, /Report status persistence separately from downstream synchronization/);
  assert.match(triage, /the status is stored but downstream synchronization is incomplete/);
  assert.match(text, /finding\/checkpoint persistence and local-to-PR handoff separately/);
  for (const group of ['compatibility-boundaries', 'followup-and-finding-state',
    'milestone-and-final-scope', 'recovery-and-readiness', 'fallback-invocation', 'recovery-policy-guards',
    'mcp-local-triage']) {
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
    const fixture = evaluationRepository(parent);
    const staged = prepareReviewEvaluation({ root: fixture.source, parent });
    assert.equal(readFileSync(join(staged.plugin, 'skills/qodo-review/SKILL.md'), 'utf8'), text);
    assert.equal(statSync(join(staged.plugin, 'skills/qodo-review/SKILL.md')).mode & 0o222, 0);
    assert.equal(staged.manifest.source_kind, 'immutable Git commit');
    assert.equal(staged.manifest.source_commit, fixture.head);
    assert.equal(staged.manifest.fixture_source_commit, fixture.head);
    assert.equal(staged.manifest.cases.length, 8);
    assert.equal(Object.values(staged.manifest.assertions).reduce((sum, count) => sum + count, 0), 40);
    assert.ok(staged.args.includes('--no-publish') && staged.args.includes('--no-scaffold'));
    assert.ok(!staged.args.includes('--allow-real-servers') && !staged.args.includes('--trust-plugin'));
    assert.ok(!staged.args.includes('--json'), 'Machine mode must not suppress a first-run trust prompt');
    const boundary = readFileSync(join(staged.plugin, 'evals/compatibility-boundaries/prompt.md'), 'utf8');
    for (const version of ['1.6.0', '"custom build"', '2.0.0', '2.3.1']) assert.ok(boundary.includes(version));
    assert.ok(boundary.includes('summary, not notes') && boundary.includes('decisions=['));
    assert.throws(() => prepareReviewEvaluation({ root: fixture.source, parent: fixture.source }), /outside the source repository/);
    assert.equal(existsSync(join(staged.directory, 'result.json')), false, 'Staging must not run a model');
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test('paid evaluator execution requires the tool-exclusion capability while staging remains offline', () => {
  assert.throws(() => requireEvaluationSupport('Usage: claude plugin eval [--runs]'), /2\.1\.299/);
  assert.doesNotThrow(() => requireEvaluationSupport('Usage: claude plugin eval --disallow-tools <tools>'));
});

test('committed model inputs are unchanged by checkout replacements and dirty inputs stop staging', (t) => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-input-test-'));
  try {
    const fixture = evaluationRepository(parent), { source } = fixture;
    const original = readGitEvaluationFiles(source, fixture.head, 'evals/qodo-review/');
    const outside = join(parent, 'outside.txt');
    writeFileSync(outside, 'private-fixture-marker');
    for (const path of ['skills/qodo-review/SKILL.md',
      'skills/qodo-review/references/review-turn-context.md',
      'evals/qodo-review/compatibility-boundaries/prompt.md',
      'evals/qodo-review/compatibility-boundaries/case.yaml']) {
      const target = join(source, path), backup = `${target}.backup`;
      renameSync(target, backup);
      try { symlinkSync(outside, target); } catch (error) {
        if (['EPERM', 'ENOTSUP'].includes(error.code)) { t.skip('Host cannot create test symlinks'); return; }
        throw error;
      }
      assert.deepEqual(readGitEvaluationFiles(source, fixture.head, 'evals/qodo-review/'), original);
      assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
      rmSync(target); renameSync(backup, target);
    }
    const refs = join(source, 'skills/qodo-review/references');
    renameSync(refs, `${refs}.backup`);
    symlinkSync(`${refs}.backup`, refs, 'dir');
    assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
    rmSync(refs); renameSync(`${refs}.backup`, refs);
    const prompt = join(source, 'evals/qodo-review/compatibility-boundaries/prompt.md');
    rmSync(prompt); symlinkSync(outside, prompt);
    fixture.commit();
    assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /regular Git file/);
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test('immutable evaluation refs reject hex-named branches and abbreviated object IDs', () => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-ref-test-'));
  try {
    const fixture = evaluationRepository(parent);
    fixture.git(['update-ref', 'refs/heads/deadbee', fixture.head]);
    for (const ref of ['deadbee', fixture.head.slice(0, 12)]) {
      assert.throws(() => prepareReviewEvaluation({ root: fixture.source, parent, ref }), /full 40-character/);
    }
    const hexBranch = 'a'.repeat(40);
    fixture.git(['update-ref', `refs/heads/${hexBranch}`, fixture.head]);
    assert.throws(() => prepareReviewEvaluation({ root: fixture.source, parent, ref: hexBranch }));
    const staged = prepareReviewEvaluation({ root: fixture.source, parent, ref: fixture.head });
    assert.equal(staged.manifest.source_commit, fixture.head);
    assert.equal(staged.manifest.fixture_source_commit, fixture.head);
  } finally { rmSync(parent, { recursive: true, force: true }); }
});

test('non-input edits do not block staging while selected additions, renames and index changes do', () => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-dirty-selection-'));
  try {
    const { source, head, git } = evaluationRepository(parent);
    for (const path of ['evals/qodo-review/README.md', 'evals/qodo-review/RESULTS.md',
      'skills/qodo-review/agents/openai.yaml']) writeFileSync(join(source, path), 'uncommitted non-input');
    const staged = prepareReviewEvaluation({ root: source, parent });
    assert.equal(staged.manifest.source_commit, head);
    assert.ok(!Object.keys(staged.manifest.fixture_fingerprints).some((path) => path.endsWith('README.md')));
    const extra = join(source, 'evals/qodo-review/compatibility-boundaries/graders/extra.md');
    writeFileSync(extra, 'new selected input');
    assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
    rmSync(extra);
    const prompt = 'evals/qodo-review/compatibility-boundaries/prompt.md';
    const original = readFileSync(join(source, prompt));
    git(['mv', prompt, 'evals/qodo-review/compatibility-boundaries/README.md']);
    assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
    writeFileSync(join(source, prompt), original);
    assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
  } finally { rmSync(parent, { recursive: true, force: true }); }
});

test('selected assume-unchanged and skip-worktree inputs fail closed without changing index flags', () => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-index-flags-'));
  try {
    const { source, head, git } = evaluationRepository(parent);
    const path = 'evals/qodo-review/compatibility-boundaries/prompt.md';
    const original = readFileSync(join(source, path));
    for (const flag of ['assume-unchanged', 'skip-worktree']) {
      git(['update-index', `--${flag}`, '--', path]);
      writeFileSync(join(source, path), 'hidden selected edit');
      assert.equal(git(['diff', '--name-only', head, '--', path]), '');
      const before = git(['ls-files', '-v', '--', path]);
      assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /assume-unchanged or skip-worktree/);
      assert.equal(git(['ls-files', '-v', '--', path]), before);
      writeFileSync(join(source, path), original);
      git(['update-index', `--no-${flag}`, '--', path]);
    }
  } finally { rmSync(parent, { recursive: true, force: true }); }
});

test('locally or globally ignored selected additions still stop evaluation staging', () => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-ignored-input-'));
  try {
    const { source, git } = evaluationRepository(parent);
    for (const [index, path] of ['compatibility-boundaries/graders/ignored.md', 'ignored-case/prompt.md'].entries()) {
      const relative = `evals/qodo-review/${path}`;
      const exclude = index === 0 ? join(source, '.git/info/exclude') : join(parent, 'global-excludes');
      writeFileSync(exclude, `${relative}\n`);
      if (index === 1) git(['config', 'core.excludesFile', exclude]);
      mkdirSync(dirname(join(source, relative)), { recursive: true });
      writeFileSync(join(source, relative), 'ignored selected addition');
      assert.equal(git(['ls-files', '--others', '--exclude-standard', '--', relative]), '');
      assert.equal(git(['check-ignore', relative]), relative);
      assert.throws(() => prepareReviewEvaluation({ root: source, parent }), /Commit the selected evaluation inputs/);
      rmSync(join(source, relative));
    }
    const nonInput = 'evals/qodo-review/ignored-case/README.md';
    writeFileSync(join(parent, 'global-excludes'), `${nonInput}\n`);
    writeFileSync(join(source, nonInput), 'ignored non-input addition');
    assert.equal(git(['check-ignore', nonInput]), nonInput);
    assert.ok(prepareReviewEvaluation({ root: source, parent }).manifest.cases.length);
  } finally { rmSync(parent, { recursive: true, force: true }); }
});

test('an immutable commit without the requested Skill is rejected before a prepared receipt', () => {
  const parent = mkdtempSync(join(tmpdir(), 'qodo-eval-missing-test-'));
  try {
    const git = (args, input) => execFileSync('git', args, { cwd: parent, encoding: 'utf8', input }).trim();
    git(['init', '--quiet']);
    const tree = git(['hash-object', '-w', '-t', 'tree', '--stdin'], '');
    // Synthetic Git object only: no user commit, branch, signing setting or hook is changed.
    const ref = git(['hash-object', '-w', '-t', 'commit', '--stdin'],
      `tree ${tree}\nauthor Fixture <fixture@qodo.invalid> 0 +0000\ncommitter Fixture <fixture@qodo.invalid> 0 +0000\n\nEmpty snapshot fixture\n`);
    git(['update-ref', 'HEAD', ref]);
    const output = mkdtempSync(join(tmpdir(), 'qodo-eval-missing-output-'));
    try { assert.throws(() => prepareReviewEvaluation({ root: parent, parent: output, ref }), /has no qodo-review\/SKILL\.md/); }
    finally { rmSync(output, { recursive: true, force: true }); }
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test('recorded grade validation rejects truthy non-boolean verdicts and inconsistent summaries', () => {
  const make = (passed) => ({ expectations: [{ text: 'Check', passed, evidence: 'response.md:1 evidence' }],
    summary: { passed: 1, failed: 0, total: 1, pass_rate: 1 } });
  for (const invalid of ['false', 'true', 1, [], {}, null, undefined]) {
    assert.throws(() => assertGrade(make(invalid), ['Check'], true), /must be a boolean/);
  }
  assert.equal(assertGrade(make(true), ['Check'], true), 1);
  assert.throws(() => assertGrade(make(false), ['Check'], true));
});

test('recorded case setup changes invalidate evidence without a model run', () => {
  const directory = mkdtempSync(join(tmpdir(), 'qodo-evidence-case-'));
  try {
    const item = { name: 'fixture', case_sha256: sha256('original setup'), prompt_sha256: sha256('prompt') };
    const manifest = { fixture_source_commit: '1'.repeat(40), cases: [{ ...item, assertions: [] }] };
    const provenance = { fixture_source_commit: manifest.fixture_source_commit,
      fixture_fingerprints: { 'fixture/case.yaml': item.case_sha256, 'fixture/prompt.md': item.prompt_sha256 } };
    assertFixtureProvenance(provenance, manifest);
    writeFileSync(join(directory, 'case.yaml'), 'original setup');
    writeFileSync(join(directory, 'prompt.md'), 'prompt');
    assertCaseInputs(directory, item, directory);
    writeFileSync(join(directory, 'case.yaml'), 'changed setup');
    assert.throws(() => assertCaseInputs(directory, item, directory), /Stale case setup/);
    manifest.cases[0].case_sha256 = sha256('changed setup');
    assertCaseInputs(directory, manifest.cases[0], directory);
    assert.throws(() => assertFixtureProvenance(provenance, manifest), /Recorded fixture inputs/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('recorded artifacts reject symlinked files and ancestors before reading them', (t) => {
  const directory = mkdtempSync(join(tmpdir(), 'qodo-evidence-path-'));
  const outside = mkdtempSync(join(tmpdir(), 'qodo-evidence-outside-'));
  const read = (path) => fixtureFile(directory, path, directory);
  try {
    writeFileSync(join(outside, 'outside.txt'), 'unrelated host fixture');
    mkdirSync(join(directory, 'nested'));
    writeFileSync(join(directory, 'nested/valid.txt'), 'evidence');
    assert.equal(read('nested/valid.txt').toString(), 'evidence');
    for (const path of ['../outside.txt', '/outside.txt', 'C:/outside.txt', 'nested\\valid.txt']) {
      assert.throws(() => read(path), /Unsafe evidence path/);
    }
    try { symlinkSync(join(outside, 'outside.txt'), join(directory, 'linked.txt')); } catch (error) {
      if (['EPERM', 'ENOTSUP'].includes(error.code)) { t.skip('Host cannot create test symlinks'); return; }
      throw error;
    }
    symlinkSync(outside, join(directory, 'linked-directory'), 'dir');
    assert.throws(() => read('linked.txt'), /symlink/);
    assert.throws(() => read('linked-directory/outside.txt'), /symlink/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
    rmSync(outside, { recursive: true, force: true });
  }
});

test('baseline evidence is bound to its immutable Git commit, not only its own manifest', () => {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-behavior');
  const { baseline } = JSON.parse(fixtureFile(evidenceRoot, 'manifest.json')).snapshots;
  assertBaselineSnapshot(evidenceRoot, baseline);
  assert.throws(() => assertBaselineSnapshot(evidenceRoot, { ...baseline, source_commit: '0'.repeat(40) }));
  assert.throws(() => assertBaselineSnapshot(evidenceRoot, { ...baseline,
    fingerprints: { ...baseline.fingerprints, 'SKILL.md': '0'.repeat(64) } }), /immutable commit/);
});

test('recorded behavior evidence covers current instructions and every assertion, with inspectable passing candidate results', () => {
  const evidenceRoot = join(root, 'test/fixtures/qodo-review-behavior');
  const manifest = JSON.parse(fixtureFile(evidenceRoot, 'manifest.json'));
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.method, 'fresh-native-agents-with-anonymous-final-answer-grading');
  assert.equal(manifest.cases.length, 8);
  assertBaselineSnapshot(evidenceRoot, manifest.snapshots.baseline);
  assert.deepEqual(assertHistoryArchives(evidenceRoot, manifest), { 6: 40, 7: 96, 8: 104, 9: 74 });
  for (const [path, expected] of Object.entries(manifest.adjudication?.artifacts ?? {})) {
    assert.equal(sha256(fixtureFile(evidenceRoot, path)), expected, path);
  }
  for (const [path, hash] of Object.entries(manifest.grading_evidence?.artifacts ?? {}))
    assert.equal(sha256(fixtureFile(evidenceRoot, path)), hash);
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
  let assertionCount = 0, candidatePasses = 0;
  const scores = { candidate: { passed: 0, total: 0 }, baseline: { passed: 0, total: 0 } };
  for (const item of manifest.cases) {
    assert.match(item.name, /^[a-z][a-z0-9-]*$/);
    const fixture = join(root, 'evals/qodo-review', item.name);
    assertCaseInputs(fixture, item);
    const graders = readdirSync(inputPath(root, join(fixture, 'graders'), 'directory'))
      .filter((name) => name.endsWith('.md')).sort();
    assert.deepEqual(item.assertions.map((entry) => entry.file), graders);
    for (const grader of item.assertions) {
      assert.equal(sha256(fixtureFile(join(fixture, 'graders'), grader.file)), grader.sha256);
    }
    assertionCount += graders.length;
    for (const configuration of ['candidate', 'baseline']) {
      const run = item.runs[configuration];
      assertRunPaths(run, item.name, configuration);
      assert.deepEqual(Object.keys(run.artifacts).sort(), [run.response, run.grading, run.provenance].sort());
      for (const [path, hash] of Object.entries(run.artifacts)) {
        assert.equal(sha256(fixtureFile(evidenceRoot, path)), hash, path);
      }
      const grade = JSON.parse(fixtureFile(evidenceRoot, run.grading));
      const passed = assertGrade(grade, graders.map((file) =>
        fixtureFile(join(fixture, 'graders'), file).toString('utf8').replace(/^---\n[\s\S]*?\n---\n/, '').trim()),
      configuration === 'candidate');
      scores[configuration].passed += passed;
      scores[configuration].total += graders.length;
      const provenance = JSON.parse(fixtureFile(evidenceRoot, run.provenance));
      assertRunIdentity(provenance, item.name, configuration);
      assertFixtureProvenance(provenance, manifest);
      assert.equal(provenance.source_commit, manifest.snapshots[configuration].source_commit);
      assert.deepEqual(provenance.fingerprints, manifest.snapshots[configuration].fingerprints);
      assert.equal(provenance.response_sha256, sha256(fixtureFile(evidenceRoot, run.response)));
      if (configuration === 'candidate') {
        candidatePasses += passed;
      }
    }
  }
  assert.equal(assertionCount, 40);
  assert.equal(candidatePasses, 40);
  assert.deepEqual(manifest.scores, scores);
});

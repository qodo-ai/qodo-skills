import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { appendFileSync, cpSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { catalogAt, git, planSkillRelease, prepareSkillRelease, readJson, releaseBaseline } from '../scripts/skill-release-plan.mjs';
import { prepareCiValidation } from '../scripts/prepare-ci-validation.mjs';
import { incrementVersion } from '../scripts/prepare-release.mjs';

const source = dirname(dirname(fileURLToPath(import.meta.url)));
const wisdom = 'skills/qodo-codebase-wisdom/SKILL.md';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'skill-release-test-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const name of readdirSync(source)) {
    if (name !== '.git' && name !== 'node_modules') cpSync(join(source, name), join(root, name), { recursive: true });
  }
  const runGit = (...args) => git(root, ...args);
  runGit('init', '--quiet');
  for (const [key, value] of Object.entries({ 'user.name': 'Test', 'user.email': 'test@example.com',
    'commit.gpgsign': 'false', 'core.autocrlf': 'false', 'core.safecrlf': 'false' })) runGit('config', key, value);
  const commit = (message) => { runGit('add', '--all'); runGit('commit', '--quiet', '-m', message); return runGit('rev-parse', 'HEAD'); };
  const base = commit('prepared release snapshot');
  const edit = (path = wisdom, text = '\nCite evidence for each conclusion.\n') => appendFileSync(join(root, path), text);
  const reset = (ref) => { runGit('reset', '--hard', ref); runGit('clean', '-fd'); };
  const check = (...args) => execFileSync(process.execPath, args, { cwd: root, stdio: 'pipe' });
  const dependencies = () => cpSync(join(source, 'node_modules'), join(root, 'node_modules'), { recursive: true });
  return { root, git: runGit, commit, base, edit, reset, check, dependencies };
}

test('a browser source edit previews in CI and becomes a separate complete release after merge', (t) => {
  const f = fixture(t);
  const prior = catalogAt(f.root, f.base);
  const kiro = readFileSync(join(f.root, 'kiro-power/skills/qodo-codebase-wisdom/SKILL.md'), 'utf8');
  f.edit();
  const merged = f.commit('Clarify Codebase Wisdom evidence (#123)');
  assert.equal(readFileSync(join(f.root, 'kiro-power/skills/qodo-codebase-wisdom/SKILL.md'), 'utf8'), kiro);
  assert.equal(prepareCiValidation(f.root, f.base).mode, 'preview');
  f.dependencies();
  f.check('scripts/validate.mjs');
  const previewTree = f.git('rev-parse', 'HEAD^{tree}');
  f.reset(merged);
  const result = prepareSkillRelease(f.root);
  assert.equal(result.version, incrementVersion(prior.package.version, 'patch'));
  const releaseCommit = f.commit('chore(skills): release');
  assert.equal(f.git('rev-parse', 'HEAD^{tree}'), previewTree);
  assert.match(readFileSync(join(f.root, `releases/v${result.version}.json`), 'utf8'), /#123/);
  assert.equal(prepareCiValidation(f.root, merged).mode, 'release');
  for (const args of [['scripts/validate.mjs'], ['scripts/build-release-index.mjs', '--check'],
    ['scripts/build-cli-managed-bundle.mjs', '--check']]) f.check(...args);
  assert.equal(releaseBaseline(f.root), releaseCommit);
  assert.equal(planSkillRelease(f.root).pending, false, 'release merge cannot create another release');
  f.edit(wisdom, '\nNext release change.\n');
  f.commit('next source PR');
  assert.equal(prepareSkillRelease(f.root).version, incrementVersion(result.version, 'patch'));
});

test('multiple source merges bump each changed skill once and preserve unrelated manifest changes', (t) => {
  const f = fixture(t);
  f.edit();
  f.commit('first source merge');
  f.edit();
  f.edit('skills/qodo-review/SKILL.md');
  const manifest = readJson(f.root, 'package.json');
  manifest.scripts.example = 'echo retained';
  writeFileSync(join(f.root, 'package.json'), JSON.stringify(manifest, null, 2));
  f.commit('second source merge');
  const plan = planSkillRelease(f.root);
  assert.deepEqual(plan.skills.map(({ name }) => name), ['qodo-codebase-wisdom', 'qodo-review']);
  const result = prepareSkillRelease(f.root, plan);
  const prior = catalogAt(f.root, f.base);
  assert.equal(result.changes[0].version, incrementVersion(prior.skills.find((s) => s.name === result.changes[0].name).version, 'patch'));
  assert.equal(readJson(f.root, 'package.json').scripts.example, 'echo retained');
});

test('reverted changes drop out of the accumulated release, including a complete revert', (t) => {
  const f = fixture(t);
  f.edit();
  f.edit('skills/qodo-review/SKILL.md');
  f.commit('two edits');
  f.git('restore', '--source', f.base, '--', wisdom);
  f.commit('revert wisdom');
  assert.deepEqual(planSkillRelease(f.root).skills, [{ name: 'qodo-review', change: 'patch' }]);
  f.git('restore', '--source', f.base, '--', 'skills/qodo-review/SKILL.md');
  f.commit('revert review');
  assert.equal(planSkillRelease(f.root).pending, false);
  assert.equal(prepareSkillRelease(f.root), null);
  assert.equal(prepareCiValidation(f.root, f.base).mode, 'source');
});

test('supporting files, catalog display metadata, and packaging fixes are collected', (t) => {
  const f = fixture(t);
  mkdirSync(join(f.root, 'skills/qodo-codebase-wisdom/references'), { recursive: true });
  f.edit('skills/qodo-codebase-wisdom/references/example.md');
  const catalog = readJson(f.root, 'distribution/catalog.json');
  catalog.skills.find((s) => s.name === 'qodo-review').displayName = 'Review changes';
  writeFileSync(join(f.root, 'distribution/catalog.json'), JSON.stringify(catalog, null, 2));
  f.commit('support and display');
  assert.equal(planSkillRelease(f.root).skills.length, 2);
  f.reset(f.base);
  f.edit('scripts/sync-adapters.mjs', '\n// Updated generator.\n');
  f.commit('packaging fix');
  const plan = planSkillRelease(f.root);
  assert.equal(plan.pending, true);
  assert.deepEqual(plan.skills, []);
  const result = prepareSkillRelease(f.root, plan);
  f.commit('package release');
  f.check('scripts/validate-diff.mjs', f.base);
  assert.equal(readJson(f.root, `releases/v${result.version}.json`).package.change, 'patch');
});

test('a new skill already merged to main uses initial relative to the last prepared release', (t) => {
  const f = fixture(t);
  const catalog = readJson(f.root, 'distribution/catalog.json');
  const skill = { ...catalog.skills.find((s) => s.name === 'qodo-codebase-wisdom'), name: 'qodo-example', version: '1.0.0' };
  catalog.skills.push(skill);
  catalog.installPackages.find((p) => p.name === 'qodo').skills.push(skill.name);
  writeFileSync(join(f.root, 'distribution/catalog.json'), JSON.stringify(catalog, null, 2));
  mkdirSync(join(f.root, 'skills/qodo-example'));
  const instructions = readFileSync(join(f.root, wisdom), 'utf8').replaceAll('qodo-codebase-wisdom', 'qodo-example')
    .replace(/^  version:.*$/m, '  version: "1.0.0"').replace(/--skill-version\s+\S+(?=\s+--distribution)/g, '--skill-version 1.0.0');
  writeFileSync(join(f.root, 'skills/qodo-example/SKILL.md'), instructions);
  const main = f.commit('add a canonical skill');
  const result = prepareSkillRelease(f.root);
  assert.equal(result.version, incrementVersion(catalog.package.version, 'minor'));
  assert.deepEqual(result.changes, [{ name: 'qodo-example', version: '1.0.0', change: 'initial' }]);
  f.commit('release the new skill');
  assert.equal(prepareCiValidation(f.root, main).mode, 'release');
});

test('source validation rejects generated edits and preemptive or mismatched version changes', (t) => {
  const f = fixture(t);
  for (const path of ['kiro-power/POWER.md', 'skills/qodo-review/agents/openai.yaml', `releases/v${catalogAt(f.root, f.base).package.version}.json`]) {
    f.edit(path);
    f.commit('invalid generated edit');
    assert.throws(() => prepareCiValidation(f.root, f.base), /belong in the release PR/);
    f.reset(f.base);
  }
  const original = readFileSync(join(f.root, wisdom), 'utf8');
  writeFileSync(join(f.root, wisdom), original.replace(/^  version:.*$/m, '  version: "99.0.0"'));
  f.commit('wrong source version');
  assert.throws(() => prepareCiValidation(f.root, f.base), /metadata.version must match/);
  f.reset(f.base);
  const catalog = readJson(f.root, 'distribution/catalog.json');
  catalog.skills[0].version = '99.0.0';
  writeFileSync(join(f.root, 'distribution/catalog.json'), JSON.stringify(catalog));
  f.commit('wrong catalog version');
  assert.throws(() => prepareCiValidation(f.root, f.base), /leave version changes/);
});

test('unsupported removals and unregistered new skills fail before a source merge', (t) => {
  const f = fixture(t);
  const catalog = readJson(f.root, 'distribution/catalog.json');
  const removed = catalog.skills.pop();
  rmSync(join(f.root, 'skills', removed.name, 'SKILL.md'));
  writeFileSync(join(f.root, 'distribution/catalog.json'), JSON.stringify(catalog));
  f.commit('unsupported removal');
  assert.throws(() => planSkillRelease(f.root), /Skill removal/);
  f.reset(f.base);
  mkdirSync(join(f.root, 'skills/qodo-unknown'));
  f.edit('skills/qodo-unknown/SKILL.md');
  f.commit('unregistered skill');
  assert.throws(() => planSkillRelease(f.root), /must be registered/);
});

test('release PR validation does not repair committed drift or absorb a later source merge', (t) => {
  const f = fixture(t);
  f.edit();
  const main = f.commit('source');
  prepareSkillRelease(f.root);
  f.edit('kiro-power/skills/qodo-codebase-wisdom/SKILL.md', '\nInvalid generated-only instruction.\n');
  f.commit('corrupted release');
  assert.equal(prepareCiValidation(f.root, main).mode, 'release');
  f.dependencies();
  assert.throws(() => f.check('scripts/validate.mjs'), /out of sync|canonical|match/i);
  f.edit('skills/qodo-review/SKILL.md');
  f.commit('main advanced with another skill');
  assert.throws(() => prepareCiValidation(f.root, main), /validate-diff\.mjs/);
});

test('CI refuses dirty checkouts and documentation-only changes need no release', (t) => {
  const f = fixture(t);
  f.edit('README.md');
  assert.throws(() => prepareCiValidation(f.root, f.base), /clean checkout/);
  f.commit('docs');
  assert.equal(planSkillRelease(f.root).pending, false);
  assert.equal(prepareCiValidation(f.root, f.base).mode, 'source');
});

test('write-scoped preparation only consumes successful main pushes; PR validation uses read permissions', () => {
  const workflow = readFileSync(join(source, '.github/workflows/prepare-skill-release.yml'), 'utf8');
  assert.match(workflow, /workflows: \[Validate distribution\]/);
  for (const guard of ["github.event.workflow_run.conclusion == 'success'", "github.event.workflow_run.event == 'push'",
    "github.event.workflow_run.head_branch == 'main'", 'github.event.workflow_run.head_repository.full_name == github.repository']) {
    assert.ok(workflow.includes(guard));
  }
  assert.doesNotMatch(workflow, /pull_request_target|workflow_run\.pull_requests|download-artifact/);
  const validation = readFileSync(join(source, '.github/workflows/validate.yml'), 'utf8');
  assert.match(validation, /contents: read/);
  assert.doesNotMatch(validation, /contents: write|pull-requests: write/);
  assert.ok(validation.indexOf('prepare-ci-validation.mjs') < validation.indexOf('run: npm test'));
});

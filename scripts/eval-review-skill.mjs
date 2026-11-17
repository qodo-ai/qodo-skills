import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmodSync, lstatSync, mkdirSync, mkdtempSync, realpathSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const json = (path, value) => writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
const instructionInput = (name) => name === 'SKILL.md' || (name.startsWith('references/') && name.endsWith('.md'));
const fixtureInput = (name) => /^[a-z][a-z0-9-]*\/(?:case\.yaml|prompt\.md|graders\/[a-zA-Z0-9._-]+\.md)$/.test(name);

export function requireEvaluationSupport(help) {
  if (!help.includes('--disallow-tools')) {
    throw new Error('--run requires Claude Code 2.1.299 or newer with plugin eval --disallow-tools; staging alone does not require it.');
  }
}

export function inputPath(root, path, kind) {
  const location = relative(root, path);
  if (!location || isAbsolute(location) || location === '..' || location.startsWith(`..${sep}`)) {
    throw new Error('Evaluation input must be inside the source repository.');
  }
  let current = root;
  for (const part of location.split(sep)) {
    current = join(current, part);
    if (lstatSync(current).isSymbolicLink()) throw new Error(`Evaluation input cannot be a symlink: ${location}`);
  }
  const stat = lstatSync(current);
  if (!(kind === 'file' ? stat.isFile() : stat.isDirectory())) {
    throw new Error(`Evaluation input must be a regular ${kind}: ${location}`);
  }
  return current;
}

function git(root, args, encoding = 'utf8') {
  return execFileSync('git', ['--no-replace-objects', '-c', 'core.fsmonitor=false', ...args], {
    cwd: root, encoding, maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^GIT_/i.test(name))),
      GIT_NO_LAZY_FETCH: '1', GIT_OPTIONAL_LOCKS: '0' },
  });
}

export function readGitEvaluationFiles(root, commit, prefix, select = () => true) {
  if (!/^[a-f0-9]{40}$/.test(commit)) throw new Error('Evaluation inputs require a full 40-character commit SHA.');
  const files = {};
  for (const entry of git(root, ['ls-tree', '-r', '-z', commit, '--', prefix]).split('\0').filter(Boolean)) {
    const tab = entry.indexOf('\t'), header = entry.slice(0, tab), path = entry.slice(tab + 1);
    const name = path.slice(prefix.length);
    if (!select(name)) continue;
    const match = header.match(/^100(?:644|755) blob ([a-f0-9]{40})$/);
    if (!match) throw new Error(`Evaluation snapshot input must be a regular Git file: ${path}`);
    if (!path.startsWith(prefix) || /[\\:\r\n\t]/.test(name)
      || name.split('/').some((part) => ['', '.', '..'].includes(part))) {
      throw new Error('Unsafe evaluation snapshot path.');
    }
    const bytes = git(root, ['cat-file', 'blob', match[1]], 'buffer');
    const objectId = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    if (objectId !== match[1]) throw new Error('Evaluation Git blob identity changed.');
    files[name] = bytes;
  }
  return files;
}

function requireCommittedInputs(root, commit, paths, select) {
  const diff = ['--no-ext-diff', '--no-textconv', '--no-renames', '--name-only', '-z', commit, '--', ...paths];
  const changed = [git(root, ['diff', ...diff]), git(root, ['diff', '--cached', ...diff]),
    git(root, ['ls-files', '--others', '--exclude-standard', '-z', '--', ...paths])];
  if (changed.some((names) => names.split('\0').some((name) => name && select(name)))) {
    throw new Error('Commit the selected evaluation inputs before staging; working files are never copied.');
  }
}

export function prepareReviewEvaluation({ root = repositoryRoot, parent = tmpdir(), ref } = {}) {
  const canonicalRoot = realpathSync(root);
  root = canonicalRoot;
  const canonicalParent = realpathSync(parent);
  const location = relative(canonicalRoot, canonicalParent);
  if (!location || (location !== '..' && !location.startsWith(`..${sep}`) && !isAbsolute(location))) {
    throw new Error('Evaluation output must be outside the source repository.');
  }
  if (ref !== undefined && !/^[a-f0-9]{40}$/.test(ref)) throw new Error('--ref requires a full 40-character commit SHA.');
  const fixtureCommit = git(root, ['rev-parse', '--verify', 'HEAD^{commit}']).trim();
  const sourceCommit = ref === undefined ? fixtureCommit : git(root, ['rev-parse', '--verify', `${ref}^{commit}`]).trim();
  if (ref !== undefined && sourceCommit !== ref) throw new Error('--ref must identify that exact commit object.');
  const instructions = readGitEvaluationFiles(root, sourceCommit, 'skills/qodo-review/', instructionInput);
  if (!instructions['SKILL.md']) throw new Error('Selected snapshot has no qodo-review/SKILL.md.');
  requireCommittedInputs(root, fixtureCommit, ['evals/qodo-review', ...(ref === undefined ? ['skills/qodo-review'] : [])],
    (path) => (path.startsWith('evals/qodo-review/') && fixtureInput(path.slice('evals/qodo-review/'.length)))
      || (ref === undefined && path.startsWith('skills/qodo-review/') && instructionInput(path.slice('skills/qodo-review/'.length))));
  const fixtures = readGitEvaluationFiles(root, fixtureCommit, 'evals/qodo-review/', fixtureInput);
  const cases = [...new Set(Object.keys(fixtures).map((name) => name.split('/')[0]))].sort();
  if (!cases.length) throw new Error('The committed snapshot has no evaluation cases.');
  for (const name of cases) {
    if (!fixtures[`${name}/case.yaml`] || !fixtures[`${name}/prompt.md`]
      || !Object.keys(fixtures).some((path) => path.startsWith(`${name}/graders/`))) {
      throw new Error(`Incomplete committed evaluation case: ${name}`);
    }
  }
  const directory = mkdtempSync(join(canonicalParent, 'qodo-review-eval-'));
  const plugin = join(directory, 'plugin'), skill = join(plugin, 'skills/qodo-review');
  mkdirSync(join(plugin, '.claude-plugin'), { recursive: true });
  const fingerprints = {};
  for (const [name, bytes] of Object.entries(instructions)) {
    mkdirSync(dirname(join(skill, name)), { recursive: true });
    writeFileSync(join(skill, name), bytes, { mode: 0o444 });
    fingerprints[name] = digest(bytes);
  }
  const assertions = Object.fromEntries(cases.map((name) => [name, 0])), fixtureFingerprints = {};
  for (const [name, bytes] of Object.entries(fixtures)) {
    const target = join(plugin, 'evals', name);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, bytes, { mode: 0o444 });
    fixtureFingerprints[name] = digest(bytes);
    if (name.includes('/graders/')) assertions[name.split('/')[0]] += 1;
  }
  json(join(plugin, '.claude-plugin/plugin.json'), { name: 'qodo-review-evaluation', version: '0.0.0-eval',
    description: 'Read-only synthetic behavior evaluation of the canonical qodo-review Skill.',
    author: { name: 'Qodo' }, license: 'MIT', skills: './skills/' });
  chmodSync(join(plugin, '.claude-plugin/plugin.json'), 0o444);
  writeFileSync(join(plugin, 'README.md'), [
    '# Qodo review evaluation fixture',
    '',
    'This temporary plugin holds one exact instruction snapshot and synthetic evaluation cases.',
    'It is not a released Qodo package or an installation update. Evaluated agents inspect',
    'the selected Skill and propose actions without calling Qodo, Git or live services.',
    'Model execution requires explicit opt-in on the operator’s Claude account. Normal',
    'trust prompts remain enabled; real MCP servers, shell/write tools, scaffold execution',
    'and report publication are not enabled by the generated command.',
    '',
  ].join('\n'), { mode: 0o444 });
  const args = ['plugin', 'eval', plugin, '--ablation', 'none', '--runs', '1',
    '--concurrency', '2', '--mocks', 'record', '--no-scaffold', '--no-publish',
    '--output-dir', join(directory, 'results'), '--report', join(directory, 'report.html'),
    '--disallow-tools', 'Bash', 'Write', 'Edit', 'Agent', 'WebFetch'];
  const manifest = { schema_version: 1, source_commit: sourceCommit,
    source_kind: 'immutable Git commit', fixture_source_commit: fixtureCommit,
    input_policy: 'Only immutable Git blobs are staged. Dirty selected inputs stop staging; checkout paths are never copied.',
    fingerprints, fixture_fingerprints: fixtureFingerprints, assertions, cases, command: { executable: 'claude', args },
    operations: 'Only synthetic command proposals; no Qodo/Git/service calls in evaluated cases.',
    limits: 'Read-only input files and gated tools are not proof of complete filesystem confinement.',
  };
  json(join(directory, 'manifest.json'), manifest);
  return { directory, plugin, args, manifest };
}

export function main(argv = process.argv.slice(2)) {
  let parent = tmpdir(), ref, run = false;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--output-parent' || argv[index] === '--ref') {
      const option = argv[index], value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error(`${option} requires a value.`);
      if (option === '--output-parent') parent = value;
      else ref = value;
    } else if (argv[index] === '--run') run = true;
    else throw new Error(`Unknown evaluation option: ${argv[index]}`);
  }
  const prepared = prepareReviewEvaluation({ parent, ref });
  console.log(JSON.stringify({ directory: prepared.directory, status: 'prepared', execution_requested: run,
    cases: prepared.manifest.cases, assertions: prepared.manifest.assertions,
    command: prepared.manifest.command }, null, 2));
  if (!run) {
    console.log('Prepared only. --run opts into billed model evaluation on your Claude account; normal trust prompts remain enabled.');
    return 0;
  }
  requireEvaluationSupport(execFileSync('claude', ['plugin', 'eval', '--help'], { encoding: 'utf8' }));
  const result = spawnSync('claude', prepared.args, { stdio: 'inherit', cwd: prepared.directory });
  if (result.error) throw result.error;
  console.log(JSON.stringify({ status: 'evaluator_exited', exit_code: result.status,
    signal: result.signal, directory: prepared.directory }));
  return result.status ?? 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = main();
}

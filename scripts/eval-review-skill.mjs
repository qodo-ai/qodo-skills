import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmodSync, copyFileSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync,
  realpathSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const json = (path, value) => writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);

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

function copyTree(root, source, target) {
  inputPath(root, source, 'directory');
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    if (entry.isDirectory()) copyTree(root, join(source, entry.name), join(target, entry.name));
    else if (entry.isFile()) {
      inputPath(root, join(source, entry.name), 'file');
      copyFileSync(join(source, entry.name), join(target, entry.name));
      chmodSync(join(target, entry.name), 0o444);
    } else throw new Error(`Evaluation input is not a regular file: ${entry.name}`);
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
  const directory = mkdtempSync(join(canonicalParent, 'qodo-review-eval-'));
  const plugin = join(directory, 'plugin');
  const skill = join(plugin, 'skills/qodo-review');
  mkdirSync(join(plugin, '.claude-plugin'), { recursive: true });
  mkdirSync(skill, { recursive: true });
  const prefix = 'skills/qodo-review/';
  let paths;
  let sourceCommit = null;
  const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
  if (ref) {
    if (!/^[a-f0-9]{7,40}$/.test(ref)) throw new Error('--ref requires an immutable Git commit SHA.');
    sourceCommit = git('rev-parse', '--verify', `${ref}^{commit}`);
    paths = git('ls-tree', '-r', '-z', sourceCommit, '--', prefix).split('\0').filter(Boolean).map((entry) => {
      const [header, path] = entry.split('\t');
      if (!/^100(?:644|755) blob [a-f0-9]+$/.test(header)) {
        throw new Error(`Evaluation snapshot input must be a regular file: ${path}`);
      }
      return path;
    });
  } else {
    inputPath(canonicalRoot, join(root, prefix, 'references'), 'directory');
    paths = [`${prefix}SKILL.md`, ...readdirSync(join(root, prefix, 'references'))
      .filter((name) => name.endsWith('.md')).map((name) => `${prefix}references/${name}`)];
  }
  paths = paths.filter((path) => path === `${prefix}SKILL.md`
    || (path.startsWith(`${prefix}references/`) && path.endsWith('.md'))).sort();
  if (!paths.includes(`${prefix}SKILL.md`)) throw new Error('Selected snapshot has no qodo-review/SKILL.md.');
  const fingerprints = {};
  for (const path of paths) {
    const bytes = ref ? execFileSync('git', ['show', `${sourceCommit}:${path}`], { cwd: root })
      : readFileSync(inputPath(canonicalRoot, join(root, path), 'file'));
    const name = path.slice(prefix.length);
    mkdirSync(dirname(join(skill, name)), { recursive: true });
    writeFileSync(join(skill, name), bytes, { mode: 0o444 });
    fingerprints[name] = digest(bytes);
  }
  const caseRoot = inputPath(canonicalRoot, join(root, 'evals/qodo-review'), 'directory');
  const cases = readdirSync(caseRoot, { withFileTypes: true })
    .filter((entry) => {
      if (entry.isSymbolicLink()) throw new Error(`Evaluation case cannot be a symlink: ${entry.name}`);
      return entry.isDirectory();
    }).map((entry) => entry.name).sort();
  const assertions = {};
  for (const name of cases) {
    const source = join(root, 'evals/qodo-review', name);
    const target = join(plugin, 'evals', name);
    mkdirSync(target, { recursive: true });
    for (const file of ['case.yaml', 'prompt.md']) {
      copyFileSync(inputPath(canonicalRoot, join(source, file), 'file'), join(target, file));
      chmodSync(join(target, file), 0o444);
    }
    copyTree(canonicalRoot, join(source, 'graders'), join(target, 'graders'));
    assertions[name] = readdirSync(join(target, 'graders')).filter((file) => file.endsWith('.md')).length;
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
    source_kind: ref ? 'immutable Git commit' : 'current working instruction bytes',
    fingerprints, assertions, cases, command: { executable: 'claude', args },
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
  const result = spawnSync('claude', prepared.args, { stdio: 'inherit', cwd: prepared.directory });
  if (result.error) throw result.error;
  console.log(JSON.stringify({ status: 'evaluator_exited', exit_code: result.status,
    signal: result.signal, directory: prepared.directory }));
  return result.status ?? 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = main();
}

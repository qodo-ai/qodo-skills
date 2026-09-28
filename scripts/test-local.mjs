/** Test source changes in an isolated release preview; never regenerate the contributor's checkout. */
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, lstatSync, mkdirSync, mkdtempSync, realpathSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));

function isolatedEnvironment() {
  // Git environment overrides must not redirect a preview write into the caller's index/worktree.
  return { ...Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^GIT_/i.test(name))),
    GIT_OPTIONAL_LOCKS: '0' };
}

function git(root, args, options = {}) {
  return execFileSync('git', ['-c', 'core.hooksPath=/dev/null', ...args], {
    cwd: root, env: isolatedEnvironment(), encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
    stdio: ['pipe', 'pipe', 'pipe'], ...options,
  });
}

function inside(root, path) {
  const value = relative(root, path);
  return value === '' || (!isAbsolute(value) && value !== '..' && !value.startsWith(`..${sep}`));
}

function assertSnapshotPath(root, path) {
  if (!path || isAbsolute(path) || path.split('/').some((part) => ['..', '.', '.git'].includes(part))) {
    throw new Error(`Unsafe test snapshot path: ${path}`);
  }
  let current = root;
  for (const part of path.split('/')) {
    current = join(current, part);
    let stat;
    try { stat = lstatSync(current); } catch (error) {
      if (error.code === 'ENOENT') return; // A tracked deletion belongs in the snapshot too.
      throw error;
    }
    if (stat.isSymbolicLink()) throw new Error(`Test snapshots do not support symlinks: ${path}`);
  }
  if (lstatSync(current).isDirectory()) throw new Error(`Test snapshots do not support submodules: ${path}`);
}

export function runArtifactTests(root) {
  const npmCli = process.env.npm_execpath;
  if (!npmCli) throw new Error('Run the test suite through npm test or npm run test:artifacts.');
  // npm.cmd cannot be spawned directly on Windows without a shell.
  execFileSync(process.execPath, [npmCli, 'run', 'test:artifacts'], {
    cwd: root, env: isolatedEnvironment(), stdio: 'inherit',
  });
}

export function runLocalTests(root = repositoryRoot, {
  base = 'origin/main', temporaryParent = tmpdir(), runSuite = runArtifactTests,
} = {}) {
  root = realpathSync(root);
  temporaryParent = realpathSync(temporaryParent);
  if (inside(root, temporaryParent)) throw new Error('The test temporary directory must be outside the contributor checkout.');
  if (!existsSync(join(root, 'node_modules'))) throw new Error('Run npm ci before npm test.');
  if (!base || base.startsWith('-')) throw new Error('Expected a Git base ref, not an option.');
  const head = git(root, ['rev-parse', 'HEAD']).trim();
  let baseCommit;
  try { baseCommit = git(root, ['merge-base', head, base]).trim(); } catch {
    throw new Error(`Cannot resolve test base ${base}; fetch repository history or use npm test -- --base <ref>.`);
  }
  const paths = git(root, ['ls-files', '-z', '--cached', '--others', '--exclude-standard']).split('\0').filter(Boolean);
  for (const path of paths) assertSnapshotPath(root, path);
  // Git supplies normalized tracked content, including both staged and unstaged changes.
  const patch = git(root, ['diff', '--binary', '--no-ext-diff', '--no-textconv', head, '--']);
  const untracked = git(root, ['ls-files', '-z', '--others', '--exclude-standard']).split('\0').filter(Boolean);
  const temporaryRoot = mkdtempSync(join(temporaryParent, 'qodo-test-'));
  const preview = join(temporaryRoot, 'repository');
  try {
    // Independent Git objects/index: no worktree registration, shared index, or remote fetch.
    git(root, ['clone', '--quiet', '--no-local', '--no-checkout', '--', root, preview]);
    for (const [key, value] of Object.entries({ 'core.autocrlf': 'false', 'core.safecrlf': 'false',
      'core.hooksPath': '/dev/null', 'commit.gpgsign': 'false', 'gc.auto': '0', 'maintenance.auto': 'false' })) {
      git(preview, ['config', key, value]);
    }
    git(preview, ['checkout', '--quiet', '--detach', head]);
    if (patch) git(preview, ['apply', '--binary', '--whitespace=nowarn', '-'], { input: patch });
    for (const path of untracked) {
      const target = join(preview, path);
      mkdirSync(dirname(target), { recursive: true });
      cpSync(join(root, path), target);
    }
    if (git(preview, ['status', '--porcelain']).trim()) {
      git(preview, ['add', '--all']);
      git(preview, ['-c', 'user.name=Local test preview', '-c', 'user.email=local-test@qodo.invalid',
        'commit', '--quiet', '-m', 'Snapshot local source changes for testing']);
    }
    cpSync(join(root, 'node_modules'), join(preview, 'node_modules'), { recursive: true, dereference: true });
    console.log('Testing an isolated snapshot; contributor files, index, versions, and branch stay unchanged.');
    execFileSync(process.execPath, ['scripts/prepare-ci-validation.mjs'], {
      cwd: preview, env: { ...isolatedEnvironment(), SKILLS_PR_BASE: baseCommit }, stdio: 'inherit',
    });
    return runSuite(preview);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = process.argv.slice(2);
    if (args.length && (args.length !== 2 || args[0] !== '--base' || !args[1])) {
      throw new Error('Usage: npm test [-- --base <ref>]');
    }
    const mode = process.env.QODO_SKILLS_TEST_MODE;
    if (mode === 'committed') runArtifactTests(repositoryRoot);
    else if (!mode) runLocalTests(repositoryRoot, args.length ? { base: args[1] } : {});
    else throw new Error(`Unknown QODO_SKILLS_TEST_MODE: ${mode}`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = Number.isInteger(error.status) && error.status > 0 ? error.status : 1;
  }
}

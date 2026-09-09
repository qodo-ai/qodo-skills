/** Generate only an ephemeral CI preview for source PRs; release PRs validate their committed bytes. */
import { execFileSync } from 'node:child_process';
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { catalogAt, git, planSkillRelease, prepareSkillRelease, releaseBaseline } from './skill-release-plan.mjs';

export function prepareCiValidation(root, base) {
  if (base && !/^[a-f0-9]{40}$/.test(base)) throw new Error('CI base must be a full commit SHA.');
  if (git(root, 'status', '--porcelain')) throw new Error('CI preparation requires a clean checkout.');
  const head = git(root, 'rev-parse', 'HEAD');
  const releasePr = base && catalogAt(root, base).package.version !== catalogAt(root, head).package.version;
  const baseline = releaseBaseline(root, releasePr ? base : head);
  let mode = 'release';
  if (!releasePr && baseline !== head) {
    const plan = planSkillRelease(root, baseline);
    const prepared = prepareSkillRelease(root, plan);
    mode = prepared ? 'preview' : 'source';
    if (prepared) {
      git(root, 'add', '--all');
      git(root, '-c', 'user.name=CI preview', '-c', 'user.email=ci@qodo.invalid', '-c', 'commit.gpgsign=false',
        '-c', 'core.hooksPath=/dev/null', 'commit', '--quiet', '-m', 'Validate unreleased skill preview');
    }
  }
  // A release PR uses the previous release snapshot, including source changes already merged to main.
  execFileSync(process.execPath, ['scripts/validate-diff.mjs', baseline], { cwd: root, stdio: 'inherit' });
  console.log(mode === 'preview' ? 'Generated a temporary release preview for CI; no branch is changed remotely.'
    : `Validating committed ${mode} files.`);
  return { mode, baseline };
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  prepareCiValidation(process.cwd(), process.env.SKILLS_PR_BASE || undefined);
}

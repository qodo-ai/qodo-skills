/** Maintain one release PR from validated main, using only the repository workflow token. */
import { execFileSync } from 'node:child_process';
import { appendFileSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { git, planSkillRelease, prepareSkillRelease } from './skill-release-plan.mjs';

export const releaseBranch = 'automation/skills-release';
export const releaseMarker = '<!-- qodo-skills-release-pr -->';
const bot = 'github-actions[bot]';

async function api(path, body, method = body ? 'POST' : 'GET') {
  const response = await fetch(`https://api.github.com/${path}`, {
    method,
    headers: { Authorization: `Bearer ${process.env.GH_TOKEN}`, Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28' },
    ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(30_000),
  });
  if (response.status === 404 && path.includes('/git/ref/heads/')) return null;
  if (!response.ok) throw new Error(`GitHub request failed (${response.status}) for ${path}.`);
  return response.json();
}

function report(message) {
  console.log(message);
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${message}\n`);
}

function owned(pr, repository) {
  return pr.user?.login === bot && pr.body?.startsWith(releaseMarker)
    && pr.base.ref === 'main' && pr.base.repo.full_name === repository
    && pr.head.ref === releaseBranch && pr.head.repo?.full_name === repository;
}

export async function runSkillRelease({ repository, base, root = process.cwd(), request = api,
  run = execFileSync, plan = planSkillRelease, prepare = prepareSkillRelease, log = report }) {
  if (repository !== 'qodo-ai/qodo-skills' || !/^[a-f0-9]{40}$/.test(base)) throw new Error('Expected validated qodo-skills main.');
  const prefix = `repos/${repository}`;
  const runGit = (...args) => run('git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  if (runGit('rev-parse', 'HEAD') !== base || runGit('status', '--porcelain')) throw new Error('Expected a clean validated main checkout.');
  if ((await request(`${prefix}/git/ref/heads/main`))?.object.sha !== base) {
    log('A newer main commit is waiting for validation; its successful run will refresh the release PR.');
    return;
  }
  const headQuery = encodeURIComponent(`qodo-ai:${releaseBranch}`);
  const prs = await request(`${prefix}/pulls?state=open&base=main&head=${headQuery}&per_page=100`);
  if (prs.length > 1 || prs.some((pr) => !owned(pr, repository))) throw new Error('Release branch has an unrecognized open PR.');
  const pr = prs[0];
  const branch = await request(`${prefix}/git/ref/heads/${releaseBranch}`);
  const expected = branch?.object.sha ?? '';
  if (pr && pr.head.sha !== expected) throw new Error('Release branch changed during discovery; rerun preparation.');
  if (branch && !pr) {
    const history = await request(`${prefix}/pulls?state=closed&base=main&head=${headQuery}&sort=updated&direction=desc&per_page=1`);
    if (!history.length || !owned(history[0], repository) || history[0].head.sha !== expected) {
      throw new Error('Existing release branch has no matching bot-owned PR. Inspect it before deleting the branch in GitHub and retrying.');
    }
  }
  const releasePlan = plan(root);
  const result = prepare(root, releasePlan);
  if (result) {
    run('npm', ['run', 'check'], { cwd: root, stdio: 'inherit' });
    runGit('add', '--all');
    runGit('-c', `user.name=${bot}`, '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
      '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '--quiet',
      '-m', `chore(skills): release v${result.version}`);
    run(process.execPath, ['scripts/validate-diff.mjs', releasePlan.baseline], { cwd: root, stdio: 'inherit' });
  }
  // Check both refs and the PR again before writing. The explicit lease also rejects races at push time.
  if ((await request(`${prefix}/git/ref/heads/main`))?.object.sha !== base
    || ((await request(`${prefix}/git/ref/heads/${releaseBranch}`))?.object.sha ?? '') !== expected) {
    throw new Error('Main or the release branch changed; no release PR update was published.');
  }
  if (pr) {
    const current = await request(`${prefix}/pulls/${pr.number}`);
    if (!owned(current, repository) || current.state !== 'open' || current.head.sha !== expected) {
      throw new Error('Release PR changed or closed; no update was published.');
    }
  }
  if (!result) {
    if (pr) await request(`${prefix}/pulls/${pr.number}`, { state: 'closed' }, 'PATCH');
    log('No unreleased package changes remain. Any open bot release PR was closed.');
    return;
  }
  const body = `${releaseMarker}\nRelease v${result.version} collects the unreleased changes on main.\n\n`
    + `${releasePlan.summary}\n\n`
    + 'Generated from main `' + base + '`, after release `' + releasePlan.baseline + '`.\n\n'
    + 'Approve workflows to run in the merge box, wait for all checks, then merge this PR to start **Release skills**. '
    + 'Publication and marketplace handoffs retain their protected approvals. '
    + 'Kiro reads the generated packages under main when this PR merges.\n\n'
    + 'This PR is refreshed automatically; make skill edits in ordinary source PRs.';
  let unchanged = false;
  if (expected) {
    const commit = await request(`${prefix}/git/commits/${expected}`);
    unchanged = commit.tree.sha === runGit('rev-parse', 'HEAD^{tree}')
      && commit.parents.length === 1 && commit.parents[0].sha === base;
  }
  if (!unchanged) runGit('push', `--force-with-lease=refs/heads/${releaseBranch}:${expected}`, 'origin', `HEAD:refs/heads/${releaseBranch}`);
  const fields = { title: `chore(skills): release v${result.version}`, body };
  if (pr) {
    if (pr.body !== body || pr.title !== fields.title) await request(`${prefix}/pulls/${pr.number}`, fields, 'PATCH');
    log(`Release PR #${pr.number} is ready for review: v${result.version}.`);
  } else {
    const created = await request(`${prefix}/pulls`, { ...fields, head: releaseBranch, base: 'main' });
    log(`Prepared [release PR #${created.number}](${created.html_url}) for v${result.version}. Approve workflows to run before merging.`);
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await runSkillRelease({ repository: process.env.GITHUB_REPOSITORY, base: git(process.cwd(), 'rev-parse', 'HEAD') });
}

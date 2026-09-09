/** GitHub-only driver. All executed code comes from the trusted default-branch checkout. */
import { execFileSync } from 'node:child_process';
import { appendFileSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { prepareSkillPullRequest } from './prepare-skill-pr.mjs';

async function api(path, body) {
  const response = await fetch(`https://api.github.com/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      Authorization: `Bearer ${process.env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`GitHub request failed (${response.status}) for ${path}.`);
  const result = await response.json();
  if (result.errors?.length) throw new Error(result.errors.map((error) => error.message).join('; '));
  return result;
}

function report(message) {
  console.log(message);
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${message}\n`);
}

function eligible(pr, repository) {
  return pr.state === 'open' && pr.base.ref === 'main'
    && pr.base.repo.full_name === repository && pr.head.repo?.full_name === repository
    && pr.head.ref !== 'main';
}

export async function runPreparation({ repository, number, base, request = api,
  run = execFileSync, prepare = prepareSkillPullRequest, root = process.cwd(), log = report }) {
  if (repository !== 'qodo-ai/qodo-skills' || !Number.isSafeInteger(number) || number < 1) {
    throw new Error('Expected a qodo-ai/qodo-skills PR.');
  }
  const pr = await request(`repos/${repository}/pulls/${number}`);
  if (!eligible(pr, repository)) {
    log('Automatic preparation applies to open, same-repository skill PRs targeting main.');
    return;
  }
  if (pr.base.sha !== base) throw new Error('Main moved since this run started. Re-run preparation.');
  const head = pr.head.sha;
  run('git', ['fetch', '--no-tags', 'origin', `refs/pull/${number}/head`], { cwd: root, stdio: 'inherit' });
  const fetched = run('git', ['rev-parse', 'FETCH_HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  if (fetched !== head) throw new Error('The PR changed during preparation. Its latest run will prepare the new head.');
  const result = prepare({ root, base, head, number });
  if (result.status !== 'prepared') {
    log(result.reason ?? `The PR already contains the prepared v${result.version} files.`);
    return;
  }
  // These commands still run the trusted base scripts and dependency manifest.
  run('npm', ['run', 'check'], { cwd: root, stdio: 'inherit' });
  run('git', ['-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
    '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '--quiet', '-m', 'Validate prepared skill release'], { cwd: root, stdio: 'inherit' });
  run(process.execPath, ['scripts/validate-diff.mjs', base], { cwd: root, stdio: 'inherit' });
  const current = await request(`repos/${repository}/pulls/${number}`);
  if (!eligible(current, repository) || current.head.sha !== head || current.head.ref !== pr.head.ref || current.base.sha !== base) {
    throw new Error('The PR or main changed; no generated commit was published. Re-run preparation on the current PR.');
  }
  const response = await request('graphql', {
    query: 'mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) { commit { oid url } } }',
    variables: {
      input: {
        branch: { repositoryNameWithOwner: repository, branchName: pr.head.ref },
        expectedHeadOid: head,
        message: { headline: result.version ? `chore(skills): prepare v${result.version} for PR #${number}`
          : `chore(skills): remove reverted release preparation for PR #${number}` },
        fileChanges: { additions: result.additions, deletions: result.deletions ?? [] },
      },
    },
  });
  const commit = response.data.createCommitOnBranch.commit;
  const outcome = result.version ? `Prepared v${result.version}` : 'Removed release preparation for reverted instructions';
  log(`${outcome} in [${commit.oid.slice(0, 7)}](${commit.url}). A reviewer must select **Approve workflows to run** in the PR merge box, then wait for the checks before merging. No local commands are required.`);
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await runPreparation({
    repository: process.env.GITHUB_REPOSITORY,
    number: Number(process.env.SKILL_PR_NUMBER),
    base: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
  });
}

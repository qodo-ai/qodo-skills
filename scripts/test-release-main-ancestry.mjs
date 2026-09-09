/** Exercise publication while main changes, using the isolated release-test repository. */
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

export function assertCapturedReleasePublication({ checkout, publishPath, publishEnv, releaseSha, run, runShell }) {
  const git = (...args) => run(checkout, 'git', args).trim();
  const unrelated = git('commit-tree', `${releaseSha}^{tree}`, '-m', 'unrelated history');
  git('push', '--force', 'origin', `${unrelated}:refs/heads/main`);
  assert.throws(() => runShell(checkout, publishPath, publishEnv), /no longer belongs to main/);
  assert.equal(git('ls-remote', '--tags', 'origin'), '', 'rejected ancestry must not create a tag');
  git('push', '--force', 'origin', `${releaseSha}:refs/heads/main`);

  writeFileSync(join(checkout, 'pending-source.txt'), 'New source awaiting the next release.\n');
  git('add', 'pending-source.txt');
  git('-c', 'commit.gpgsign=false', 'commit', '-m', 'source merged while publication awaited approval');
  const advanced = git('rev-parse', 'HEAD');
  git('push', 'origin', 'main');
  git('reset', '--hard', releaseSha);
  runShell(checkout, publishPath, publishEnv);
  assert.equal(git('rev-parse', 'HEAD'), releaseSha);
  assert.equal(git('rev-parse', 'origin/main'), advanced);
  // Reset only this temporary fixture's remote for the independent recovery cases that follow.
  git('push', '--force', 'origin', `${releaseSha}:refs/heads/main`);
}

/** Shared prepared-release baseline for automated and manual preparation. */
import { execFileSync } from 'node:child_process';

export function git(root, ...args) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'pipe'] }).trimEnd();
}

export const catalogAt = (root, ref) => JSON.parse(git(root, 'show', `${ref}:distribution/catalog.json`));

export function releaseBaseline(root, ref = 'HEAD') {
  const version = catalogAt(root, ref).package.version;
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Expected a stable package version.');
  const commit = git(root, 'log', '--diff-filter=A', '-1', '--format=%H', ref,
    '--', `releases/v${version}.json`);
  if (!/^[a-f0-9]{40}$/.test(commit)) throw new Error(`Cannot find the prepared v${version} release baseline.`);
  if (catalogAt(root, commit).package.version !== version) throw new Error('Release baseline catalog does not match its record.');
  return commit;
}

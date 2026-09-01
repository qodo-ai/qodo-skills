/** Verify that the remote repository rejects release-tag movement. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const fixture = mkdtempSync(join(tmpdir(), 'qodo-release-lease-'));
const origin = join(fixture, 'origin.git');
const seed = join(fixture, 'seed');
const runner = join(fixture, 'runner');
const git = (cwd, args) => execFileSync('git', [
  '-c', 'commit.gpgsign=false',
  '-c', 'tag.gpgSign=false',
  ...args,
], { cwd, encoding: 'utf8', stdio: 'pipe' }).trim();

try {
  git(fixture, ['init', '--bare', '--initial-branch=main', origin]);
  const preReceive = join(origin, 'hooks', 'pre-receive');
  writeFileSync(preReceive, [
    '#!/usr/bin/env bash',
    '# Description: reject updates and deletions of release tags in this bare-repository fixture.',
    '# Usage: Git pre-receive hook; reads "<old-sha> <new-sha> <ref>" records from stdin.',
    'set -euo pipefail',
    'while read -r old_sha new_sha ref_name; do',
    '  case "${ref_name}" in',
    '    refs/tags/*)',
    '      if [[ "${old_sha}" == *[!0]* ]]; then',
    '        echo "immutable release tag update rejected: ${ref_name}" >&2',
    '        exit 1',
    '      fi',
    '      ;;',
    '  esac',
    'done',
    '',
  ].join('\n'));
  chmodSync(preReceive, 0o755);
  git(fixture, ['clone', origin, seed]);
  git(seed, ['config', 'user.name', 'Release Test']);
  git(seed, ['config', 'user.email', 'release-test@qodo.invalid']);
  writeFileSync(join(seed, 'release.txt'), 'v1\n');
  git(seed, ['add', 'release.txt']);
  git(seed, ['commit', '-m', 'release v1']);
  const releaseSha = git(seed, ['rev-parse', 'HEAD']);
  git(seed, ['push', 'origin', 'main']);

  git(fixture, ['clone', origin, runner]);
  git(runner, ['config', 'user.name', 'Release Test']);
  git(runner, ['config', 'user.email', 'release-test@qodo.invalid']);
  git(runner, ['tag', '-a', 'v1', '-m', 'v1']);
  git(runner, ['push', 'origin', 'refs/tags/v1:refs/tags/v1']);
  assert.equal(
    git(runner, ['ls-remote', 'origin', 'refs/tags/v1^{}']).split(/\s+/)[0],
    releaseSha,
  );

  writeFileSync(join(seed, 'release.txt'), 'v2\n');
  git(seed, ['add', 'release.txt']);
  git(seed, ['commit', '-m', 'advance main']);
  git(seed, ['push', 'origin', 'main']);

  git(runner, ['fetch', 'origin', 'main']);
  assert.notEqual(git(runner, ['rev-parse', 'origin/main']), releaseSha,
    'the final release guard must observe an intervening main advance');
  git(runner, ['tag', '-f', '-a', 'v1', '-m', 'moved v1', 'origin/main']);
  assert.throws(() => git(runner, [
    'push', '--force', 'origin', 'refs/tags/v1:refs/tags/v1',
  ]), /immutable release tag update rejected/);
  assert.equal(
    git(runner, ['ls-remote', 'origin', 'refs/tags/v1^{}']).split(/\s+/)[0],
    releaseSha,
  );
} finally {
  rmSync(fixture, { recursive: true, force: true });
}

console.log('Release tag protection test passed.');

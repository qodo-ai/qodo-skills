/** Exercise release transaction failure paths without mutating the source tree. */
import assert from 'node:assert/strict';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { executeReleaseTransaction, releaseTransaction } from './prepare-release.mjs';

const temporaryRoot = mkdtempSync(join(tmpdir(), 'qodo-skills-release-transaction-test-'));

try {
  const snapshotRepository = join(temporaryRoot, 'snapshot-repository');
  const snapshotBackups = join(temporaryRoot, 'snapshot-backups');
  mkdirSync(snapshotRepository);
  mkdirSync(snapshotBackups);
  writeFileSync(join(snapshotRepository, 'package.json'), '{"version":"1.0.0"}\n');
  assert.throws(
    () => releaseTransaction(snapshotRepository, {
      backupParent: snapshotBackups,
      copy() {
        throw new Error('injected snapshot failure');
      },
    }),
    /injected snapshot failure/,
  );
  assert.deepEqual(readdirSync(snapshotBackups), [], 'failed snapshot construction must clean its backup');

  const rollbackRepository = join(temporaryRoot, 'rollback-repository');
  const rollbackBackups = join(temporaryRoot, 'rollback-backups');
  mkdirSync(rollbackRepository);
  mkdirSync(rollbackBackups);
  writeFileSync(join(rollbackRepository, 'package.json'), '{"version":"1.0.0"}\n');
  let rollbackCopyCount = 0;
  assert.throws(
    () => executeReleaseTransaction(rollbackRepository, () => {
      writeFileSync(join(rollbackRepository, 'package.json'), '{"version":"2.0.0"}\n');
      throw new Error('injected release failure');
    }, {
      backupParent: rollbackBackups,
      copy(...args) {
        rollbackCopyCount += 1;
        if (rollbackCopyCount > 1) throw new Error('injected restore failure');
        cpSync(...args);
      },
    }),
    (error) => {
      assert.ok(error instanceof AggregateError);
      assert.match(error.message, /rollback was incomplete/);
      assert.match(error.message, /recovery backup retained at/);
      return true;
    },
  );
  assert.equal(readdirSync(rollbackBackups).length, 1, 'failed rollback must retain its recovery backup');

  const cleanupRepository = join(temporaryRoot, 'cleanup-repository');
  const cleanupBackups = join(temporaryRoot, 'cleanup-backups');
  mkdirSync(cleanupRepository);
  mkdirSync(cleanupBackups);
  const cleanupPackage = join(cleanupRepository, 'package.json');
  writeFileSync(cleanupPackage, '{"version":"1.0.0"}\n');
  assert.throws(
    () => executeReleaseTransaction(cleanupRepository, () => {
      writeFileSync(cleanupPackage, '{"version":"2.0.0"}\n');
      throw new Error('primary release failure');
    }, {
      backupParent: cleanupBackups,
      remove(path, options) {
        if (path.startsWith(cleanupBackups)) throw new Error('injected cleanup failure');
        rmSync(path, options);
      },
    }),
    (error) => {
      assert.ok(error instanceof AggregateError);
      assert.deepEqual(error.errors.map((item) => item.message), [
        'primary release failure',
        'injected cleanup failure',
      ]);
      assert.match(error.message, /repository state was restored but backup cleanup failed/);
      return true;
    },
  );
  assert.equal(readFileSync(cleanupPackage, 'utf8'), '{"version":"1.0.0"}\n');
  assert.equal(readdirSync(cleanupBackups).length, 1, 'cleanup failure must retain the restored backup');
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}

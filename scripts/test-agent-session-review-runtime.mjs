/** Test the maintained skill-local Python component without an upstream checkout or provider access. */
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repository = dirname(dirname(fileURLToPath(import.meta.url)));
const runtime = join(repository, 'skills/qodo-agent-session-review/runtime');
const suite = join(repository, 'test/agent-session-review');
const args = process.argv.slice(2);
let python = process.env.COCKPIT_TEST_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
let reportPath;
const flags = [];
for (let index = 0; index < args.length; index++) {
  const value = args[index];
  if (value === '--offline' || value === '--list') flags.push(value);
  else if (value === '--python' || value === '--report') {
    const next = args[++index];
    if (!next || next.startsWith('--')) throw new Error(`${value} requires a value`);
    if (value === '--python') python = next;
    else reportPath = resolve(next);
  } else throw new Error(`Unknown option: ${value}`);
}
if (!existsSync(join(runtime, 'cockpit/__main__.py'))) throw new Error('Maintained Agent Session Review runtime is missing');
const scratch = mkdtempSync(join(tmpdir(), 'qodo-agent-session-review-tests-'));
const suiteHome = join(scratch, 'home'), suiteTmp = join(scratch, 'tmp'), fixtureBin = join(scratch, 'fixture-bin');
for (const path of [suiteHome, suiteTmp, fixtureBin]) mkdirSync(path, { recursive: true });
const fixtureLog = join(scratch, 'fixture-cli.jsonl');
const summaryPath = join(scratch, 'summary.json');
const quote = (value) => `'${value.replaceAll("'", "'\\''")}'`;
// Real provider clients are never executed, including by child CLI/demo processes.
for (const name of ['gh', 'qodo']) {
  const payload = JSON.stringify({ error: { code: 'fixture_unavailable', message: 'No provider connection in runtime tests' } });
  const log = JSON.stringify({ command: name, fixture: true });
  if (process.platform === 'win32') {
    writeFileSync(join(fixtureBin, `${name}.cmd`), `@echo off\r\necho ${log}>>"${fixtureLog}"\r\necho ${payload}\r\nexit /b 1\r\n`);
    if (name === 'qodo') writeFileSync(join(fixtureBin, 'qodo.mjs'),
      `import fs from 'node:fs';fs.appendFileSync(${JSON.stringify(fixtureLog)},${JSON.stringify(log+'\n')});console.log(${JSON.stringify(payload)});process.exit(1);\n`);
  } else {
    writeFileSync(join(fixtureBin, name), `#!/bin/sh\nprintf '%s\\n' ${quote(log)} >> ${quote(fixtureLog)}\nprintf '%s\\n' ${quote(payload)}\nexit 1\n`, { mode: 0o755 });
  }
}
const isolated = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
  !/^(?:GIT_|PYTHON|REVIEW_COCKPIT_|PR_COCKPIT_|COCKPIT_TEST_|QODO_)/i.test(key)));
const pathKey = Object.keys(isolated).find((key) => key.toLowerCase() === 'path') || 'PATH';
const env = { ...isolated,
  HOME: suiteHome, USERPROFILE: suiteHome, TMPDIR: suiteTmp, TEMP: suiteTmp, TMP: suiteTmp,
  REVIEW_COCKPIT_HOME: join(suiteHome, '.qodo/review-cockpit'), PR_COCKPIT_HOME: '', REVIEW_COCKPIT_PRODUCT: '0',
  PYTHONPATH: [runtime, suite].join(delimiter), PYTHONDONTWRITEBYTECODE: '1', PYTHONUTF8: '1', PYTHONNOUSERSITE: '1',
  GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : '/dev/null', GIT_CONFIG_NOSYSTEM: '1',
  COCKPIT_TEST_ISOLATED: '1', COCKPIT_TEST_FIXTURE_BIN: fixtureBin,
  COCKPIT_TEST_OFFLINE: flags.includes('--offline') ? '1' : '0', COCKPIT_TEST_SUMMARY: summaryPath,
  [pathKey]: fixtureBin + delimiter + (isolated[pathKey] || ''),
};
let exitCode = 1;
try {
  const probe = spawnSync(python, ['-X', 'utf8', '-B', '-c',
    'import sys; assert sys.version_info >= (3,9), "Python 3.9+ required"; print(sys.version.split()[0])'],
  { cwd: runtime, env, encoding: 'utf8' });
  if (probe.error || probe.status !== 0) throw new Error(`Python 3.9+ prerequisite failed: ${probe.error?.message || probe.stderr}`);
  console.log(`Agent Session Review runtime tests: Python ${probe.stdout.trim()}, isolated state, ${flags.includes('--offline') ? 'offline accounted subset' : 'full unittest discovery'}`);
  const run = spawnSync(python, ['-X', 'utf8', '-B', join(suite, 'run_suite.py'), ...flags],
    { cwd: runtime, env, stdio: 'inherit', timeout: 180_000 });
  const report = existsSync(summaryPath) ? JSON.parse(readFileSync(summaryPath, 'utf8')) :
    { successful: false, error: run.error?.message || `Python exited ${run.status} (${run.signal || 'no signal'})` };
  report.fixtureCliCalls = existsSync(fixtureLog)
    ? readFileSync(fixtureLog, 'utf8').trim().split('\n').filter(Boolean).map((line) => JSON.parse(line)) : [];
  if (reportPath) { mkdirSync(dirname(reportPath), { recursive: true }); writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n'); }
  console.log(JSON.stringify({ discovered: report.discovered, testsRun: report.testsRun, failures: report.failures,
    errors: report.errors, skipped: report.skipped, excluded: report.excluded?.length, fixtureCliCalls: report.fixtureCliCalls.length }));
  exitCode = run.error ? 1 : (run.status ?? 1);
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
process.exitCode = exitCode;

/** Import a reviewed, committed Cockpit snapshot; never read mutable runtime files or fetch. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const skill = join(root, 'skills/qodo-review-cockpit');
const REVIEWED_FAVICON = 'app/favicon.svg';
const hash = (data) => createHash('sha256').update(data).digest('hex');
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^GIT_/i.test(key)));
function git(source, args) {
  return execFileSync('git', ['-C', source, ...args], { env, maxBuffer: 32 * 1024 * 1024 });
}
function safe(path) {
  assert(path && !path.startsWith('/') && !path.includes('\\')
    && !path.split('/').some((part) => ['', '.', '..'].includes(part)), `Unsafe path: ${path}`);
}
export function selected(path) {
  safe(path);
  if (path.split('/').some((p) => p.startsWith('.') && p !== '.keep')) return false;
  return path === REVIEWED_FAVICON || /^(cockpit\/.*\.py|app\/.*\.(?:html|js|css)|config\.json|LICENSE|NOTICE(?:\.txt)?|fixtures\/(?:build_demo\.py|demo-[^/]+\.json|demo-memory\/.*\.md))$/.test(path);
}
// Apply the committed upstream release manifest with the same marker/exception rules.
function matches(path, patterns) {
  return patterns.some((pattern) => {
    const token = pattern.replace(/\*\*\//g, '\u0001').replace(/\*\*/g, '\u0002')
      .replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]')
      .replace(/\u0001/g, '(?:.*/)?').replace(/\u0002/g, '.*');
    return new RegExp(`^${token}$`).test(path);
  });
}
function sanitizeFiles(source, commit, files, manifest) {
  const common = new Set(['claude', 'noreply', 'users', 'github', 'bot', 'the', 'dev', 'admin', 'root', 'user']);
  const people = new Set((manifest.people ?? []).map((s) => s.toLowerCase()));
  const history = git(source, ['log', commit, '--format=%an%x00%ae%x00%cn%x00%ce']).toString();
  for (const part of history.split(/[\n\0]/)) {
    if (part.includes('[bot]')) continue;
    const name = part.split('@')[0];
    for (const word of [...name.split(/[^A-Za-z]+/), ...(part.includes('@') ? [name.split('+').at(-1)] : [])]) {
      if (word.length >= 4) people.add(word.toLowerCase());
    }
  }
  for (const word of common) people.delete(word);
  const rules = [...manifest.rules];
  const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (people.size) rules.push({ name: 'person', pattern: `\\b(?:${[...people].sort().map(escape).join('|')})\\b`, flags: 'i' });
  return files.map((file) => {
    assert(!matches(file.path, manifest.never), `Excluded runtime path: ${file.path}`);
    const data = Buffer.from(file.data, 'base64');
    if (file.path === REVIEWED_FAVICON) {
      // Upstream treats SVG as binary: a reviewed exact hash admits raw bytes, without text transforms.
      const approved = manifest.binaries?.reviewed?.[file.path]?.sha256;
      assert(/^[a-f0-9]{64}$/.test(approved ?? '') && approved === hash(data),
        `Reviewed favicon SHA-256 is missing or does not match the committed blob: ${file.path}`);
      const text = new TextDecoder('utf-8', { fatal: true }).decode(data);
      assert(!text.includes('\0'), 'Reviewed favicon must be UTF-8 text for existing host projections');
      return { path: file.path, data: file.data, strippedLines: 0, reviewedSha256: approved };
    }
    const text = new TextDecoder('utf-8', { fatal: true }).decode(data);
    assert(!text.includes('\0'), `Binary runtime file: ${file.path}`);
    let inside = false, strippedLines = 0;
    const lines = [];
    for (const line of text.match(/[^\n]*\n|[^\n]+$/g) ?? []) {
      const mark = /^\s*(?:#|\/\/|<!--|\/\*)?\s*(\/?)release:internal\s*(?:-->|\*\/)?\s*$/.exec(line);
      if (mark) {
        assert(mark[1] ? inside : !inside, `Invalid internal markers: ${file.path}`);
        inside = !mark[1]; strippedLines++;
      } else if (inside) strippedLines++;
      else lines.push(line);
    }
    assert(!inside, `Unclosed internal marker: ${file.path}`);
    let output = lines.join('');
    for (const replacement of manifest.replacements ?? []) {
      if (!matches(file.path, [replacement.path])) continue;
      assert(output.includes(replacement.from), `Stale release replacement: ${file.path}`);
      output = output.split(replacement.from).join(replacement.to);
    }
    for (const rule of rules) {
      const flags = rule.flags?.includes('i') ? 'gi' : 'g';
      const allowed = (manifest.allow ?? []).filter((a) => a.rule === rule.name && matches(file.path, [a.path]));
      for (const line of output.split('\n')) {
        for (const hit of line.matchAll(new RegExp(rule.pattern, flags))) {
          const covered = allowed.some((a) => [...line.matchAll(new RegExp(a.match, 'g'))]
            .some((m) => m.index <= hit.index && m.index + m[0].length >= hit.index + hit[0].length));
          assert(covered, `Release sanitization blocked ${file.path}: ${rule.name}`);
        }
      }
    }
    return { path: file.path, data: Buffer.from(output).toString('base64'), strippedLines };
  });
}

export function importRuntime({ source, commit, destination = skill }) {
  assert(/^[a-f0-9]{40}$/.test(commit ?? ''), 'An explicit full lowercase 40-hex commit SHA is required');
  source = resolve(source);
  const origin = git(source, ['config', '--get', 'remote.origin.url']).toString().trim();
  assert(/^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)qodo-ai\/pr-review-cockpit(?:\.git)?\/?$/.test(origin),
    'Source origin must be the intended qodo-ai/pr-review-cockpit repository');
  assert.equal(git(source, ['rev-parse', `${commit}^{commit}`]).toString().trim(), commit);
  const dirty = git(source, ['status', '--porcelain', '--untracked-files=all', '--',
    'cockpit', 'app', 'fixtures', 'config.json', 'LICENSE', 'NOTICE', 'release']).toString().trim();
  assert.equal(dirty, '', 'Runtime/policy source is dirty; commit or clean it before importing');
  const records = git(source, ['ls-tree', '-r', '-z', '--full-tree', commit]).toString().split('\0').filter(Boolean);
  const files = [];
  for (const record of records) {
    const [meta, path] = record.split('\t');
    if (!selected(path)) continue;
    assert(/^100(?:644|755) blob [a-f0-9]{40}$/.test(meta), `Non-regular import: ${path}`);
    const blob = meta.split(' ')[2];
    const data = git(source, ['cat-file', 'blob', blob]);
    files.push({ path, data: data.toString('base64'), sourceSha256: hash(data), sourceBytes: data.length });
  }
  for (const path of ['cockpit/__main__.py', 'app/index.html', 'config.json', 'LICENSE']) {
    assert(files.some((f) => f.path === path), `Required runtime file missing: ${path}`);
  }
  const policy = git(source, ['show', `${commit}:release/build.py`]);
  const manifest = git(source, ['show', `${commit}:release/manifest.json`]);
  const sanitized = sanitizeFiles(source, commit, files, JSON.parse(manifest));
  const entries = sanitized.map((f) => {
    safe(f.path);
    const data = Buffer.from(f.data, 'base64');
    assert(data.length <= 512 * 1024, `${f.path}: exceeds unchanged 512 KiB CLI limit; split upstream`);
    if (f.path === 'LICENSE') assert.equal(hash(data), files.find((x) => x.path === 'LICENSE').sourceSha256,
      'Preserve the original Cockpit LICENSE exactly');
    const original = files.find((x) => x.path === f.path);
    return { path: f.path, sourceSha256: original.sourceSha256, sourceBytes: original.sourceBytes,
      sha256: hash(data), bytes: data.length, strippedLines: f.strippedLines,
      ...(f.reviewedSha256 ? { reviewedSha256: f.reviewedSha256 } : {}) };
  });
  // All validation happens before replacing the previous imported resource tree.
  const target = join(destination, 'runtime');
  rmSync(target, { recursive: true, force: true });
  for (const f of sanitized) {
    mkdirSync(dirname(join(target, f.path)), { recursive: true });
    writeFileSync(join(target, f.path), Buffer.from(f.data, 'base64'));
  }
  const receipt = { schemaVersion: 1, source: 'https://github.com/qodo-ai/pr-review-cockpit', commit,
    license: 'Qodo agreement or Qodo Terms of Use; see runtime/LICENSE',
    policy: { buildSha256: hash(policy), manifestSha256: hash(manifest) },
    totalBytes: entries.reduce((sum, f) => sum + f.bytes, 0), files: entries };
  // One deterministic entry per line keeps the receipt readable and below 500 lines.
  writeFileSync(join(destination, 'runtime-manifest.json'), JSON.stringify(receipt, null, 2)
    .replace(/    \{\n([\s\S]*?)\n    \}/g, (record) => JSON.stringify(JSON.parse(record))) + '\n');
  return receipt;
}

export function verifyRuntime(destination = skill) {
  const manifest = JSON.parse(readFileSync(join(destination, 'runtime-manifest.json')));
  assert.equal(manifest.schemaVersion, 1);
  assert(/^[a-f0-9]{40}$/.test(manifest.commit));
  const walk = (path, prefix = '') => readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const relative = prefix + entry.name;
    assert(!entry.isSymbolicLink(), `Symlink in runtime: ${relative}`);
    return entry.isDirectory() ? walk(join(path, entry.name), relative + '/') : [relative];
  });
  assert.deepEqual(walk(join(destination, 'runtime')).sort(), manifest.files.map((f) => f.path).sort());
  let total = 0;
  for (const file of manifest.files) {
    safe(file.path);
    assert(selected(file.path), `Unexpected runtime path: ${file.path}`);
    const data = readFileSync(join(destination, 'runtime', file.path));
    assert.equal(data.length, file.bytes, file.path);
    assert.equal(hash(data), file.sha256, file.path);
    if (file.path === REVIEWED_FAVICON) {
      assert.equal(file.reviewedSha256, file.sha256, 'Favicon must retain upstream reviewed hash');
      assert.equal(file.sourceSha256, file.sha256, 'Favicon bytes must remain unchanged from source');
    }
    assert(data.length <= 512 * 1024, file.path);
    total += data.length;
  }
  assert.equal(total, manifest.totalBytes);
  return manifest;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = process.argv.slice(2);
    if (args.length === 1 && args[0] === '--verify') {
      const receipt = verifyRuntime();
      console.log(`Verified ${receipt.files.length} Cockpit resources at ${receipt.commit} (${receipt.totalBytes} bytes)`);
    } else {
      assert(args.length === 4 && args[0] === '--source' && args[2] === '--commit',
        'Usage: --source /path/to/upstream --commit <40-hex-sha> | --verify');
      const receipt = importRuntime({ source: args[1], commit: args[3] });
      console.log(`Imported ${receipt.files.length} Cockpit resources at ${receipt.commit} (${receipt.totalBytes} bytes)`);
    }
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

/** Validate the maintained local component; inventory hashes come from current source, never an upstream pin. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const skill = join(root, 'skills/qodo-review-cockpit');
const policy = JSON.parse(readFileSync(join(root, 'scripts/cockpit-runtime-policy.json'), 'utf8'));
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
export const MAX_RESOURCE_BYTES = 512 * 1024;

function safe(path) {
  assert(path && !path.startsWith('/') && !path.includes('\\')
    && !path.split('/').some((part) => ['', '.', '..'].includes(part)), `Unsafe resource path: ${path}`);
}

export function selected(path) {
  safe(path);
  if (path.split('/').some((part) => part.startsWith('.') && part !== '.keep')) return false;
  return path === 'app/favicon.svg'
    || /^(cockpit\/.*\.py|app\/.*\.(?:html|js|css)|config\.json|LICENSE|NOTICE(?:\.txt)?|fixtures\/(?:build_demo\.py|demo-[^/]+\.json|demo-memory\/.*\.md))$/.test(path);
}

function matches(path, patterns) {
  return patterns.some((pattern) => {
    const token = pattern.replace(/\*\*\//g, '\u0001').replace(/\*\*/g, '\u0002')
      .replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]')
      .replace(/\u0001/g, '(?:.*/)?').replace(/\u0002/g, '.*');
    return new RegExp(`^${token}$`).test(path);
  });
}

function scan(path, text) {
  const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const rules = [...policy.rules];
  if (policy.people?.length) rules.push({name: 'person', pattern: `\\b(?:${policy.people.map(escape).join('|')})\\b`, flags: 'i'});
  for (const rule of rules) {
    const flags = [...new Set((rule.flags ?? '').replace(/g/g, '') + 'g')].join('');
    for (const hit of text.matchAll(new RegExp(rule.pattern, flags))) {
      const allowed = policy.allow.some((exception) => exception.rule === rule.name && exception.why
        && matches(path, [exception.path])
        && [...text.matchAll(new RegExp(exception.match, flags))].some((span) =>
          span.index <= hit.index && span.index + span[0].length >= hit.index + hit[0].length));
      // Never echo matched text: it may itself be a credential or personal data.
      assert(allowed, `${path}: component hygiene blocked ${rule.name}`);
    }
  }
}

export function verifyRuntime(destination = skill) {
  const directory = join(destination, 'runtime');
  assert(lstatSync(directory).isDirectory() && !lstatSync(directory).isSymbolicLink(), 'Runtime must be a local directory');
  const walk = (path, prefix = '') => readdirSync(path, {withFileTypes: true}).flatMap((entry) => {
    const relative = prefix + entry.name;
    assert(!entry.isSymbolicLink(), `Symlink in runtime: ${relative}`);
    if (entry.isDirectory()) {
      assert(!relative.split('/').some((part) => part.startsWith('.'))
        && !matches(relative + '/placeholder', policy.never), `Forbidden runtime directory: ${relative}`);
      return walk(join(path, entry.name), relative + '/');
    }
    assert(entry.isFile(), `Non-file runtime resource: ${relative}`);
    return [relative];
  });
  const paths = walk(directory).sort();
  for (const required of ['LICENSE', 'config.json', 'cockpit/__main__.py', 'app/index.html', 'app/app.js',
    'app/styles/package.html', 'app/styles/package.js']) assert(paths.includes(required), `Missing runtime resource: ${required}`);
  const files = paths.map((path) => {
    safe(path);
    assert(selected(path) && !matches(path, policy.never), `Unexpected runtime resource: ${path}`);
    const bytes = readFileSync(join(directory, path));
    assert(bytes.length <= MAX_RESOURCE_BYTES, `${path}: exceeds unchanged 512 KiB resource limit`);
    const sha256 = hash(bytes);
    if (path === 'LICENSE') assert.equal(sha256, policy.licenseSha256, 'Cockpit component LICENSE changed; preserve its terms');
    if (path === 'app/favicon.svg') {
      assert.equal(sha256, policy.reviewedAssets[path]?.sha256, 'Reviewed favicon SHA-256 does not match');
    } else {
      const text = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
      assert(!text.includes('\0') && !/^\s*(?:%PDF-|(?:<\?xml[^>]*>\s*)?<svg\b)/i.test(text), `Unreviewed binary/document: ${path}`);
      assert(!/^\s*(?:#|\/\/|<!--|\/\*)?\s*\/?release:internal\s*(?:-->|\*\/)?\s*$/m.test(text), `Internal release marker in maintained resource: ${path}`);
      scan(path, text);
    }
    return {path, sha256, bytes: bytes.length};
  });
  return {schemaVersion: 1, component: 'qodo-review-cockpit', totalBytes: files.reduce((sum, file) => sum + file.bytes, 0), files};
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const inventory = verifyRuntime();
  console.log(`Validated ${inventory.files.length} maintained Cockpit resources (${inventory.totalBytes} bytes)`);
}

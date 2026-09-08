import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { prepareMarketplace, verifyKiroDocument, verifyMarketplace } from '../scripts/marketplace-release.mjs';

const fixture = readFileSync(new URL('../scripts/fixtures/kiro-powers.html', import.meta.url), 'utf8');
const catalog = JSON.parse(readFileSync(new URL('../distribution/marketplaces.json', import.meta.url), 'utf8'));
const provider = catalog.providers.find(({ id }) => id === 'kiro');
const version = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version;
const context = { tag: `v${version}`, version, commit: 'a'.repeat(40), release: {} };
const entries = provider.listings.map(({ id, sourcePath }) => ({
  name: id,
  repositoryUrl: `https://github.com/qodo-ai/qodo-skills/tree/${provider.sourceRef}/${sourcePath}`,
  repositoryCloneUrl: 'git@github.com:qodo-ai/qodo-skills.git',
  pathInRepo: sourcePath,
  repositoryBranch: provider.sourceRef,
}));

function flightDocument(records, { split = false } = {}) {
  const row = `34:${JSON.stringify(['$', 'div', null, { id: 'browse-powers', cards: records }])}\n`;
  const middle = Math.floor(row.length / 2);
  const chunks = split ? [row.slice(0, middle), row.slice(middle)] : [row];
  return `<html><body>${chunks.map((chunk) =>
    `<script>self.__next_f.push(${JSON.stringify([1, chunk])})</script>`).join('')}</body></html>`;
}

test('captured Kiro HTML recognizes qodo and reports its actual main branch', () => {
  assert.throws(() => verifyKiroDocument(fixture, context),
    /Kiro qodo: expected branch marketplace-kiro, found main/);
  const currentProvider = { ...provider, sourceRef: 'main', listings: [provider.listings[0]] };
  assert.equal(verifyKiroDocument(fixture, context, currentProvider)[0].branch, 'main');
  assert.throws(() => verifyKiroDocument(fixture, context, { ...provider, sourceRef: 'main' }),
    /Kiro qodo-standards: provider listing is missing/);
});

test('accepts both listings in raw JSON, JSON script data, and split Next.js data', () => {
  const json = JSON.stringify({ powers: entries });
  const directory = JSON.stringify({ id: 'browse-powers', cards: entries });
  for (const document of [json, `<script type="application/json">${directory}</script>`,
    flightDocument(entries), flightDocument(entries, { split: true })]) {
    assert.deepEqual(verifyKiroDocument(document, context).map(({ id }) => id), ['qodo', 'qodo-standards']);
  }
});

test('unrelated script metadata cannot stand in for missing directory cards', () => {
  const metadata = `<script type="application/json">${JSON.stringify(entries)}</script>`;
  for (const document of [metadata, metadata + flightDocument([]),
    JSON.stringify({ powers: [], metadata: entries }),
    flightDocument(entries).replace('browse-powers', 'unrelated-section')]) {
    assert.throws(() => verifyKiroDocument(document, context), /provider listing is missing/);
  }
});

test('JSON decoding preserves escaped quotes, backslashes, Unicode and braces inside strings', () => {
  const description = 'Quoted "text", C:\\source, {braces}, and révision';
  const records = entries.map((entry) => ({ ...entry, description }));
  assert.equal(verifyKiroDocument(flightDocument(records), context).length, 2);
  const escaped = JSON.stringify({ powers: records }).replaceAll('/', '\\u002F');
  assert.equal(verifyKiroDocument(escaped, context).length, 2);
  assert.throws(() => verifyKiroDocument(JSON.stringify({ description: JSON.stringify(entries) }), context),
    /provider listing is missing/);
});

test('page prose and malformed scripts cannot establish listings or execute code', () => {
  const json = JSON.stringify({ powers: entries });
  for (const document of [`<p>${json}</p>`, '<script>self.__next_f.push([1,"34:[broken"])</script>',
    `<script>throw new Error('provider code executed');</script><p>${json}</p>`]) {
    assert.throws(() => verifyKiroDocument(document, context), /provider listing is missing/);
  }
});

test('requires each listing to carry the configured path, branch and repository in one record', () => {
  const invalid = [
    [{ ...entries[0], pathInRepo: 'wrong' }, /expected path kiro-power/],
    [{ ...entries[0], repositoryBranch: 'main' }, /expected branch marketplace-kiro, found main/],
    [{ ...entries[0], repositoryUrl: 'https://github.com/unrelated/repo' }, /expected repository/],
    [{ name: 'qodo' }, /expected path kiro-power/],
  ];
  for (const [entry, message] of invalid) {
    assert.throws(() => verifyKiroDocument(flightDocument([entry, entries[1]]), context), message);
  }
  assert.throws(() => verifyKiroDocument(flightDocument([
    { name: 'qodo' }, { ...entries[0], name: 'unrelated' }, entries[1],
  ]), context), /expected path kiro-power/);
  assert.throws(() => verifyKiroDocument(flightDocument([entries[0]]), context), /qodo-standards.*missing/);
  assert.throws(() => verifyKiroDocument(flightDocument([
    ...entries, { ...entries[0], repositoryBranch: 'main' },
  ]), context), /expected branch marketplace-kiro, found main/);
});

test('provider verification still requires the protected branch to equal the release commit', async (t) => {
  let branchCommit = 'b'.repeat(40);
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === provider.directoryUrl) return new Response(flightDocument(entries));
    assert.equal(url, 'https://api.github.com/repos/qodo-ai/qodo-skills/commits/marketplace-kiro');
    return new Response(JSON.stringify({ sha: branchCommit }));
  });
  await assert.rejects(verifyMarketplace('kiro', context), /Kiro follows marketplace-kiro.*not release commit/);
  branchCommit = context.commit;
  const results = await verifyMarketplace('kiro', context);
  assert.equal(results.length, 2);
  assert.ok(results.every(({ commit }) => commit === context.commit));
});

test('clone URLs must identify the same repository as the displayed tree', () => {
  const https = entries.map((entry) => ({ ...entry, repositoryCloneUrl: 'https://github.com/qodo-ai/qodo-skills.git' }));
  assert.equal(verifyKiroDocument(flightDocument(https), context).length, 2);
  for (const repositoryCloneUrl of [undefined, 'git@github.com:unrelated/repo.git',
    'https://github.com/unrelated/repo.git', 'https://github.com.evil.test/qodo-ai/qodo-skills.git']) {
    assert.throws(() => verifyKiroDocument(flightDocument([
      { ...entries[0], repositoryCloneUrl }, entries[1],
    ]), context), /expected clone repository/);
  }
});

test('Kiro release packet provides directory entries from the canonical marketplace contract', () => {
  const temporaryRoot = mkdtempSync(join(tmpdir(), 'qodo-kiro-packet-'));
  try {
    const packet = prepareMarketplace('kiro', context, join(temporaryRoot, 'packet'));
    const desired = JSON.parse(readFileSync(join(packet.output, 'directory-entries.json'), 'utf8'));
    assert.deepEqual(desired.map(({ name, repositoryUrl, repositoryCloneUrl, pathInRepo, repositoryBranch }) =>
      ({ name, repositoryUrl, repositoryCloneUrl, pathInRepo, repositoryBranch })), entries);
    assert.equal(verifyKiroDocument(JSON.stringify(desired), context).length, 2);
    assert.equal(desired[0].displayName, provider.listings[0].displayName);
    assert.equal(desired[0].description, provider.listings[0].description);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

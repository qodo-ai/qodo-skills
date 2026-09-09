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

function flightPayload(value, { split = false } = {}) {
  const row = `34:${JSON.stringify(value)}\n`;
  const middle = Math.floor(row.length / 2);
  const chunks = split ? [row.slice(0, middle), row.slice(middle)] : [row];
  return `<html><body>${chunks.map((chunk) =>
    `<script>self.__next_f.push(${JSON.stringify([1, chunk])})</script>`).join('')}</body></html>`;
}

function directoryElement(records) {
  return ['$', '$L37', null, { id: 'browse-powers', cards: records }];
}

function flightDocument(records, options) {
  return flightPayload(directoryElement(records), options);
}

test('captured Kiro HTML accepts the main source and still reports missing Standards', () => {
  assert.throws(() => verifyKiroDocument(fixture, context),
    /Kiro qodo-standards: provider listing is missing/);
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

test('directory cards are found through component children, including nested child arrays', () => {
  const tree = ['$', 'main', null, {
    children: [null, ['$', 'div', null, { children: [directoryElement(entries)] }]],
  }];
  assert.deepEqual(verifyKiroDocument(flightPayload(tree, { split: true }), context)
    .map(({ id }) => id), ['qodo', 'qodo-standards']);
});

test('nested browse-powers metadata cannot satisfy the complete release verifier', async (t) => {
  const directory = { id: 'browse-powers', cards: entries };
  const metadata = { analytics: { cachedDirectory: directory } };
  const jsonScript = (value) => `<script type="application/json">${JSON.stringify(value)}</script>`;
  const documents = [
    JSON.stringify(metadata),
    jsonScript(metadata),
    jsonScript({ id: 'browse-powers', cards: [], metadata }),
    jsonScript({ children: directory }),
    flightPayload(metadata),
    flightPayload(['$', 'main', null, { metadata, children: directoryElement([]) }]),
    flightPayload(['$', 'main', null, { metadata: directoryElement(entries), children: directoryElement([]) }]),
    flightPayload(['$', 'main', null, { children: directory }]),
    flightPayload(['unrelated', '$L37', null, directory]),
  ];
  let document;
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === provider.directoryUrl) return new Response(document);
    assert.equal(url, 'https://api.github.com/repos/qodo-ai/qodo-skills/commits/main');
    return new Response(JSON.stringify({ sha: context.commit }));
  });
  for (document of documents) {
    await assert.rejects(verifyMarketplace('kiro', context), /provider listing is missing/);
  }
});

test('unrelated metadata cannot add conflicting cards to a valid directory', () => {
  const stale = entries.map((entry) => ({ ...entry, repositoryBranch: 'obsolete' }));
  const metadata = { id: 'browse-powers', cards: stale };
  const directory = { id: 'browse-powers', cards: entries, metadata };
  for (const document of [JSON.stringify(directory),
    `<script type="application/json">${JSON.stringify(directory)}</script>`,
    flightPayload(['$', 'main', null, { metadata, children: directoryElement(entries) }])]) {
    assert.equal(verifyKiroDocument(document, context).length, 2);
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
    [{ ...entries[0], repositoryBranch: 'obsolete' }, /expected branch main, found obsolete/],
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
    ...entries, { ...entries[0], repositoryBranch: 'obsolete' },
  ]), context), /expected branch main, found obsolete/);
});

test('main is a moving source and verification records its observed commit', async (t) => {
  let branchCommit = 'b'.repeat(40);
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === provider.directoryUrl) return new Response(flightDocument(entries));
    assert.equal(url, 'https://api.github.com/repos/qodo-ai/qodo-skills/commits/main');
    return new Response(JSON.stringify({ sha: branchCommit }));
  });
  for (const commit of ['b'.repeat(40), context.commit]) {
    branchCommit = commit;
    const results = await verifyMarketplace('kiro', context);
    assert.equal(results.length, 2);
    assert.ok(results.every((entry) => entry.commit === commit && entry.branch === 'main'));
  }
  for (const invalid of [undefined, 'main', '', 'b'.repeat(39)]) {
    branchCommit = invalid;
    await assert.rejects(verifyMarketplace('kiro', context), /could not resolve a valid commit for main/);
  }
});

test('older immutable contracts retain their exact release-branch requirement', async (t) => {
  const previous = { ...provider, mode: 'protected-release-branch', sourceRef: 'marketplace-kiro' };
  const previousEntries = entries.map((entry) => ({ ...entry,
    repositoryBranch: previous.sourceRef,
    repositoryUrl: entry.repositoryUrl.replace('/tree/main/', '/tree/marketplace-kiro/'),
  }));
  let branchCommit = 'b'.repeat(40);
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === provider.directoryUrl) return new Response(flightDocument(previousEntries));
    assert.equal(url, 'https://api.github.com/repos/qodo-ai/qodo-skills/commits/marketplace-kiro');
    return new Response(JSON.stringify({ sha: branchCommit }));
  });
  await assert.rejects(verifyMarketplace('kiro', context, previous), /not release commit/);
  branchCommit = context.commit;
  assert.equal((await verifyMarketplace('kiro', context, previous)).length, 2);
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
    assert.match(readFileSync(join(packet.output, 'SUBMISSION.md'), 'utf8'), /moving source/);
    assert.ok(desired.every((entry) => entry.repositoryBranch === 'main'));
    assert.equal(desired[0].displayName, provider.listings[0].displayName);
    assert.equal(desired[0].description, provider.listings[0].description);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { codexListingInterface, validateStarterPrompts } from '../scripts/codex-portal-contract.mjs';
import { createDeterministicZip } from '../scripts/deterministic-zip.mjs';
import { prepareMarketplace } from '../scripts/marketplace-release.mjs';
import { verifyCodexPacket } from '../scripts/verify-codex-packet.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const json = (path) => JSON.parse(readFileSync(path, 'utf8'));
const catalog = json(join(root, 'distribution/catalog.json'));
const submissions = json(join(root, 'distribution/codex-submissions.json'));
const context = { tag: `v${catalog.package.version}`, version: catalog.package.version,
  commit: '0123456789abcdef0123456789abcdef01234567', release: {} };
const writeJson = (path, value) => writeFileSync(path, JSON.stringify(value));

test('starter selection is independent of installed skills and cannot cross package boundaries', () => {
  const submission = submissions.listings[0];
  const ui = codexListingInterface(catalog, submission);
  assert.equal(ui.defaultPrompt.length, 3);
  assert.equal(catalog.installPackages[0].skills.length, 4);
  assert.ok(catalog.installPackages[0].skills.includes('qodo-setup'));
  for (const names of [[], ['qodo-get-rules'], ['qodo-review', 'qodo-review'],
    catalog.installPackages[0].skills, ['unknown']]) {
    assert.throws(() => codexListingInterface(catalog, { ...submission, starterSkills: names }), /starterSkills/);
  }
  assert.throws(() => codexListingInterface(catalog, { ...submission, shortDescription: 'x'.repeat(31) }),
    /shortDescription/);
});

test('directory prompt limits reject too many, blank, duplicate, multiline, long and app-mention prompts', () => {
  assert.deepEqual(validateStarterPrompts(['Review my code']), ['Review my code']);
  for (const prompts of [undefined, [], ['a', 'b', 'c', 'd'], [''], [null], ['x'.repeat(129)],
    ['a\nb'], ['a\u2028b'], ['Use @app'], ['Review  code', 'Review code'], ['Café', 'Cafe\u0301']]) {
    assert.throws(() => validateStarterPrompts(prompts), /Codex defaultPrompt/);
  }
});

function packetFixture(operation) {
  const temporary = mkdtempSync(join(tmpdir(), 'qodo-codex-contract-'));
  try {
    const { output } = prepareMarketplace('codex', context, join(temporary, 'packet'));
    operation(output);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

// Rebuild and rebind all hashes so each failure exercises the actual internal
// contract, not an incidental checksum mismatch.
function repack(output, mutate) {
  const listing = join(output, 'listings/qodo');
  const manifestPath = join(listing, '.codex-plugin/plugin.json');
  const plugin = json(manifestPath);
  mutate(plugin, listing);
  writeJson(manifestPath, plugin);
  const release = json(join(output, 'release.json'));
  const artifact = release.artifacts.find((entry) => entry.listingId === 'qodo');
  const bundle = createDeterministicZip(listing, join(output, artifact.path));
  Object.assign(artifact, { sha256: bundle.sha256, sizeBytes: bundle.sizeBytes });
  writeJson(join(output, 'release.json'), release);
  const submissionPath = join(output, 'submissions/qodo.json');
  const submission = json(submissionPath);
  submission.artifact = artifact;
  submission.listing.starterPrompts = plugin.interface.defaultPrompt;
  submission.listing.shortDescription = plugin.interface.shortDescription;
  writeJson(submissionPath, submission);
  writeFileSync(join(output, 'bundles/SHA256SUMS'),
    release.artifacts.map((entry) => `${entry.sha256}  ${entry.path.slice(8)}\n`).join(''));
}

function mutateArchive(output, mutate) {
  const release = json(join(output, 'release.json'));
  const artifact = release.artifacts.find((entry) => entry.listingId === 'qodo');
  const path = join(output, artifact.path);
  const bytes = readFileSync(path);
  const centralOffset = bytes.readUInt32LE(bytes.length - 6);
  const changed = mutate(bytes, centralOffset) ?? bytes;
  writeFileSync(path, changed);
  artifact.sha256 = createHash('sha256').update(changed).digest('hex');
  artifact.sizeBytes = changed.length;
  writeJson(join(output, 'release.json'), release);
  const submissionPath = join(output, 'submissions/qodo.json');
  const submission = json(submissionPath);
  submission.artifact = artifact;
  writeJson(submissionPath, submission);
  writeFileSync(join(output, 'bundles/SHA256SUMS'),
    release.artifacts.map((entry) => `${entry.sha256}  ${entry.path.slice(8)}\n`).join(''));
}

test('central-only generic manifest is rejected with all packet hashes rebound', () => packetFixture((output) => {
  repack(output, (plugin, path) => writeJson(join(path, 'plubin.json'), plugin));
  mutateArchive(output, (bytes, centralOffset) => {
    const nameOffset = bytes.indexOf(Buffer.from('plubin.json'), centralOffset);
    assert.ok(nameOffset > centralOffset);
    Buffer.from('plugin.json').copy(bytes, nameOffset);
  });
  assert.throws(() => verifyCodexPacket(output), /central directory does not match/);
}));

for (const [name, mutate] of [
  ['central flags', (bytes, offset) => { bytes[offset + 8] ^= 1; }],
  ['central method', (bytes, offset) => { bytes[offset + 10] ^= 1; }],
  ['central CRC', (bytes, offset) => { bytes[offset + 16] ^= 1; }],
  ['central size', (bytes, offset) => { bytes[offset + 20] ^= 1; }],
  ['central local offset', (bytes, offset) => { bytes[offset + 42] ^= 1; }],
  ['extra central entry', (bytes, offset) => {
    const firstEnd = offset + 46 + bytes.readUInt16LE(offset + 28);
    return Buffer.concat([bytes.subarray(0, -22), bytes.subarray(offset, firstEnd), bytes.subarray(-22)]);
  }],
  ['local CRC', (bytes) => { bytes[14] ^= 1; }],
  ['local flags', (bytes) => { bytes[6] ^= 1; }],
  ['local name', (bytes) => { bytes[30] = '/'.charCodeAt(0); }],
  ['end record count', (bytes) => { bytes[bytes.length - 14] ^= 1; }],
  ['end record offset', (bytes) => { bytes[bytes.length - 6] ^= 1; }],
  ['truncated central directory', (bytes, offset) => bytes.subarray(0, offset + 10)],
  ['truncated end record', (bytes) => bytes.subarray(0, -1)],
  ['trailing bytes', (bytes) => Buffer.concat([bytes, Buffer.from('extra')])],
]) {
  test(`ZIP verification rejects ${name} with all packet hashes rebound`, () => packetFixture((output) => {
    mutateArchive(output, mutate);
    assert.throws(() => verifyCodexPacket(output), /Invalid deterministic ZIP/);
  }));
}

test('portable verifier and generated skill interfaces remain complete', () => packetFixture((output) => {
  const run = spawnSync(process.execPath, ['verify-codex-packet.mjs'], { cwd: output, encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(JSON.parse(run.stdout).verified.length, 2);
  for (const pkg of catalog.installPackages) {
    const directory = join(output, 'listings', pkg.name);
    assert.throws(() => readFileSync(join(directory, 'plugin.json')), /ENOENT/);
    const manifest = json(join(directory, '.codex-plugin/plugin.json'));
    assert.equal(manifest.interface.composerIcon, manifest.interface.logo);
    assert.equal(createHash('sha256').update(readFileSync(join(directory, 'assets/qodo.png'))).digest('hex'),
      '3b55f9064c1bd1c68de454db1c0056baaf3d881946770a94dc7252f3ce1ebeab');
    const skills = pkg.name === 'qodo' ? [...pkg.skills, 'qodo-pr-resolver'] : pkg.skills;
    for (const name of skills) {
      const yaml = readFileSync(join(directory, 'skills', name, 'agents/openai.yaml'), 'utf8');
      for (const field of ['display_name', 'short_description', 'default_prompt']) {
        assert.match(yaml, new RegExp(`^  ${field}: .+`, 'm'));
      }
      const skill = readFileSync(join(directory, 'skills', name, 'SKILL.md'), 'utf8');
      assert.match(skill, /^metadata:$/m);
      assert.match(skill, /^  version: /m);
      assert.match(skill, /^  distribution: "marketplace"$/m);
    }
  }
}));

for (const [name, mutate, expected] of [
  ['four prompts', (plugin) => plugin.interface.defaultPrompt.push('Fourth prompt'), /one to three/],
  ['missing logo', (plugin) => delete plugin.interface.logo, /branding/],
  ['unsafe asset path', (plugin) => plugin.interface.logo = '../qodo.png', /branding/],
  ['missing asset', (_, path) => rmSync(join(path, 'assets/qodo.png')), /missing assets\/qodo.png/],
  ['non-square image', (_, path) => {
    const bytes = readFileSync(join(path, 'assets/qodo.png'));
    bytes.writeUInt32BE(200, 20);
    writeFileSync(join(path, 'assets/qodo.png'), bytes);
  }, /square/],
  ['wrong image encoding', (_, path) => writeFileSync(join(path, 'assets/qodo.png'), 'not PNG'), /PNG/],
  ['generic root manifest', (plugin, path) => writeJson(join(path, 'plugin.json'), plugin), /only the native/],
]) {
  test(`ZIP verification rejects ${name} even with consistent hashes`, () => packetFixture((output) => {
    repack(output, mutate);
    assert.throws(() => verifyCodexPacket(output), expected);
  }));
}

test('submission prompt drift is rejected', () => packetFixture((output) => {
  const path = join(output, 'submissions/qodo.json');
  const submission = json(path);
  submission.listing.starterPrompts = ['Different prompt'];
  writeJson(path, submission);
  assert.throws(() => verifyCodexPacket(output), /submission interface/);
}));

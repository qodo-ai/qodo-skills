import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { buildRepositoryCatalog, writeRepositoryCatalog } from '../scripts/build-repository-catalog.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const sha = 'a'.repeat(40);

test('all canonical resources and component terms survive the standalone catalog', () => {
  const before = readFileSync(join(root, 'distribution/qodo-cli-managed-bundle.json'));
  const bundle = buildRepositoryCatalog(root, sha);
  const cockpit = bundle.skills.find((skill) => skill.name === 'qodo-review-cockpit');
  assert.equal(cockpit.package, 'qodo-cockpit');
  assert.ok(cockpit.files.length > 90);
  assert.ok(cockpit.files.some((file) => file.path === 'runtime/LICENSE'));
  for (const skill of bundle.skills) for (const file of skill.files) {
    const source = readFileSync(join(root, 'skills', skill.name, file.path));
    assert.ok(Buffer.from(file.content, 'base64').equals(source));
    assert.equal(file.executable, Boolean(statSync(join(root, 'skills', skill.name, file.path)).mode & 0o111));
    assert.equal(file.sha256, createHash('sha256').update(source).digest('hex'));
  }
  const flags = bundle.installPackages.find((pkg) => pkg.name === 'qodo-cockpit');
  assert.equal(flags.default, false); assert.equal(flags.managed, false); assert.equal(flags.providerListed, false);
  assert.deepEqual(readFileSync(join(root, 'distribution/qodo-cli-managed-bundle.json')), before);
});

test('output is deterministic and checksummed without a package/name allowlist', (t) => {
  const dir = mkdtempSync(join(tmpdir(), 'repository-catalog-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  mkdirSync(join(dir, 'distribution')); mkdirSync(join(dir, 'skills/qodo-future-skill'), { recursive: true });
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify({ package: { version: '1.2.3', repository: 'https://github.com/qodo-ai/qodo-skills' }, runtime: { minimumCliVersion: '2.0.0' }, installPackages: [{ name: 'qodo-future', default: false, skills: ['qodo-future-skill'] }], skills: [{ name: 'qodo-future-skill', version: '1.0.0', recommended: false, displayName: 'Future', shortDescription: 'Future', defaultPrompt: 'Future' }] }));
  writeFileSync(join(dir, 'skills/qodo-future-skill/SKILL.md'), 'future');
  writeRepositoryCatalog(dir, sha, join(dir, 'out'));
  const first = readFileSync(join(dir, 'out/qodo-repository-catalog.json'));
  assert.equal(JSON.parse(first).minimumCliVersion, '2.3.0');
  writeRepositoryCatalog(dir, sha, join(dir, 'out'));
  assert.deepEqual(readFileSync(join(dir, 'out/qodo-repository-catalog.json')), first);
  assert.equal(JSON.parse(first).skills[0].package, 'qodo-future');
  assert.ok(readFileSync(join(dir, 'out/qodo-repository-catalog.json.sha256'), 'utf8').startsWith(createHash('sha256').update(first).digest('hex')));
  writeFileSync(join(dir, 'skills/qodo-future-skill/large.bin'), Buffer.alloc(512 * 1024 + 1));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /budget/);
  rmSync(join(dir, 'skills/qodo-future-skill/large.bin'));
  symlinkSync('SKILL.md', join(dir, 'skills/qodo-future-skill/link'));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /symlink/);
});

test('catalog prereleases address drafts by ID, resume partial uploads and enforce immutable publication', async (t) => {
  const { publishRepositorySnapshot } = await import('../scripts/publish-repository-catalog.mjs');
  const dir = mkdtempSync(join(tmpdir(), 'repository-publish-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const remote = new Map(); let release; let writes = 0; let failUpload = true; let immutable = true; let tagCreated = false;
  const run = (command, args) => {
    if (command === 'git') {
      if (args[0] === 'rev-parse') return sha;
      if (args[0] === 'remote') return 'git@github.com:qodo-ai/qodo-skills.git';
      if (args[0] === 'ls-remote' && tagCreated) return `${sha} refs/tags/catalog-${sha}`;
      return '';
    }
    assert.equal(command, 'gh'); assert.equal(args[0], 'api', 'draft tag commands must not be used');
    const method = args.includes('--method') ? args[args.indexOf('--method') + 1] : 'GET';
    const endpoint = args.find((arg) => arg.startsWith('repos/') || arg.startsWith('https:'));
    if (endpoint.endsWith('?per_page=100')) return JSON.stringify([release ? [{ ...release, assets: [...remote.values()].map(({ id, name }) => ({ id, name })) }] : []]);
    if (method === 'POST' && endpoint === 'repos/qodo-ai/qodo-skills/releases') {
      writes++; assert.ok(args.includes('prerelease=true')); assert.ok(args.includes('make_latest=false'));
      release = { id: 17, tag_name: `catalog-${sha}`, target_commitish: sha, draft: true, prerelease: true, immutable: false, assets: [], upload_url: 'https://uploads.github.com/repos/qodo-ai/qodo-skills/releases/17/assets{?name,label}' };
      return JSON.stringify(release);
    }
    if (method === 'POST') {
      if (failUpload && remote.size === 1) { failUpload = false; throw new Error('interrupted upload'); }
      const name = new URL(endpoint).searchParams.get('name'); assert.ok(!remote.has(name), 'never replace assets');
      writes++; remote.set(name, { id: remote.size + 100, name, content: readFileSync(args[args.indexOf('--input') + 1]) }); return '{}';
    }
    if (method === 'PATCH') {
      writes++; release.draft = args.includes('draft=true'); release.immutable = !release.draft && immutable; tagCreated ||= !release.draft; return JSON.stringify(release);
    }
    if (endpoint.includes('/assets/')) {
      const asset = [...remote.values()].find((item) => String(item.id) === endpoint.split('/').at(-1)); return asset.content.toString('utf8');
    }
    return JSON.stringify({ ...release, assets: [...remote.values()].map(({ id, name }) => ({ id, name })) });
  };
  const options = { repositoryRoot: root, sourceCommit: sha, outputDirectory: dir, run };
  assert.throws(() => publishRepositorySnapshot(options), /interrupted upload/);
  assert.equal(release.draft, true); assert.equal(remote.size, 1);
  assert.equal(publishRepositorySnapshot(options).marketplacePublication, false);
  const publishedWrites = writes; publishRepositorySnapshot(options); assert.equal(writes, publishedWrites);
  const asset = remote.get('qodo-repository-catalog.json'); remote.set(asset.name, { ...asset, content: Buffer.from('changed') });
  assert.throws(() => publishRepositorySnapshot(options), /immutable/); assert.equal(writes, publishedWrites);
  remote.set(asset.name, asset); release.draft = true; immutable = false;
  assert.throws(() => publishRepositorySnapshot(options), /mutable/); assert.equal(release.draft, true);
  const workflow = readFileSync(join(root, '.github/workflows/repository-catalog.yml'), 'utf8');
  assert.ok(workflow.includes('workflow_dispatch:')); assert.ok(!workflow.includes('publish-release.sh'));
  assert.ok(!workflow.includes('marketplace-release.mjs'));
  assert.ok(workflow.includes('ref: ${{ github.sha }}'));
  assert.ok(workflow.includes('git worktree add --detach'));
  assert.ok(workflow.includes('SOURCE_ROOT: ${{ runner.temp }}/catalog-source'));
  assert.ok(!workflow.includes('git checkout --detach'), 'publisher must stay in the trusted workflow checkout');
});

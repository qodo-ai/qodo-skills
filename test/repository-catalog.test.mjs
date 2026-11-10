import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
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

test('catalog prereleases resume safely and never overwrite published bytes or run marketplace publication', async (t) => {
  const { publishRepositorySnapshot } = await import('../scripts/publish-repository-catalog.mjs');
  const dir = mkdtempSync(join(tmpdir(), 'repository-publish-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const remote = new Map(); let release; let writes = 0;
  const run = (command, args) => {
    if (command === 'git') {
      if (args[0] === 'rev-parse') return sha;
      if (args[0] === 'remote') return 'git@github.com:qodo-ai/qodo-skills.git';
      return '';
    }
    assert.equal(command, 'gh'); assert.equal(args[0], 'release'); assert.equal(args.at(-1), 'qodo-ai/qodo-skills');
    if (args[1] === 'view') { if (!release) throw new Error('release not found'); return JSON.stringify({ ...release, assets: [...remote.keys()].map((name) => ({ name })) }); }
    if (args[1] === 'create') { writes++; assert.ok(args.includes('--prerelease')); assert.ok(args.includes('--latest=false')); release = { isDraft: true, isPrerelease: true }; }
    if (args[1] === 'upload') { writes++; assert.ok(!args.includes('--clobber')); const path = args[3]; remote.set(path.split('/').at(-1), readFileSync(path)); }
    if (args[1] === 'download') { const name = args[args.indexOf('--pattern') + 1]; writeFileSync(join(args[args.indexOf('--dir') + 1], name), remote.get(name)); }
    if (args[1] === 'edit') { writes++; release.isDraft = false; }
    return '';
  };
  const options = { repositoryRoot: root, sourceCommit: sha, outputDirectory: dir, run };
  assert.equal(publishRepositorySnapshot(options).marketplacePublication, false);
  const publishedWrites = writes; publishRepositorySnapshot(options); assert.equal(writes, publishedWrites);
  remote.set('qodo-repository-catalog.json', Buffer.from('changed'));
  assert.throws(() => publishRepositorySnapshot(options), /immutable/); assert.equal(writes, publishedWrites);
  const workflow = readFileSync(join(root, '.github/workflows/repository-catalog.yml'), 'utf8');
  assert.ok(workflow.includes('workflow_dispatch:')); assert.ok(!workflow.includes('publish-release.sh'));
  assert.ok(!workflow.includes('marketplace-release.mjs'));
});

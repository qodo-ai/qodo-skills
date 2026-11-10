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
  const base = JSON.parse(readFileSync(join(root, 'distribution/catalog.json'), 'utf8'));
  const fixture = { ...base, package: { ...base.package, version: '1.2.3' }, runtime: { ...base.runtime, minimumCliVersion: '2.0.0' },
    installPackages: [{ ...base.installPackages[0], name: 'qodo-future', compatibilityAliases: {}, skills: ['qodo-future-skill'] }, { ...base.installPackages[1], name: 'qodo-next--', compatibilityAliases: {}, skills: ['qodo-z--future-'] }],
    skills: ['qodo-future-skill', 'qodo-z--future-'].map((name) => ({ ...base.skills[0], name })) };
  mkdirSync(join(dir, 'skills/qodo-z--future-'), { recursive: true });
  const document = (name, pkg, body) => `---\nname: ${name}\ndescription: A fixture skill.\nowner: Qodo\nmetadata:\n  vendor: qodo\n  distribution: skills-sh\n  version: "${base.skills[0].version}"\n  recommended: "true"\n  package: "${pkg}"\n---\n${body}`;
  writeFileSync(join(dir, 'skills/qodo-z--future-/SKILL.md'), document('qodo-z--future-', 'qodo-next--', 'second'));
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  const skillPath = join(dir, 'skills/qodo-future-skill/SKILL.md');
  const original = document('qodo-future-skill', 'qodo-future', 'future');
  writeFileSync(skillPath, original);
  writeRepositoryCatalog(dir, sha, join(dir, 'out'));
  const first = readFileSync(join(dir, 'out/qodo-repository-catalog.json'));
  assert.equal(JSON.parse(first).minimumCliVersion, '2.3.0');
  for (const [from, to] of [['description: A fixture skill.', 'description:'], ['owner: Qodo', 'owner: Other'], ['vendor: qodo', 'vendor: other'], ['distribution: skills-sh', 'distribution: other'], ['recommended: \"true\"', 'recommended: \"invalid\"'], ['name: qodo-future-skill', 'name: qodo-wrong'], [`version: \"${base.skills[0].version}\"`, 'version: \"999.0.0\"'], ['recommended: \"true\"', 'recommended: \"false\"'], ['package: \"qodo-future\"', 'package: \"qodo-wrong\"']]) {
    writeFileSync(skillPath, original.replace(from, to));
    assert.throws(() => buildRepositoryCatalog(dir, sha), /frontmatter differs/);
  }
  writeFileSync(skillPath, original);
  const aliases = fixture.installPackages[0].compatibilityAliases;
  fixture.installPackages[0].compatibilityAliases = { missing: 'qodo-missing' };
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /compatibility alias/);
  fixture.installPackages[0].compatibilityAliases = { shared: 'qodo-future-skill' };
  fixture.installPackages[1].compatibilityAliases = { shared: 'qodo-z--future-' };
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /compatibility alias/);
  fixture.installPackages[1].compatibilityAliases = {};
  fixture.installPackages[0].compatibilityAliases = aliases;
  writeFileSync(skillPath, original.replace('  recommended: \"true\"\n', ''));
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.equal(buildRepositoryCatalog(dir, sha).skills[0].recommended, true);
  writeFileSync(skillPath, original);
  fixture.runtime.minimumCliVersion = '2.4.0+build.1'; fixture.package.version = '1.2.3+build.2';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.equal(buildRepositoryCatalog(dir, sha).minimumCliVersion, '2.4.0+build.1');
  delete fixture.package.version; writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /metadata/);
  fixture.package.version = '1.2.3\n'; writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /metadata/);
  fixture.package.version = '1.2.3'; fixture.runtime.minimumCliVersion = '2.0.0\n';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /metadata|minimum CLI/);
  fixture.runtime.minimumCliVersion = '2.0.0';
  const initialSkills = fixture.skills, initialPackages = fixture.installPackages;
  fixture.skills = Array.from({ length: 501 }, () => initialSkills[0]);
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /metadata/);
  fixture.skills = initialSkills; fixture.installPackages = Array.from({ length: 101 }, () => initialPackages[0]);
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /metadata/);
  fixture.installPackages = initialPackages;
  fixture.package.version = '1.2.3'; fixture.runtime.minimumCliVersion = '2.0.0';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  fixture.installPackages[1].name = fixture.installPackages[0].name;
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /Duplicate repository package/);
  fixture.installPackages[1].name = 'qodo-next--'; writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  mkdirSync(join(dir, 'skills/qodo-unlisted')); writeFileSync(join(dir, 'skills/qodo-unlisted/SKILL.md'), 'unlisted');
  assert.throws(() => buildRepositoryCatalog(dir, sha), /Uncatalogued/);
  rmSync(join(dir, 'skills/qodo-unlisted'), { recursive: true });
  writeRepositoryCatalog(dir, sha, join(dir, 'out'));
  assert.deepEqual(readFileSync(join(dir, 'out/qodo-repository-catalog.json')), first);
  assert.equal(JSON.parse(first).skills[0].package, 'qodo-future');
  assert.ok(readFileSync(join(dir, 'out/qodo-repository-catalog.json.sha256'), 'utf8').startsWith(createHash('sha256').update(first).digest('hex')));
  writeFileSync(join(dir, 'skills/qodo-future-skill/large.bin'), Buffer.alloc(512 * 1024 + 1));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /budget/);
  rmSync(join(dir, 'skills/qodo-future-skill/large.bin'));
  if (process.platform !== 'win32') {
    writeFileSync(join(dir, 'skills/qodo-future-skill/NUL'), 'not portable');
    assert.throws(() => buildRepositoryCatalog(dir, sha), /Unsafe/);
    rmSync(join(dir, 'skills/qodo-future-skill/NUL'));
  }
  for (const name of ['é.txt', 'e\u0301.txt', 'ς.txt', 'σ.txt']) {
    const path = join(dir, 'skills/qodo-future-skill', name); writeFileSync(path, 'data');
    const found = buildRepositoryCatalog(dir, sha).skills[0].files.find((file) => file.path.normalize('NFC') === name.normalize('NFC'));
    assert.ok(found); assert.equal(Buffer.from(found.content, 'base64').toString('utf8'), 'data');
    rmSync(path);
  }
  const multilingual = 'שלום 世界 σς';
  writeFileSync(join(dir, 'skills/qodo-future-skill/international.txt'), multilingual);
  const resource = buildRepositoryCatalog(dir, sha).skills[0].files.find((file) => file.path === 'international.txt');
  assert.equal(Buffer.from(resource.content, 'base64').toString('utf8'), multilingual);
  symlinkSync('SKILL.md', join(dir, 'skills/qodo-future-skill/link'));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /symlink/);
});

test('Unicode comparison covers the pinned full-fold mapping and Windows aliases', async () => {
  const { resourcePathKeys } = await import('../scripts/resource-path-keys.mjs');
  const data = JSON.parse(readFileSync(join(root, 'scripts/unicode-casefold.json'), 'utf8'));
  assert.equal(data.unicodeVersion, '17.0.0'); assert.equal(data.sourceSha256, 'ff8d8fefbf123574205085d6714c36149eb946d717a0c585c27f0f4ef58c4183');
  for (const [source, folded] of Object.entries(data.fold)) assert.equal(resourcePathKeys(source)[0], resourcePathKeys(folded)[0]);
  assert.ok(resourcePathKeys('assets/ς.txt').some((key) => resourcePathKeys('assets/σ.txt').includes(key)));
  assert.ok(resourcePathKeys('assets/é.txt').some((key) => resourcePathKeys('assets/e\u0301.txt').includes(key)));
  assert.ok(resourcePathKeys('assets/ı.txt').some((key) => resourcePathKeys('assets/i.txt').includes(key)));
});

test('catalog prereleases address drafts by ID, resume partial uploads and enforce immutable publication', async (t) => {
  const { publishRepositorySnapshot } = await import('../scripts/publish-repository-catalog.mjs');
  const dir = mkdtempSync(join(tmpdir(), 'repository-publish-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const remote = new Map(); let release; let writes = 0; let failUpload = true; let immutable = true; let tagCreated = false; let competingTag = false; let nextAssetId = 100;
  const run = (command, args) => {
    if (command === 'git') {
      if (args[0] === 'rev-parse') return sha;
      if (args[0] === 'remote') return 'git@github.com:qodo-ai/qodo-skills.git';
      if (args[0] === 'ls-remote' && tagCreated) return `${competingTag ? 'b'.repeat(40) : sha} refs/tags/catalog-${sha}`;
      return '';
    }
    assert.equal(command, 'gh'); assert.equal(args[0], 'api', 'draft tag commands must not be used');
    const method = args.includes('--method') ? args[args.indexOf('--method') + 1] : 'GET';
    const endpoint = args.find((arg) => arg.startsWith('repos/') || arg.startsWith('https:'));
    if (method === 'POST' && endpoint.endsWith('/git/refs')) {
      writes++; assert.ok(args.includes(`ref=refs/tags/catalog-${sha}`)); assert.ok(args.includes(`sha=${sha}`));
      assert.equal(tagCreated, false); tagCreated = true;
      if (competingTag) throw new Error('competing tag creator won');
      return '{}';
    }
    if (endpoint.endsWith('?per_page=100')) return JSON.stringify([release ? [{ ...release, assets: [...remote.values()].map(({ id, name, state }) => ({ id, name, state })) }] : []]);
    if (method === 'POST' && endpoint === 'repos/qodo-ai/qodo-skills/releases') {
      writes++; assert.ok(args.includes('prerelease=true')); assert.ok(args.includes('make_latest=false'));
      release = { id: 17, tag_name: `catalog-${sha}`, target_commitish: sha, draft: true, prerelease: true, immutable: false, assets: [], upload_url: 'https://uploads.github.com/repos/qodo-ai/qodo-skills/releases/17/assets{?name,label}' };
      return JSON.stringify(release);
    }
    if (method === 'POST') {
      const name = new URL(endpoint).searchParams.get('name'); assert.ok(!remote.has(name), 'never replace assets');
      if (failUpload && remote.size === 1) {
        failUpload = false; remote.set(name, { id: nextAssetId++, name, state: 'starter', content: Buffer.alloc(0) });
        throw new Error('interrupted upload');
      }
      writes++; remote.set(name, { id: nextAssetId++, name, state: 'uploaded', content: readFileSync(args[args.indexOf('--input') + 1]) }); return '{}';
    }
    if (method === 'DELETE') {
      const asset = [...remote.values()].find((item) => String(item.id) === endpoint.split('/').at(-1));
      assert.equal(release.draft, true); assert.equal(asset.state, 'starter', 'never delete uploaded bytes');
      writes++; remote.delete(asset.name); return '';
    }
    if (method === 'PATCH') {
      if (args.includes('draft=false')) assert.equal(tagCreated, true, 'reserve the source before immutable publication');
      writes++; release.draft = args.includes('draft=true'); release.immutable = !release.draft && immutable; tagCreated ||= !release.draft; return JSON.stringify(release);
    }
    if (endpoint.includes('/assets/')) {
      const asset = [...remote.values()].find((item) => String(item.id) === endpoint.split('/').at(-1)); return asset.content.toString('utf8');
    }
    return JSON.stringify({ ...release, assets: [...remote.values()].map(({ id, name, state }) => ({ id, name, state })) });
  };
  const options = { repositoryRoot: root, sourceCommit: sha, outputDirectory: dir, run };
  assert.throws(() => publishRepositorySnapshot(options), /interrupted upload/);
  assert.equal(release.draft, true); assert.equal(remote.size, 2);
  assert.equal([...remote.values()].filter((asset) => asset.state === 'starter').length, 1);
  assert.equal(publishRepositorySnapshot(options).marketplacePublication, false);
  const publishedWrites = writes; publishRepositorySnapshot(options); assert.equal(writes, publishedWrites);
  const asset = remote.get('qodo-repository-catalog.json'); remote.set(asset.name, { ...asset, content: Buffer.from('changed') });
  assert.throws(() => publishRepositorySnapshot(options), /immutable/); assert.equal(writes, publishedWrites);
  release.draft = true;
  assert.throws(() => publishRepositorySnapshot(options), /immutable/);
  assert.equal(writes, publishedWrites, 'an uploaded draft asset with changed bytes requires an explicit recovery choice');
  remote.set(asset.name, asset); release.draft = true; immutable = false;
  assert.throws(() => publishRepositorySnapshot(options), /mutable/); assert.equal(release.draft, true);
  tagCreated = false; competingTag = true;
  assert.throws(() => publishRepositorySnapshot(options), /existing tag must name the same source/);
  assert.equal(release.draft, true, 'a wrong competing tag must never publish the draft');
  const workflow = readFileSync(join(root, '.github/workflows/repository-catalog.yml'), 'utf8');
  assert.ok(workflow.includes('workflow_dispatch:')); assert.ok(!workflow.includes('publish-release.sh'));
  assert.ok(!workflow.includes('marketplace-release.mjs'));
  assert.ok(workflow.includes('ref: ${{ github.sha }}'));
  assert.ok(workflow.includes('git worktree add --detach'));
  assert.ok(workflow.includes('SOURCE_ROOT: ${{ runner.temp }}/catalog-source'));
  assert.ok(!workflow.includes('git checkout --detach'), 'publisher must stay in the trusted workflow checkout');
});


test('publisher command transport carries a catalog larger than the default Node buffer', async () => {
  const { runRepositoryPublisherCommand } = await import('../scripts/publish-repository-catalog.mjs');
  const bytes = runRepositoryPublisherCommand(root, process.execPath, ['-e', "process.stdout.write('x'.repeat(2 * 1024 * 1024))"]);
  assert.equal(Buffer.byteLength(bytes), 2 * 1024 * 1024);
});

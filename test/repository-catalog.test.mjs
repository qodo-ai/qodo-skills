import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync, statSync, renameSync } from 'node:fs';
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
  const cockpit = bundle.skills.find((skill) => skill.name === 'qodo-agent-session-review');
  assert.equal(cockpit.package, 'qodo-agent-session-review');
  assert.ok(cockpit.files.length > 90);
  assert.ok(cockpit.files.some((file) => file.path === 'runtime/LICENSE'));
  for (const skill of bundle.skills) for (const file of skill.files) {
    const source = readFileSync(join(root, 'skills', skill.name, file.path));
    assert.ok(Buffer.from(file.content, 'base64').equals(source));
    assert.equal(file.executable, Boolean(statSync(join(root, 'skills', skill.name, file.path)).mode & 0o111));
    assert.equal(file.sha256, createHash('sha256').update(source).digest('hex'));
  }
  const flags = bundle.installPackages.find((pkg) => pkg.name === 'qodo-agent-session-review');
  assert.equal(flags.default, false); assert.equal(flags.managed, false); assert.equal(flags.providerListed, false);
  assert.deepEqual(readFileSync(join(root, 'distribution/qodo-cli-managed-bundle.json')), before);
});

test('output is deterministic and checksummed without a package/name allowlist', (t) => {
  const dir = mkdtempSync(join(tmpdir(), 'repository-catalog-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  mkdirSync(join(dir, 'distribution')); mkdirSync(join(dir, 'skills/qodo-future-skill'), { recursive: true });
  const base = JSON.parse(readFileSync(join(root, 'distribution/catalog.json'), 'utf8'));
  const fixture = { ...base, package: { ...base.package, name: 'qodo-future', version: '1.2.3' }, runtime: { ...base.runtime, minimumCliVersion: '2.0.0' },
    installPackages: [{ ...base.installPackages[0], name: 'qodo-future', compatibilityAliases: {}, skills: ['qodo-future-skill'] }, { ...base.installPackages[1], name: 'qodo-next', compatibilityAliases: {}, skills: ['qodo-z-future'] }],
    skills: ['qodo-future-skill', 'qodo-z-future'].map((name, index) => ({ ...base.skills[0], name, recommended: index === 0 })) };
  mkdirSync(join(dir, 'skills/qodo-z-future'), { recursive: true });
  const document = (name, pkg, body) => `---\nname: ${name}\ndescription: A fixture skill.\nowner: Qodo\nmetadata:\n  vendor: qodo\n  distribution: skills-sh\n  version: "${base.skills[0].version}"\n  recommended: "${pkg === 'qodo-future'}"\n  package: "${pkg}"\n---\n${body}`;
  writeFileSync(join(dir, 'skills/qodo-z-future/SKILL.md'), document('qodo-z-future', 'qodo-next', 'second'));
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  const skillPath = join(dir, 'skills/qodo-future-skill/SKILL.md');
  const original = document('qodo-future-skill', 'qodo-future', 'future');
  writeFileSync(skillPath, original);
  writeRepositoryCatalog(dir, sha, join(dir, 'out'));
  const first = readFileSync(join(dir, 'out/qodo-repository-catalog.json'));
  assert.equal(JSON.parse(first).minimumCliVersion, '2.3.0');
  for (const invalid of ['qodo--future', 'qodo-future-']) {
    fixture.skills[0].name = invalid; fixture.installPackages[0].skills = [invalid];
    renameSync(join(dir, 'skills/qodo-future-skill'), join(dir, 'skills', invalid));
    writeFileSync(join(dir, 'skills', invalid, 'SKILL.md'), document(invalid, 'qodo-future', 'future'));
    writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
    assert.throws(() => buildRepositoryCatalog(dir, sha), /skill identity/);
    renameSync(join(dir, 'skills', invalid), join(dir, 'skills/qodo-future-skill'));
  }
  fixture.skills[0].name = 'qodo-future-skill'; fixture.installPackages[0].skills = ['qodo-future-skill'];
  writeFileSync(skillPath, original);
  fixture.installPackages[1].name = 'qodo-next--';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /package membership/);
  fixture.installPackages[1].name = 'qodo-next';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));

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
  fixture.installPackages[1].compatibilityAliases = { shared: 'qodo-z-future' };
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /compatibility alias/);
  fixture.installPackages[1].compatibilityAliases = {};
  fixture.installPackages[0].compatibilityAliases = aliases;
  fixture.installPackages[1].default = true;
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /default package/);
  fixture.installPackages[1].default = false;
  fixture.package.name = 'qodo-wrong';
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /default package/);
  fixture.package.name = 'qodo-future';
  fixture.skills[1].recommended = true;
  const secondPath = join(dir, 'skills/qodo-z-future/SKILL.md');
  writeFileSync(secondPath, document('qodo-z-future', 'qodo-next', 'second').replace('recommended: \"false\"', 'recommended: \"true\"'));
  writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
  assert.throws(() => buildRepositoryCatalog(dir, sha), /frontmatter differs/);
  fixture.skills[1].recommended = false; writeFileSync(secondPath, document('qodo-z-future', 'qodo-next', 'second'));
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
  fixture.installPackages[1].name = 'qodo-next'; writeFileSync(join(dir, 'distribution/catalog.json'), JSON.stringify(fixture));
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

test('normal release workflow builds the catalog from its dependency-installed captured source', () => {
  const workflow = readFileSync(join(root, '.github/workflows/release.yml'), 'utf8');
  const install = workflow.indexOf('npm ci --ignore-scripts --prefix "${RUNNER_TEMP}/qodo-release-source"');
  const builder = workflow.indexOf('node "${RUNNER_TEMP}/qodo-release-source/scripts/build-repository-catalog.mjs"');
  const publish = workflow.indexOf('run: scripts/publish-release.sh');
  assert.ok(install >= 0 && builder > install && publish > builder);
  const command = workflow.slice(builder, workflow.indexOf('fi', builder));
  assert.match(command, /--output-dir "\$\{RUNNER_TEMP\}\/qodo-enterprise-release"/);
  assert.match(command, /--source-commit "\$\{RELEASE_COMMIT\}"/);
  assert.match(workflow, /QODO_ENTERPRISE_RELEASE_DIR: \$\{\{ runner.temp \}\}\/qodo-enterprise-release/);
  assert.match(workflow, /if \[\[ "\$\{CATALOG_EXPECTED\}" == true \]\]; then/);
});

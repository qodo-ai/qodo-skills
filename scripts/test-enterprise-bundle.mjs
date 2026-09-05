/** Verify deterministic enterprise release assets and package isolation. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import {
  assertNoPrivateKeyPayload,
  buildEnterpriseBundle,
} from './build-enterprise-bundle.mjs';

const commit = '0123456789abcdef0123456789abcdef01234567';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const packageVersion = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).version;

function sha256(payload) {
  return createHash('sha256').update(payload).digest('hex');
}

function tarFiles(archive) {
  const tar = gunzipSync(archive);
  const files = new Map();
  for (let offset = 0; offset + 512 <= tar.length;) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every((byte) => byte === 0)) break;
    const text = (start, length) => header.subarray(start, start + length).toString().replace(/\0.*$/, '');
    const name = text(0, 100);
    const prefix = text(345, 155);
    const path = prefix ? `${prefix}/${name}` : name;
    const size = Number.parseInt(text(124, 12).trim() || '0', 8);
    const storedChecksum = Number.parseInt(text(148, 8).trim(), 8);
    const checksumHeader = Buffer.from(header);
    checksumHeader.fill(0x20, 148, 156);
    assert.equal(checksumHeader.reduce((sum, byte) => sum + byte, 0), storedChecksum, `${path}: tar checksum`);
    const start = offset + 512;
    files.set(path, tar.subarray(start, start + size));
    offset = start + Math.ceil(size / 512) * 512;
  }
  return files;
}

const firstRoot = mkdtempSync(join(tmpdir(), 'qodo-enterprise-first-'));
const secondRoot = mkdtempSync(join(tmpdir(), 'qodo-enterprise-second-'));
try {
  const first = buildEnterpriseBundle({ output: firstRoot, commit });
  const second = buildEnterpriseBundle({ output: secondRoot, commit });
  assert.equal(first.version, packageVersion);
  assert.equal(first.archiveName, `qodo-enterprise-bundle-v${packageVersion}.tar.gz`);

  const firstArchive = readFileSync(join(firstRoot, first.archiveName));
  const secondArchive = readFileSync(join(secondRoot, second.archiveName));
  assert.deepEqual(firstArchive, secondArchive, 'enterprise archive must be byte-deterministic');
  assert.equal(first.archiveSha256, sha256(firstArchive));
  assert.equal(
    readFileSync(join(firstRoot, `${first.archiveName}.sha256`), 'utf8'),
    `${first.archiveSha256}  ${first.archiveName}\n`,
  );

  const manifestPayload = readFileSync(join(firstRoot, first.manifestName));
  const manifest = JSON.parse(manifestPayload);
  assert.equal(manifest.packageVersion, packageVersion);
  assert.equal(manifest.minimumCliVersion, '0.1.0-next.37');
  assert.deepEqual(manifest.source, {
    repository: 'https://github.com/qodo-ai/qodo-skills',
    commit,
    tag: `v${packageVersion}`,
  });
  assert.deepEqual(manifest.archive, { name: first.archiveName, sha256: first.archiveSha256 });
  assert.equal(manifest.discovery.schema, 'https://schemas.agentskills.io/discovery/0.2.0/schema.json');
  assert.equal(manifest.discovery.minimumCliVersion, '0.1.0-next.39');
  assert.deepEqual(manifest.installation, {
    skillsCli: { environment: { DO_NOT_TRACK: '1' } },
  });
  assert.equal(manifest.index.name, 'qodo-skills-index.json');
  assert.equal(
    readFileSync(join(firstRoot, `${first.manifestName}.sha256`), 'utf8'),
    `${sha256(manifestPayload)}  ${first.manifestName}\n`,
  );

  const discoveryPackages = new Map(manifest.discovery.packages.map((entry) => [entry.name, entry]));
  assert.deepEqual([...discoveryPackages.keys()].sort(), ['qodo', 'qodo-standards']);
  for (const [packageName, discoveryPackage] of discoveryPackages) {
    const expectedIndex = packageName === 'qodo'
      ? 'qodo-agent-skills-core-index.json'
      : 'qodo-agent-skills-standards-index.json';
    assert.equal(discoveryPackage.index.name, expectedIndex);
    const firstIndex = readFileSync(join(firstRoot, expectedIndex));
    const secondIndex = readFileSync(join(secondRoot, expectedIndex));
    assert.deepEqual(firstIndex, secondIndex, `${packageName} discovery index must be deterministic`);
    assert.equal(sha256(firstIndex), discoveryPackage.index.sha256);
    const index = JSON.parse(firstIndex);
    assert.equal(index.$schema, manifest.discovery.schema);
    assert.deepEqual(index.skills.map((entry) => entry.name), discoveryPackage.skills.map((entry) => entry.name));
    for (const entry of index.skills) {
      assert.equal(entry.type, 'archive');
      assert.match(entry.url, /^\.\.\/\.\.\/artifacts\/qodo-agent-skill-qodo-[a-z0-9-]+\.tar\.gz$/);
      const archiveName = entry.url.split('/').at(-1);
      const indexUrl = `https://qar.example/toolbox/skills/${packageName}/.well-known/agent-skills/index.json`;
      assert.equal(
        new URL(entry.url, indexUrl).pathname,
        `/toolbox/skills/${packageName}/artifacts/${archiveName}`,
        `${packageName} archive URL must resolve inside its package-scoped QAR route`,
      );
      const firstSkillArchive = readFileSync(join(firstRoot, archiveName));
      const secondSkillArchive = readFileSync(join(secondRoot, archiveName));
      assert.deepEqual(firstSkillArchive, secondSkillArchive, `${entry.name} archive must be deterministic`);
      assert.equal(entry.digest, `sha256:${sha256(firstSkillArchive)}`);
      const skillArchiveFiles = tarFiles(firstSkillArchive);
      assert.ok(skillArchiveFiles.has('SKILL.md'));
      assert.match(skillArchiveFiles.get('SKILL.md').toString(), /  distribution: "enterprise-bundle"/);
      assert.ok([...skillArchiveFiles.keys()].every((path) => !path.startsWith('qodo-enterprise/')));
    }
  }

  const files = tarFiles(firstArchive);
  assert.ok(files.has('qodo-enterprise/README.md'));
  assert.match(files.get('qodo-enterprise/README.md').toString(), /DO_NOT_TRACK=1/);
  assert.match(files.get('qodo-enterprise/README.md').toString(), /Qodo CLI 0\.1\.0-next\.37 or newer/);
  assert.ok(files.has('qodo-enterprise/bundle.json'));
  assert.equal(
    JSON.parse(files.get('qodo-enterprise/bundle.json')).minimumCliVersion,
    '0.1.0-next.37',
  );
  assert.ok(![...files.keys()].some((path) => path.endsWith('/qodo.mjs')), 'CLI bytes must remain a separate release');
  for (const [path, payload] of files) assertNoPrivateKeyPayload(payload, path);
  for (const marker of [
    '-----BEGIN PRIVATE KEY-----',
    '-----BEGIN ENCRYPTED PRIVATE KEY-----',
    '-----BEGIN DSA PRIVATE KEY-----',
    '-----BEGIN OPENSSH PRIVATE KEY-----',
    '-----BEGIN PGP PRIVATE KEY BLOCK-----',
  ]) {
    assert.throws(
      () => assertNoPrivateKeyPayload(Buffer.from(marker), 'qodo-enterprise/private.pem'),
      /private\.pem: enterprise bundles must not contain private keys/,
    );
  }
  for (const provider of ['claude', 'codex', 'kiro', 'portable']) {
    assert.ok([...files.keys()].some((path) => path.startsWith(`qodo-enterprise/${provider}/qodo/`)));
    assert.ok([...files.keys()].some((path) => path.startsWith(`qodo-enterprise/${provider}/qodo-standards/`)));
  }
  const core = manifest.packages.find((entry) => entry.name === 'qodo');
  assert.ok(!files.has('qodo-enterprise/kiro/qodo/Qodo-Kiro.png'));
  assert.doesNotMatch(files.get('qodo-enterprise/kiro/qodo/README.md').toString(), /Qodo-Kiro\.png/);
  assert.match(readFileSync(join(root, 'kiro-power/README.md'), 'utf8'), /Qodo-Kiro\.png/);
  // Current QAR schema v1 uses exact interface and non-skill file allowlists.
  // Directory-only artwork must not silently extend that enterprise protocol.
  const codexInterfaceFields = ['displayName', 'shortDescription', 'longDescription',
    'developerName', 'category', 'capabilities', 'websiteURL', 'privacyPolicyURL',
    'termsOfServiceURL', 'brandColor', 'defaultPrompt'].sort();
  for (const packageName of ['qodo', 'qodo-standards']) {
    const codexRoot = `qodo-enterprise/codex/${packageName}`;
    const plugin = JSON.parse(files.get(`${codexRoot}/.codex-plugin/plugin.json`));
    assert.deepEqual(Object.keys(plugin.interface).sort(), codexInterfaceFields);
    assert.ok(plugin.interface.defaultPrompt.length <= 3);
    assert.ok(files.has(`${codexRoot}/plugin.json`));
    assert.ok(![...files.keys()].some((path) => path.startsWith(`${codexRoot}/assets/`)));
    const publicPlugin = JSON.parse(readFileSync(join(root, 'codex-packages', packageName, '.codex-plugin/plugin.json')));
    assert.equal(publicPlugin.interface.logo, './assets/qodo.png');
    assert.ok(readFileSync(join(root, 'codex-packages', packageName, 'assets/qodo.png')).length > 0);
  }
  const standards = manifest.packages.find((entry) => entry.name === 'qodo-standards');
  assert.equal(core.default, true);
  assert.equal(standards.default, false);
  assert.ok(!core.skills.includes('qodo-get-rules'));
  assert.deepEqual(standards.skills.sort(), ['qodo-get-rules', 'qodo-manage-standards']);
  assert.deepEqual(core.projectionSkills.portable, core.skills);
  for (const provider of ['claude', 'codex', 'kiro']) {
    assert.deepEqual(
      core.projectionSkills[provider],
      [...core.skills, 'qodo-pr-resolver'].sort(),
    );
  }
  for (const provider of ['claude', 'codex', 'kiro', 'portable']) {
    assert.deepEqual(standards.projectionSkills[provider], standards.skills);
  }

  const skillFiles = [...files].filter(([path]) => path.endsWith('/SKILL.md'));
  assert.ok(skillFiles.length > 0);
  for (const [path, payload] of skillFiles) {
    const text = payload.toString();
    assert.match(text, /  distribution: "enterprise-bundle"/);
    assert.match(text, /--distribution enterprise-bundle/);
    assert.doesNotMatch(text, /--distribution (?:skills-sh|marketplace|kiro-power)(?=$|[^A-Za-z0-9_-])/m);
    assert.doesNotMatch(text, /  distribution: "(?:skills-sh|marketplace|kiro-power)"/);
    assert.ok(path.startsWith('qodo-enterprise/'));
  }
} finally {
  rmSync(firstRoot, { recursive: true, force: true });
  rmSync(secondRoot, { recursive: true, force: true });
}

console.log('Enterprise bundle tests passed.');

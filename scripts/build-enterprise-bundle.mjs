/** Build the deterministic, offline Qodo enterprise skills release assets. */
import { createHash } from 'node:crypto';
import {
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  writeFileSync,
} from 'node:fs';
import { gzipSync } from 'node:zlib';
import { dirname, join, posix, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const DISTRIBUTION = 'enterprise-bundle';
const PREFIX = 'qodo-enterprise';
const DISCOVERY_SCHEMA = 'https://schemas.agentskills.io/discovery/0.2.0/schema.json';
const DISCOVERY_MINIMUM_CLI_VERSION = '0.1.0-next.39';
const PRIVATE_KEY_PEM = /-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY(?: BLOCK)?-----/;

function sha256(payload) {
  return createHash('sha256').update(payload).digest('hex');
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function normalizedPath(path) {
  return path.split(sep).join('/');
}

function assertArchivePath(path) {
  if (
    !path || path.startsWith('/') || path.includes('\\')
    || path.split('/').some((segment) => !segment || segment === '.' || segment === '..')
  ) throw new Error(`Unsafe enterprise archive path: ${path}`);
}

function enterpriseSkill(text, sourcePath) {
  const metadata = /^  distribution: "(?:skills-sh|marketplace|kiro-power)"$/m;
  const calls = /--distribution (?:skills-sh|marketplace|kiro-power)(?=$|[^A-Za-z0-9_-])/g;
  if (!metadata.test(text) || !calls.test(text)) {
    throw new Error(`${sourcePath}: skill has no recognized distribution provenance`);
  }
  calls.lastIndex = 0;
  return text
    .replace(metadata, `  distribution: "${DISTRIBUTION}"`)
    .replace(calls, `--distribution ${DISTRIBUTION}`);
}

function bytewisePathCompare(left, right) {
  return Buffer.compare(Buffer.from(left), Buffer.from(right));
}

export function assertNoPrivateKeyPayload(payload, sourcePath) {
  if (PRIVATE_KEY_PEM.test(payload.toString())) {
    throw new Error(`${sourcePath}: enterprise bundles must not contain private keys`);
  }
}

function collectTree(sourceRoot, archiveRoot, files) {
  for (const entry of readdirSync(sourceRoot, { withFileTypes: true })
    .sort((left, right) => bytewisePathCompare(left.name, right.name))) {
    if (entry.name === '.DS_Store') continue;
    const source = join(sourceRoot, entry.name);
    const target = posix.join(archiveRoot, entry.name);
    if (entry.isDirectory()) collectTree(source, target, files);
    else if (entry.isFile()) {
      const payload = entry.name === 'SKILL.md'
        ? Buffer.from(enterpriseSkill(readFileSync(source, 'utf8'), normalizedPath(relative(root, source))))
        : readFileSync(source);
      files.push({ path: target, payload });
    } else {
      throw new Error(`${source}: enterprise bundles do not permit symlinks or special files`);
    }
  }
}

function collectProjection(provider, source, archiveRoot, files) {
  const projection = [];
  collectTree(source, archiveRoot, projection);
  for (const file of projection) {
    // Enterprise schema v1 predates marketplace directory artwork. Preserve QAR's
    // exact metadata/payload allowlist without changing the public projection.
    if (provider === 'codex' && file.path === `${archiveRoot}/assets/qodo.png`) continue;
    if (provider === 'kiro' && file.path === `${archiveRoot}/Qodo-Kiro.png`) continue;
    if (provider === 'kiro' && file.path === `${archiveRoot}/README.md`) {
      file.payload = Buffer.from(file.payload.toString('utf8').replace(
        /^<p align="center">\r?\n  <img src="\.\/Qodo-Kiro\.png"[^\r\n]*>\r?\n<\/p>\r?\n\r?\n/,
        '',
      ));
    }
    if (provider === 'codex' && file.path === `${archiveRoot}/.codex-plugin/plugin.json`) {
      const plugin = JSON.parse(file.payload.toString('utf8'));
      delete plugin.interface.composerIcon;
      delete plugin.interface.logo;
      file.payload = Buffer.from(`${JSON.stringify(plugin, null, 2)}\n`);
    }
    files.push(file);
  }
}

function writeField(header, offset, length, value) {
  const encoded = Buffer.from(value);
  if (encoded.length > length) throw new Error(`Tar field is too long: ${value}`);
  encoded.copy(header, offset);
}

function octal(value, length) {
  const encoded = value.toString(8);
  if (encoded.length > length - 1) throw new Error(`Tar numeric field is too large: ${value}`);
  return encoded.padStart(length - 1, '0') + '\0';
}

function tarName(header, path) {
  assertArchivePath(path);
  if (Buffer.byteLength(path) <= 100) {
    writeField(header, 0, 100, path);
    return;
  }
  const slash = path.lastIndexOf('/');
  const prefix = path.slice(0, slash);
  const name = path.slice(slash + 1);
  if (!slash || Buffer.byteLength(name) > 100 || Buffer.byteLength(prefix) > 155) {
    throw new Error(`Enterprise archive path is too long for ustar: ${path}`);
  }
  writeField(header, 0, 100, name);
  writeField(header, 345, 155, prefix);
}

function tarHeader(path, size) {
  const header = Buffer.alloc(512);
  tarName(header, path);
  writeField(header, 100, 8, octal(0o644, 8));
  writeField(header, 108, 8, octal(0, 8));
  writeField(header, 116, 8, octal(0, 8));
  writeField(header, 124, 12, octal(size, 12));
  writeField(header, 136, 12, octal(0, 12));
  header.fill(0x20, 148, 156);
  header[156] = '0'.charCodeAt(0);
  writeField(header, 257, 6, 'ustar\0');
  writeField(header, 263, 2, '00');
  writeField(header, 265, 32, 'qodo');
  writeField(header, 297, 32, 'qodo');
  const checksum = header.reduce((sum, byte) => sum + byte, 0).toString(8).padStart(6, '0');
  writeField(header, 148, 8, `${checksum}\0 `);
  return header;
}

function tar(files) {
  const parts = [];
  for (const file of [...files].sort((left, right) => bytewisePathCompare(left.path, right.path))) {
    assertArchivePath(file.path);
    parts.push(tarHeader(file.path, file.payload.length), file.payload);
    const padding = (512 - (file.payload.length % 512)) % 512;
    if (padding) parts.push(Buffer.alloc(padding));
  }
  parts.push(Buffer.alloc(1024));
  return Buffer.concat(parts);
}

function buildDiscoveryFeeds({ catalog, outputDir, repositoryRoot }) {
  const skillMetadata = new Map(catalog.skills.map((skill) => [skill.name, skill]));
  const packages = [];
  const assets = [];
  for (const installPackage of catalog.installPackages) {
    const entries = [];
    for (const skillName of installPackage.skills) {
      const files = [];
      collectTree(join(repositoryRoot, 'skills', skillName), '', files);
      const archiveName = `qodo-agent-skill-${skillName}.tar.gz`;
      const archive = gzipSync(tar(files), { level: 9, mtime: 0 });
      const digest = sha256(archive);
      writeFileSync(join(outputDir, archiveName), archive);
      entries.push({
        name: skillName,
        description: skillMetadata.get(skillName)?.shortDescription
          ?? `Qodo workflow ${skillName}.`,
        type: 'archive',
        url: `../../artifacts/${archiveName}`,
        digest: `sha256:${digest}`,
      });
      assets.push({ name: archiveName, sha256: digest });
    }
    const indexName = `qodo-agent-skills-${installPackage.name === 'qodo' ? 'core' : 'standards'}-index.json`;
    const indexPayload = Buffer.from(`${JSON.stringify({ $schema: DISCOVERY_SCHEMA, skills: entries }, null, 2)}\n`);
    writeFileSync(join(outputDir, indexName), indexPayload);
    const indexDigest = sha256(indexPayload);
    assets.push({ name: indexName, sha256: indexDigest });
    packages.push({
      name: installPackage.name,
      sourcePath: installPackage.name,
      index: { name: indexName, sha256: indexDigest },
      skills: entries.map((entry) => ({
        name: entry.name,
        archive: entry.url.split('/').at(-1),
        sha256: entry.digest.slice('sha256:'.length),
      })),
    });
  }
  return { schema: DISCOVERY_SCHEMA, packages, assets };
}

function packageRoots(name) {
  return {
    claude: `${PREFIX}/claude/${name}`,
    codex: `${PREFIX}/codex/${name}`,
    kiro: `${PREFIX}/kiro/${name}`,
    portable: `${PREFIX}/portable/${name}`,
  };
}

function packagedSkills(packageRoot) {
  return readdirSync(join(packageRoot, 'skills'), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort(bytewisePathCompare);
}

function bundleReadme(version, minimumCliVersion) {
  return `# Qodo enterprise skills ${version}

This archive contains Qodo skills only; the Qodo CLI runtime is released and pinned separately.

It requires Qodo CLI ${minimumCliVersion} or newer. QAR must verify this against its independently
pinned CLI before serving the bundle.

- Install the \`qodo\` package by default from the directory for the target host.
- Install \`qodo-standards\` only after an explicit administrator or user choice.
- Use \`portable/<package>\` for agents that consume a local \`skills/\` source.
- If an enterprise importer invokes the skills CLI, it must set \`DO_NOT_TRACK=1\` for every
  inventory, install, update, and removal command. The bundle itself never invokes that CLI.
- Keep one lifecycle owner per installed root. Do not install a public marketplace copy over an
  enterprise-managed copy.
- Update by importing a newer immutable enterprise bundle, then start a new agent session.

See \`bundle.json\` for exact package roots, versions, and membership.
`;
}

function argumentsFrom(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!value || !['--output', '--commit', '--release-index'].includes(flag)) throw new Error(`Unknown or incomplete argument: ${flag}`);
    options[flag === '--release-index' ? 'releaseIndex' : flag.slice(2)] = value;
  }
  if (!options.output) throw new Error('--output is required');
  if (!/^[a-f0-9]{40}$/i.test(options.commit ?? '')) throw new Error('--commit must be a 40-character Git SHA');
  return options;
}

export function buildEnterpriseBundle({ output, commit, releaseIndex }, repositoryRoot = root) {
  const catalog = JSON.parse(readFileSync(join(repositoryRoot, 'distribution', 'catalog.json'), 'utf8'));
  const version = catalog.package.version;
  const files = [];
  const packages = catalog.installPackages.map((installPackage) => {
    const roots = packageRoots(installPackage.name);
    const sources = {
      claude: join(repositoryRoot, 'packages', installPackage.name),
      codex: join(repositoryRoot, 'codex-packages', installPackage.name),
      kiro: join(repositoryRoot, installPackage.name === 'qodo' ? 'kiro-power' : 'kiro-power-standards'),
    };
    for (const [provider, source] of Object.entries(sources)) collectProjection(provider, source, roots[provider], files);
    for (const skill of installPackage.skills) {
      collectTree(
        join(repositoryRoot, 'skills', skill),
        posix.join(roots.portable, 'skills', skill),
        files,
      );
    }
    const projectionSkills = {
      ...Object.fromEntries(
        Object.entries(sources).map(([provider, source]) => [provider, packagedSkills(source)]),
      ),
      portable: [...installPackage.skills],
    };
    for (const [provider, skills] of Object.entries(projectionSkills)) {
      const missing = installPackage.skills.filter((skill) => !skills.includes(skill));
      if (missing.length > 0) {
        throw new Error(`${installPackage.name}: ${provider} projection is missing ${missing.join(', ')}`);
      }
    }
    return {
      name: installPackage.name,
      displayName: installPackage.displayName,
      description: installPackage.description,
      default: installPackage.default,
      skills: installPackage.skills,
      compatibilityAliases: installPackage.compatibilityAliases,
      projectionSkills,
      roots,
    };
  });
  const bundle = {
    schemaVersion: 1,
    distribution: DISTRIBUTION,
    packageVersion: version,
    runtimeProtocolVersion: catalog.runtime.protocolVersion,
    minimumCliVersion: catalog.runtime.minimumCliVersion,
    source: { repository: catalog.package.repository, commit, tag: `v${version}` },
    installation: { skillsCli: { environment: { DO_NOT_TRACK: '1' } } },
    packages,
  };
  files.push(
    { path: `${PREFIX}/README.md`, payload: Buffer.from(bundleReadme(version, catalog.runtime.minimumCliVersion)) },
    { path: `${PREFIX}/bundle.json`, payload: Buffer.from(`${JSON.stringify(bundle, null, 2)}\n`) },
  );
  for (const file of files) assertNoPrivateKeyPayload(file.payload, file.path);

  const outputDir = resolve(repositoryRoot, output);
  mkdirSync(outputDir, { recursive: true });
  const discovery = buildDiscoveryFeeds({ catalog, outputDir, repositoryRoot });
  const archiveName = `qodo-enterprise-bundle-v${version}.tar.gz`;
  const archive = gzipSync(tar(files), { level: 9, mtime: 0 });
  const archiveDigest = sha256(archive);
  writeFileSync(join(outputDir, archiveName), archive);
  writeFileSync(join(outputDir, `${archiveName}.sha256`), `${archiveDigest}  ${archiveName}\n`);

  const indexName = 'qodo-skills-index.json';
  const indexPath = resolve(repositoryRoot, releaseIndex ?? join('distribution', indexName));
  const index = readFileSync(indexPath);
  const indexChecksum = readFileSync(`${indexPath}.sha256`, 'utf8');
  const indexDigest = sha256(index);
  if (!indexChecksum.startsWith(`${indexDigest}  ${indexName}`)) throw new Error('Qodo skills index checksum is stale');
  const manifest = {
    ...bundle,
    archive: { name: archiveName, sha256: archiveDigest },
    index: { name: indexName, sha256: indexDigest, checksumName: `${indexName}.sha256` },
    discovery: {
      schema: discovery.schema,
      minimumCliVersion: DISCOVERY_MINIMUM_CLI_VERSION,
      packages: discovery.packages,
    },
  };
  const manifestName = 'qodo-enterprise-manifest.json';
  const manifestPath = join(outputDir, manifestName);
  writeJson(manifestPath, manifest);
  const manifestPayload = readFileSync(manifestPath);
  writeFileSync(
    join(outputDir, `${manifestName}.sha256`),
    `${sha256(manifestPayload)}  ${manifestName}\n`,
  );
  return {
    version,
    archiveName,
    archiveSha256: archiveDigest,
    manifestName,
    discoveryAssets: discovery.assets.map((asset) => asset.name),
    outputDir,
  };
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = buildEnterpriseBundle(argumentsFrom(process.argv.slice(2)));
    console.log(`Built Qodo enterprise bundle ${result.version} at ${result.outputDir}.`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

/** Validate canonical skills, generated adapters, and release invariants. */
import { execFileSync } from 'node:child_process';
import {
  existsSync,
  lstatSync,
  readFileSync,
  readdirSync,
} from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const errors = [];
const semver = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const forbiddenRuntimeBypass = new RegExp([
  'QODO_', 'API_KEY', '|',
  'API_KEY', '\\s*[":=]', '|',
  'qodo-platform\\.', '[^\\s]+', '\\/rules\\/v1',
].join(''), 'i');

function fail(message) {
  errors.push(message);
}

function json(path) {
  try {
    return JSON.parse(readFileSync(join(root, path), 'utf8'));
  } catch (error) {
    fail(`${path}: ${error.message}`);
    return {};
  }
}

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir).sort()) {
    if (name === '.git' || name === 'node_modules') continue;
    const path = join(dir, name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) fail(`${relative(root, path)}: symlinks are not allowed`);
    else if (stat.isDirectory()) files.push(...walk(path));
    else if (stat.isFile()) files.push(path);
  }
  return files;
}

function frontmatter(path) {
  const text = readFileSync(path, 'utf8').replace(/\r\n/g, '\n');
  const match = text.match(/^---\n([\s\S]*?)\n---/);
  if (!match) {
    fail(`${relative(root, path)}: missing YAML frontmatter`);
    return {};
  }
  const result = { metadata: {} };
  let section = '';
  for (const line of match[1].split('\n')) {
    const field = line.match(/^([a-z_-]+):(?:\s*(.*))?$/);
    if (field) {
      section = field[1];
      if (field[2]) result[field[1]] = field[2].replace(/^['"]|['"]$/g, '');
      continue;
    }
    const nested = line.match(/^  ([a-z_-]+):\s*(.+)\s*$/);
    if (section === 'metadata' && nested) {
      result.metadata[nested[1]] = nested[2].replace(/^['"]|['"]$/g, '');
    }
  }
  return result;
}

const catalog = json('distribution/catalog.json');
const packageVersion = catalog.package?.version;
if (!semver.test(packageVersion ?? '')) fail('catalog package.version must be semantic version');
if (catalog.runtime?.command !== 'qodo') fail('runtime command must remain qodo');
if (catalog.runtime?.loginCommand !== 'qodo login') fail('runtime login must remain qodo login');

const skillsRoot = join(root, 'skills');
const diskSkills = readdirSync(skillsRoot)
  .filter((name) => lstatSync(join(skillsRoot, name)).isDirectory())
  .sort();
const catalogSkills = (catalog.skills ?? []).map((skill) => skill.name).sort();
if (JSON.stringify(diskSkills) !== JSON.stringify(catalogSkills)) {
  fail(`skills/catalog mismatch: disk=${diskSkills.join(',')} catalog=${catalogSkills.join(',')}`);
}

for (const skill of catalog.skills ?? []) {
  if (!/^qodo-[a-z0-9-]+$/.test(skill.name)) fail(`${skill.name}: invalid skill name`);
  if (!semver.test(skill.version ?? '')) fail(`${skill.name}: invalid version`);
  if (skill.defaultPrompt && !skill.defaultPrompt.includes(`$${skill.name}`)) {
    fail(`${skill.name}: defaultPrompt must name $${skill.name}`);
  }
  const skillPath = join(skillsRoot, skill.name, 'SKILL.md');
  if (!existsSync(skillPath)) {
    fail(`${skill.name}: missing SKILL.md`);
    continue;
  }
  const meta = frontmatter(skillPath);
  if (meta.name !== skill.name) fail(`${skill.name}: frontmatter name differs from catalog`);
  if (meta.metadata.vendor !== 'qodo') fail(`${skill.name}: frontmatter metadata.vendor must be qodo`);
  if (meta.metadata.version !== skill.version) fail(`${skill.name}: frontmatter version differs from catalog`);
  const recommended = meta.metadata.recommended === undefined ? true : meta.metadata.recommended === 'true';
  if (recommended !== skill.recommended) fail(`${skill.name}: recommended differs from catalog`);
}

const expectedVersions = [
  ['package.json', json('package.json').version],
  ['plugin.json', json('plugin.json').version],
  ['.codex-plugin/plugin.json', json('.codex-plugin/plugin.json').version],
  ['.claude-plugin/plugin.json', json('.claude-plugin/plugin.json').version],
  ['.claude-plugin/marketplace.json metadata', json('.claude-plugin/marketplace.json').metadata?.version],
  ['.claude-plugin/marketplace.json plugin', json('.claude-plugin/marketplace.json').plugins?.[0]?.version],
  ['gemini-extension.json', json('gemini-extension.json').version],
];
for (const [path, version] of expectedVersions) {
  if (version !== packageVersion) fail(`${path}: version ${version ?? '<missing>'} != ${packageVersion}`);
}

const agentPlugin = json('plugin.json');
if (agentPlugin.$schema !== 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json') {
  fail('plugin.json: unsupported Agent Plugins schema');
}
const allowedAgentFields = new Set([
  '$schema', 'name', 'version', 'description', 'author', 'homepage',
  'repository', 'license', 'keywords', 'extensions',
]);
for (const field of Object.keys(agentPlugin)) {
  if (!allowedAgentFields.has(field)) fail(`plugin.json: unsupported field ${field}`);
}

const codexMarketplace = json('.agents/plugins/marketplace.json');
const codexEntry = codexMarketplace.plugins?.find((entry) => entry.name === catalog.package?.name);
if (codexMarketplace.name !== 'qodo' || !codexEntry) fail('Codex marketplace must expose qodo');
if (codexEntry?.source?.path !== './') fail('Codex marketplace must package this repository root');
if (codexEntry?.policy?.authentication !== 'ON_USE') {
  fail('Codex marketplace authentication must happen on first use');
}

for (const file of walk(root)) {
  const path = relative(root, file);
  if (/\.(md|mjs|json|ya?ml)$/.test(path)) {
    const lines = readFileSync(file, 'utf8').split('\n').length;
    if (lines > 500) fail(`${path}: ${lines} lines exceeds the 500-line limit`);
  }
  if (/\.(md|mjs|json|ya?ml)$/.test(path)) {
    const text = readFileSync(file, 'utf8');
    if (forbiddenRuntimeBypass.test(text)) {
      fail(`${path}: bypasses the qodo runtime credential boundary`);
    }
  }
}

try {
  execFileSync(process.execPath, [join(root, 'scripts', 'sync-adapters.mjs'), '--check'], {
    cwd: root,
    stdio: 'ignore',
  });
} catch (error) {
  fail(`generated adapters are stale or invalid: ${error.message}`);
}

if (errors.length) {
  console.error(`Validation failed (${errors.length}):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}
console.log(`Validated ${catalog.skills.length} canonical skills and all marketplace adapters.`);

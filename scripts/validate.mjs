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
const valueMomentHeadings = new Map([
  ['qodo-setup', '# ✅ Qodo Ready'],
  ['qodo-codebase-wisdom', '# 🧭 Qodo Codebase Insight'],
  ['qodo-get-rules', '# 📋 Qodo Rules Loaded'],
  ['qodo-manage-standards', '# 🛡️ Qodo Review Standards'],
  ['qodo-review', '# 🔍 Qodo Pre-PR Review'],
  ['qodo-review-resolver', '# 🔎 Qodo PR Review'],
]);
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

const installPackageNames = new Set();
const packagedSkills = new Map();
for (const installPackage of catalog.installPackages ?? []) {
  if (!/^qodo(?:-[a-z0-9-]+)?$/.test(installPackage.name) || installPackageNames.has(installPackage.name)) {
    fail(`invalid or duplicate install package ${installPackage.name ?? '<missing>'}`);
    continue;
  }
  installPackageNames.add(installPackage.name);
  if (!Array.isArray(installPackage.skills) || installPackage.skills.length === 0) {
    fail(`${installPackage.name}: install package must contain skills`);
    continue;
  }
  for (const skillName of installPackage.skills) {
    if (packagedSkills.has(skillName)) {
      fail(`${skillName}: assigned to both ${packagedSkills.get(skillName)} and ${installPackage.name}`);
    } else {
      packagedSkills.set(skillName, installPackage.name);
    }
  }
}
const defaults = (catalog.installPackages ?? []).filter((entry) => entry.default);
if (defaults.length !== 1 || defaults[0]?.name !== catalog.package?.name) {
  fail(`exactly the ${catalog.package?.name ?? 'qodo'} install package must be default`);
}
for (const skillName of catalogSkills) {
  if (!packagedSkills.has(skillName)) fail(`${skillName}: missing install package assignment`);
}
for (const skillName of packagedSkills.keys()) {
  if (!catalogSkills.includes(skillName)) fail(`${skillName}: install package references unknown skill`);
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
  const installPackage = (catalog.installPackages ?? []).find((entry) => entry.skills.includes(skill.name));
  if (meta.metadata.package !== installPackage?.name) {
    fail(`${skill.name}: frontmatter package differs from catalog`);
  }
  if (meta.metadata.distribution !== 'skills-sh') {
    fail(`${skill.name}: canonical source distribution must be skills-sh`);
  }
  if (installPackage && recommended !== installPackage.default) {
    fail(`${skill.name}: recommended must match install package ${installPackage.name} default state`);
  }
  const expectedHeading = valueMomentHeadings.get(skill.name);
  const skillText = readFileSync(skillPath, 'utf8');
  const provenance = `--skill ${skill.name} --skill-version ${skill.version} --distribution skills-sh`;
  if (!skillText.includes(provenance)) fail(`${skill.name}: missing canonical provenance invocation`);
  const headingCount = expectedHeading ? skillText.split(expectedHeading).length - 1 : 0;
  if (!expectedHeading || headingCount !== 1) {
    fail(`${skill.name}: expected exactly one branded value-moment heading ${expectedHeading ?? '<unregistered>'}`);
  }
}

const expectedVersions = [
  ['package.json', json('package.json').version],
  ['packages/qodo/plugin.json', json('packages/qodo/plugin.json').version],
  ['packages/qodo/.codex-plugin/plugin.json', json('packages/qodo/.codex-plugin/plugin.json').version],
  ['packages/qodo-standards/plugin.json', json('packages/qodo-standards/plugin.json').version],
  ['packages/qodo-standards/.codex-plugin/plugin.json', json('packages/qodo-standards/.codex-plugin/plugin.json').version],
  ['kiro-power/plugin.json', json('kiro-power/plugin.json').version],
  ['kiro-power-standards/plugin.json', json('kiro-power-standards/plugin.json').version],
  ['packages/qodo/.claude-plugin/plugin.json', json('packages/qodo/.claude-plugin/plugin.json').version],
  ['packages/qodo-standards/.claude-plugin/plugin.json', json('packages/qodo-standards/.claude-plugin/plugin.json').version],
  ['.claude-plugin/marketplace.json metadata', json('.claude-plugin/marketplace.json').metadata?.version],
  ['packages/qodo/gemini-extension.json', json('packages/qodo/gemini-extension.json').version],
  ['packages/qodo-standards/gemini-extension.json', json('packages/qodo-standards/gemini-extension.json').version],
];
for (const [path, version] of expectedVersions) {
  if (version !== packageVersion) fail(`${path}: version ${version ?? '<missing>'} != ${packageVersion}`);
}

const agentPlugin = json('packages/qodo/plugin.json');
if (agentPlugin.$schema !== 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json') {
  fail('packages/qodo/plugin.json: unsupported Agent Plugins schema');
}
const allowedAgentFields = new Set([
  '$schema', 'name', 'version', 'description', 'author', 'homepage',
  'repository', 'license', 'keywords', 'extensions',
]);
for (const field of Object.keys(agentPlugin)) {
  if (!allowedAgentFields.has(field)) fail(`packages/qodo/plugin.json: unsupported field ${field}`);
}

const codexMarketplace = json('.agents/plugins/marketplace.json');
const codexEntry = codexMarketplace.plugins?.find((entry) => entry.name === catalog.package?.name);
if (codexMarketplace.name !== 'qodo' || !codexEntry) fail('Codex marketplace must expose qodo');
if (codexEntry?.source?.path !== './packages/qodo') fail('Codex marketplace must package the generated core root');
if (codexEntry?.policy?.authentication !== 'ON_USE') {
  fail('Codex marketplace authentication must happen on first use');
}
const codexStandards = codexMarketplace.plugins?.find((entry) => entry.name === 'qodo-standards');
if (codexStandards?.source?.path !== './packages/qodo-standards') {
  fail('Codex marketplace must expose standards as a separate optional plugin');
}

const claudeMarketplace = json('.claude-plugin/marketplace.json');
if ((claudeMarketplace.plugins ?? []).some((entry) => 'version' in entry)) {
  fail('Claude plugin versions must come only from package-local .claude-plugin/plugin.json files');
}
if (claudeMarketplace.plugins?.find((entry) => entry.name === 'qodo')?.source !== './packages/qodo') {
  fail('Claude marketplace must package the generated core root');
}
if (claudeMarketplace.plugins?.find((entry) => entry.name === 'qodo-standards')?.source !== './packages/qodo-standards') {
  fail('Claude marketplace must expose standards as a separate optional plugin');
}

for (const unsafeRoot of ['plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json', 'gemini-extension.json']) {
  if (existsSync(join(root, unsafeRoot))) fail(`${unsafeRoot}: root package would expose optional skills automatically`);
}
if (existsSync(join(root, 'packages', 'qodo', 'skills', 'qodo-get-rules'))) {
  fail('qodo-get-rules must not be present in the default core package');
}
if (!existsSync(join(root, 'packages', 'qodo-standards', 'skills', 'qodo-get-rules', 'SKILL.md'))) {
  fail('qodo-get-rules must be present in the optional standards package');
}

for (const installPackage of catalog.installPackages ?? []) {
  for (const skillName of installPackage.skills) {
    const skill = catalog.skills.find((entry) => entry.name === skillName);
    const generated = [
      [`packages/${installPackage.name}/skills/${skillName}/SKILL.md`, 'marketplace'],
      [
        `${installPackage.name === catalog.package.name ? 'kiro-power' : 'kiro-power-standards'}/skills/${skillName}/SKILL.md`,
        'kiro-power',
      ],
    ];
    for (const [path, distribution] of generated) {
      const meta = frontmatter(join(root, path));
      if (meta.metadata.package !== installPackage.name || meta.metadata.distribution !== distribution) {
        fail(`${path}: generated provenance differs from catalog`);
      }
      const text = readFileSync(join(root, path), 'utf8');
      const marker = `--skill ${skillName} --skill-version ${skill.version} --distribution ${distribution}`;
      if (!text.includes(marker)) fail(`${path}: missing generated provenance invocation`);
    }
  }
}

const release = json(`releases/v${packageVersion}.json`);
if (release.version !== packageVersion) fail('current release record must match package.version');
if (typeof release.summary !== 'string' || !release.summary.trim()) fail('release summary is required');
if (!['initial', 'patch', 'minor', 'major'].includes(release.package?.change)) {
  fail('release package.change must be initial, patch, minor, or major');
}
if (release.runtimeProtocolVersion !== catalog.runtime?.protocolVersion) {
  fail('release runtimeProtocolVersion must match the catalog');
}
const releaseSkillNames = new Set();
for (const change of release.skills ?? []) {
  if (releaseSkillNames.has(change.name)) fail(`release repeats skill ${change.name}`);
  releaseSkillNames.add(change.name);
  if (!semver.test(change.version ?? '')) fail(`release ${change.name}: invalid version`);
  if (!['initial', 'patch', 'minor', 'major'].includes(change.change)) {
    fail(`release ${change.name}: invalid change type`);
  }
  const skill = catalog.skills?.find((entry) => entry.name === change.name);
  if (!skill) fail(`release references unknown skill ${change.name}`);
  else if (skill.version !== change.version) fail(`release ${change.name}: version differs from catalog`);
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

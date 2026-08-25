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
const marketplaces = json('distribution/marketplaces.json');
const codexSubmissions = json('distribution/codex-submissions.json');
const packageVersion = catalog.package?.version;
if (!semver.test(packageVersion ?? '')) fail('catalog package.version must be semantic version');
if (catalog.runtime?.command !== 'qodo') fail('runtime command must remain qodo');
if (catalog.runtime?.loginCommand !== 'qodo login') fail('runtime login must remain qodo login');
for (const field of ['repository', 'homepage', 'supportUrl', 'privacyPolicyUrl', 'termsOfServiceUrl']) {
  if (!String(catalog.package?.[field] ?? '').startsWith('https://')) {
    fail(`catalog package.${field} must be an HTTPS URL`);
  }
}

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

const expectedProviders = ['claude', 'codex', 'kiro'];
const providerIds = (marketplaces.providers ?? []).map((entry) => entry.id).sort();
if (JSON.stringify(providerIds) !== JSON.stringify(expectedProviders)) {
  fail(`marketplace providers must be exactly ${expectedProviders.join(', ')}`);
}
for (const provider of marketplaces.providers ?? []) {
  const listingPackages = (provider.listings ?? []).map((entry) => entry.package).sort();
  if (JSON.stringify(listingPackages) !== JSON.stringify([...installPackageNames].sort())) {
    fail(`${provider.id}: listings must cover every install package exactly once`);
  }
  if (![provider.submissionUrl, provider.directoryUrl].every((url) => String(url).startsWith('https://'))) {
    fail(`${provider.id}: release URLs must use HTTPS`);
  }
}

const codexProvider = marketplaces.providers?.find((entry) => entry.id === 'codex');
const codexSubmissionPackages = (codexSubmissions.listings ?? []).map((entry) => entry.package).sort();
const codexListingPackages = (codexProvider?.listings ?? []).map((entry) => entry.package).sort();
if (JSON.stringify(codexSubmissionPackages) !== JSON.stringify(codexListingPackages)) {
  fail('Codex submission metadata must cover every Codex listing exactly once');
}
for (const submission of codexSubmissions.listings ?? []) {
  if ((submission.positiveTests ?? []).length < 5) {
    fail(`${submission.package}: Codex submission requires at least five positive tests`);
  }
  if ((submission.negativeTests ?? []).length < 3) {
    fail(`${submission.package}: Codex submission requires at least three negative tests`);
  }
  if (!['initial', 'update'].includes(submission.releaseType)) {
    fail(`${submission.package}: invalid Codex release type`);
  }
  for (const test of submission.positiveTests ?? []) {
    for (const field of ['prompt', 'expectedBehavior', 'expectedResultShape', 'fixtureData']) {
      if (!String(test[field] ?? '').trim()) fail(`${submission.package}: positive test missing ${field}`);
    }
  }
  for (const test of submission.negativeTests ?? []) {
    for (const field of ['scenario', 'expectedSafeBehavior', 'reason']) {
      if (!String(test[field] ?? '').trim()) fail(`${submission.package}: negative test missing ${field}`);
    }
  }
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
  ['codex-packages/qodo/plugin.json', json('codex-packages/qodo/plugin.json').version],
  ['codex-packages/qodo/.codex-plugin/plugin.json', json('codex-packages/qodo/.codex-plugin/plugin.json').version],
  ['packages/qodo-standards/plugin.json', json('packages/qodo-standards/plugin.json').version],
  ['codex-packages/qodo-standards/plugin.json', json('codex-packages/qodo-standards/plugin.json').version],
  ['codex-packages/qodo-standards/.codex-plugin/plugin.json', json('codex-packages/qodo-standards/.codex-plugin/plugin.json').version],
  ['kiro-power/plugin.json', json('kiro-power/plugin.json').version],
  ['kiro-power-standards/plugin.json', json('kiro-power-standards/plugin.json').version],
  ['packages/qodo/.claude-plugin/plugin.json', json('packages/qodo/.claude-plugin/plugin.json').version],
  ['packages/qodo-standards/.claude-plugin/plugin.json', json('packages/qodo-standards/.claude-plugin/plugin.json').version],
  ['.claude-plugin/marketplace.json metadata', json('.claude-plugin/marketplace.json').metadata?.version],
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
if (codexEntry?.source?.path !== './codex-packages/qodo') fail('Codex marketplace must package the host-specific generated core root');
if (codexEntry?.policy?.authentication !== 'ON_USE') {
  fail('Codex marketplace authentication must happen on first use');
}
const codexStandards = codexMarketplace.plugins?.find((entry) => entry.name === 'qodo-standards');
if (codexStandards?.source?.path !== './codex-packages/qodo-standards') {
  fail('Codex marketplace must expose standards as a separate optional plugin');
}

const claudeMarketplace = json('.claude-plugin/marketplace.json');
const claudeProvider = marketplaces.providers?.find((entry) => entry.id === 'claude');
const claudeCoreId = claudeProvider?.listings?.find((entry) => entry.package === 'qodo')?.id;
if ((claudeMarketplace.plugins ?? []).some((entry) => 'version' in entry)) {
  fail('Claude plugin versions must come only from package-local .claude-plugin/plugin.json files');
}
if (claudeCoreId !== 'qodo') {
  fail('Claude core listing must preserve the existing qodo identity');
}
if (claudeMarketplace.plugins?.find((entry) => entry.name === claudeCoreId)?.source !== './packages/qodo') {
  fail('Claude marketplace must preserve qodo while packaging the generated core root');
}
if (claudeMarketplace.plugins?.find((entry) => entry.name === 'qodo-standards')?.source !== './packages/qodo-standards') {
  fail('Claude marketplace must expose standards as a separate optional plugin');
}
if (json('packages/qodo/.claude-plugin/plugin.json').name !== claudeCoreId) {
  fail('Claude core package manifest must preserve the qodo identity');
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
      [`packages/${installPackage.name}/skills/${skillName}/SKILL.md`, 'marketplace', 'claude-code'],
      [`codex-packages/${installPackage.name}/skills/${skillName}/SKILL.md`, 'marketplace', 'codex'],
      [
        `${installPackage.name === catalog.package.name ? 'kiro-power' : 'kiro-power-standards'}/skills/${skillName}/SKILL.md`,
        'kiro-power',
        'kiro',
      ],
    ];
    for (const [path, distribution, host] of generated) {
      const meta = frontmatter(join(root, path));
      if (meta.metadata.package !== installPackage.name || meta.metadata.distribution !== distribution) {
        fail(`${path}: generated provenance differs from catalog`);
      }
      const text = readFileSync(join(root, path), 'utf8');
      const loader = `qodo help workflow ${skillName} --distribution ${distribution} --host ${host} --json`;
      if (!text.includes(loader)) fail(`${path}: missing exact host-scoped playbook loader`);
      if ((text.match(/qodo help workflow /g) ?? []).length !== 1) {
        fail(`${path}: bootstrap must contain exactly one playbook loader`);
      }
      if (!text.includes('## Static authority ceiling')) fail(`${path}: missing static authority ceiling`);
      if (!text.includes('may be\n  newer than this discovery bootstrap')) {
        fail(`${path}: bootstrap incorrectly pins routine playbook updates to its own version`);
      }
      if (!text.includes('`integrity.cache: verified-cache`')) {
        fail(`${path}: bootstrap accepts a non-cache playbook source`);
      }
      if (!text.includes('`fresh` or `last-known-good`')) {
        fail(`${path}: bootstrap does not constrain verified-cache provenance state`);
      }
      if (!text.includes('An\n`embedded-fallback` response is compatible CLI help')) {
        fail(`${path}: bootstrap does not reject embedded fallback for marketplace execution`);
      }
      if (!text.includes('retry the exact loader once with `--refresh`')) {
        fail(`${path}: bootstrap lacks bounded initial-cache recovery`);
      }
      if (text.includes('## Handle a skill update notice')) fail(`${path}: marketplace adapter contains the full canonical playbook`);
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

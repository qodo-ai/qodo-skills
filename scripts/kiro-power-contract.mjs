const AGENT_PLUGIN_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json';

const AGENT_PLUGIN_FIELDS = new Set([
  '$schema',
  'name',
  'version',
  'description',
  'author',
  'homepage',
  'repository',
  'license',
  'keywords',
  'extensions',
]);

const KIRO_REQUIRED_FIELDS = [
  '$schema',
  'name',
  'version',
  'description',
  'author',
  'keywords',
  'license',
];

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

export function validateKiroPowerContract({ manifest, entries }, label = 'Kiro Power') {
  const errors = [];
  const files = new Set(entries);

  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    return [`${label}/plugin.json: expected a JSON object`];
  }
  if (manifest.$schema !== AGENT_PLUGIN_SCHEMA) {
    errors.push(`${label}/plugin.json: unsupported Agent Plugins schema`);
  }
  for (const field of KIRO_REQUIRED_FIELDS) {
    if (manifest[field] === undefined) errors.push(`${label}/plugin.json: missing required field ${field}`);
  }
  for (const field of Object.keys(manifest)) {
    if (!AGENT_PLUGIN_FIELDS.has(field)) {
      errors.push(`${label}/plugin.json: unsupported Agent Plugins field ${field}`);
    }
  }
  if (!isNonEmptyString(manifest.name) || !/^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/.test(manifest.name)) {
    errors.push(`${label}/plugin.json: name must be a valid Agent Plugins identifier`);
  }
  if (!isNonEmptyString(manifest.version)) errors.push(`${label}/plugin.json: version must be a non-empty string`);
  if (!isNonEmptyString(manifest.description)) errors.push(`${label}/plugin.json: description must be a non-empty string`);
  if (!isNonEmptyString(manifest.author?.name)) errors.push(`${label}/plugin.json: author.name must be a non-empty string`);
  if (!Array.isArray(manifest.keywords) || manifest.keywords.length === 0
    || manifest.keywords.some((keyword) => !isNonEmptyString(keyword))) {
    errors.push(`${label}/plugin.json: keywords must contain non-empty strings`);
  }
  if (!isNonEmptyString(manifest.license)) errors.push(`${label}/plugin.json: license must be a non-empty string`);

  if (files.has('POWER.md')) {
    errors.push(`${label}: legacy POWER.md is forbidden; use plugin.json plus skills/`);
  }
  if ([...files].some((path) => path === 'steering' || path.startsWith('steering/'))) {
    errors.push(`${label}: legacy steering/ is forbidden; use skills/ or a dev.kiro extension`);
  }
  if (![...files].some((path) => /^skills\/[^/]+\/SKILL\.md$/.test(path))) {
    errors.push(`${label}: expected at least one skills/<name>/SKILL.md`);
  }

  return errors;
}

export function assertKiroPowerContract(input, label) {
  const errors = validateKiroPowerContract(input, label);
  if (errors.length > 0) throw new Error(errors.join('\n'));
}

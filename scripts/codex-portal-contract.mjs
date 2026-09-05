/** Shared generator/ZIP checks for the Qodo Codex directory contract.
 * https://developers.openai.com/plugins/deploy/submission-errors (checked: 2026-09-05)
 * Not a substitute for the provider's validation, review, and publication.
 */
const unsupportedSingleLine = /[\p{Cc}\p{Cf}\p{Cs}\u2028\u2029]/u;

function text(value, label, limit) {
  if (typeof value !== 'string' || !value.trim() ||
      [...value].length > limit || unsupportedSingleLine.test(value)) {
    throw new Error(`${label}: expected non-empty single-line text, at most ${limit} characters`);
  }
}

export function validateStarterPrompts(prompts) {
  if (!Array.isArray(prompts) || prompts.length < 1 || prompts.length > 3) {
    throw new Error('Codex defaultPrompt must contain one to three prompts');
  }
  const seen = new Set();
  for (const prompt of prompts) {
    text(prompt, 'Codex defaultPrompt', 128);
    const normalized = prompt.normalize('NFKC').replace(/\s+/gu, ' ').trim();
    if (seen.has(normalized)) throw new Error('Codex defaultPrompt contains duplicate prompts');
    if (/@[\p{L}\p{N}_-]+/u.test(prompt)) throw new Error('Codex defaultPrompt must not contain app mentions');
    seen.add(normalized);
  }
  return prompts;
}

export function codexListingInterface(catalog, submission) {
  const pkg = catalog.installPackages.find((entry) => entry.name === submission?.package);
  const names = submission?.starterSkills;
  if (!pkg || !Array.isArray(names) || names.length < 1 || names.length > 3 ||
      new Set(names).size !== names.length || names.some((name) => !pkg.skills.includes(name))) {
    throw new Error('Codex starterSkills must select one to three distinct skills inside the listing package');
  }
  const defaultPrompt = names.map((name) => catalog.skills.find((skill) => skill.name === name)?.defaultPrompt);
  validateStarterPrompts(defaultPrompt);
  text(submission.shortDescription, 'Codex shortDescription', 30);
  return { shortDescription: submission.shortDescription, defaultPrompt };
}

function assetPath(value) {
  if (typeof value !== 'string' || !/^\.\/assets\/[a-z0-9][a-z0-9.-]*\.png$/.test(value)) {
    throw new Error('Qodo Codex branding must reference a bundled ./assets/*.png file');
  }
  return value.slice(2);
}

// Qodo currently ships PNG branding only. This checks signature and dimensions,
// not arbitrary image decoding; the provider remains the full image validator.
function validatePng(bytes) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (!Buffer.isBuffer(bytes) || bytes.length < 33 || bytes.length > 5 * 1024 * 1024 ||
      !bytes.subarray(0, 8).equals(signature) || bytes.readUInt32BE(8) !== 13 ||
      bytes.toString('ascii', 12, 16) !== 'IHDR') {
    throw new Error('Codex branding must be a PNG with an IHDR header, no larger than 5 MiB');
  }
  const width = bytes.readUInt32BE(16);
  if (width < 48 || width > 4096 || width !== bytes.readUInt32BE(20)) {
    throw new Error('Codex branding must be square, between 48 and 4096 pixels');
  }
}

export function validateCodexPortalManifest(plugin, readAsset) {
  const ui = plugin?.interface;
  validateStarterPrompts(ui?.defaultPrompt);
  text(ui?.displayName, 'Codex displayName', 30);
  text(ui?.shortDescription, 'Codex shortDescription', 30);
  for (const field of ['composerIcon', 'logo']) {
    const path = assetPath(ui?.[field]);
    validatePng(readAsset(path));
  }
}

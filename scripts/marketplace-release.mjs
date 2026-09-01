/** Prepare and verify one immutable release against official marketplace contracts. */
import { appendFileSync, cpSync, existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const marketplaceCatalog = JSON.parse(readFileSync(join(root, 'distribution', 'marketplaces.json'), 'utf8'));
const codexSubmissions = JSON.parse(readFileSync(join(root, 'distribution', 'codex-submissions.json'), 'utf8'));
const repositoryUrl = 'https://github.com/qodo-ai/qodo-skills';

function argumentMap(argv) {
  const values = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith('--') || value === undefined) throw new Error(`Incomplete argument: ${flag ?? '<missing>'}`);
    values.set(flag.slice(2), value);
  }
  return values;
}

function isTrue(value) {
  return value === true || String(value).toLowerCase() === 'true';
}

export function resolveSelection(inputs, providers = marketplaceCatalog.providers) {
  const known = providers.map((provider) => provider.id);
  const selected = isTrue(inputs.all)
    ? known
    : known.filter((id) => isTrue(inputs[id]));
  if (selected.length === 0) throw new Error('Select at least one marketplace or select all.');
  return selected;
}

function provider(id) {
  const value = marketplaceCatalog.providers.find((entry) => entry.id === id);
  if (!value) throw new Error(`Unknown marketplace: ${id}`);
  return value;
}

function releaseContext(tag, commit) {
  const version = catalog.package.version;
  if (tag !== `v${version}`) throw new Error(`Release tag ${tag} does not match catalog version v${version}`);
  const release = JSON.parse(readFileSync(join(root, 'releases', `${tag}.json`), 'utf8'));
  if (release.version !== version) throw new Error(`${tag}: release record does not match the catalog`);
  if (!/^[0-9a-f]{40}$/.test(commit)) throw new Error(`Invalid release commit: ${commit}`);
  return { tag, commit, version, release };
}

function safeSourcePath(path) {
  const source = realpathSync(join(root, path));
  const relativePath = relative(realpathSync(root), source);
  if (relativePath === '..' || relativePath.startsWith(`..${sep}`) || resolve(source) === resolve(root)) {
    throw new Error(`${path}: marketplace source must stay inside the repository`);
  }
  return source;
}

function createOutputRoot(path) {
  const output = resolve(path);
  if (output === resolve(root) || dirname(output) === output) throw new Error(`Unsafe output path: ${path}`);
  if (existsSync(output)) throw new Error(`Output path already exists: ${path}`);
  mkdirSync(output);
  return output;
}

function packageDetails(packageName) {
  const value = catalog.installPackages.find((entry) => entry.name === packageName);
  if (!value) throw new Error(`Unknown install package: ${packageName}`);
  return value;
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function desiredClaudeEntry(listing, context) {
  const details = packageDetails(listing.package);
  return {
    name: listing.id,
    description: details.description,
    author: { name: 'Qodo', email: 'support@qodo.ai' },
    category: 'development',
    source: {
      source: 'git-subdir',
      url: `${repositoryUrl}.git`,
      path: listing.sourcePath,
      ref: 'main',
      sha: context.commit,
    },
    homepage: repositoryUrl,
  };
}

function submissionMarkdown(selectedProvider, context) {
  const packages = selectedProvider.listings.map((listing) => `- \`${listing.id}\` from \`${listing.sourcePath}\``).join('\n');
  const completion = selectedProvider.mode === 'reviewed-portal-snapshot'
    ? 'Publication requires review and an explicit publish action in the provider portal. The protected GitHub environment approval is the release-owner attestation for that external step.'
    : 'Publication is complete only after the provider-visible directory resolves every listing to this exact release commit.';
  return [
    `# ${selectedProvider.displayName} marketplace release`,
    '',
    `- Release: \`${context.tag}\``,
    `- Commit: \`${context.commit}\``,
    `- Version: \`${context.version}\``,
    `- Provider contract: \`${selectedProvider.mode}\``,
    `- Provider entry point: ${selectedProvider.submissionUrl}`,
    `- Support: ${catalog.package.supportUrl}`,
    `- Privacy: ${catalog.package.privacyPolicyUrl}`,
    `- Terms: ${catalog.package.termsOfServiceUrl}`,
    '',
    '## Listings',
    '',
    packages,
    '',
    '## Completion rule',
    '',
    completion,
    '',
  ].join('\n');
}

export function prepareMarketplace(providerId, context, outputPath) {
  const selectedProvider = provider(providerId);
  const output = createOutputRoot(outputPath);
  const listingsRoot = join(output, 'listings');
  mkdirSync(listingsRoot);
  for (const listing of selectedProvider.listings) {
    cpSync(safeSourcePath(listing.sourcePath), join(listingsRoot, listing.id), {
      recursive: true,
      errorOnExist: true,
    });
  }
  const release = {
    schemaVersion: 1,
    provider: providerId,
    providerMode: selectedProvider.mode,
    tag: context.tag,
    commit: context.commit,
    version: context.version,
    listingMetadata: {
      website: catalog.package.homepage,
      support: catalog.package.supportUrl,
      privacyPolicy: catalog.package.privacyPolicyUrl,
      termsOfService: catalog.package.termsOfServiceUrl,
    },
    listings: selectedProvider.listings,
  };
  writeJson(join(output, 'release.json'), release);
  writeFileSync(join(output, 'SUBMISSION.md'), submissionMarkdown(selectedProvider, context));
  if (providerId === 'claude') {
    writeJson(join(output, 'directory-entries.json'), selectedProvider.listings.map((entry) => desiredClaudeEntry(entry, context)));
  }
  if (providerId === 'codex') {
    const submissionsRoot = join(output, 'submissions');
    mkdirSync(submissionsRoot);
    for (const listing of selectedProvider.listings) {
      const submission = codexSubmissions.listings.find((entry) => entry.package === listing.package);
      if (!submission) throw new Error(`Codex submission metadata is missing ${listing.package}`);
      const details = packageDetails(listing.package);
      const skills = details.skills.map((name) => catalog.skills.find((entry) => entry.name === name));
      writeJson(join(submissionsRoot, `${listing.id}.json`), {
        schemaVersion: 1,
        listingId: listing.id,
        package: listing.package,
        release: {
          tag: context.tag,
          commit: context.commit,
          version: context.version,
        },
        listing: {
          displayName: details.displayName,
          description: details.description,
          website: catalog.package.homepage,
          support: catalog.package.supportUrl,
          privacyPolicy: catalog.package.privacyPolicyUrl,
          termsOfService: catalog.package.termsOfServiceUrl,
          starterPrompts: skills.map((skill) => skill.defaultPrompt),
        },
        ...submission,
      });
    }
  }
  return { output, release };
}

function normalizeRepositoryUrl(value) {
  return String(value ?? '').replace(/\.git$/, '').replace(/\/$/, '');
}

export function verifyClaudeDocument(document, context, selectedProvider = provider('claude')) {
  if (document.renames?.['qodo-skills'] !== 'qodo') {
    throw new Error('Claude directory must preserve the qodo-skills to qodo rename');
  }
  const results = [];
  for (const listing of selectedProvider.listings) {
    const entry = document.plugins?.find((candidate) => candidate.name === listing.id);
    if (!entry) throw new Error(`Claude directory is missing ${listing.id}`);
    const source = entry.source;
    if (source?.source !== 'git-subdir') throw new Error(`Claude ${listing.id}: source must be git-subdir`);
    if (normalizeRepositoryUrl(source.url) !== repositoryUrl) throw new Error(`Claude ${listing.id}: wrong repository`);
    if (source.path !== listing.sourcePath) throw new Error(`Claude ${listing.id}: expected path ${listing.sourcePath}`);
    if (source.ref !== 'main') throw new Error(`Claude ${listing.id}: expected ref main`);
    if (source.sha !== context.commit) throw new Error(`Claude ${listing.id}: provider SHA ${source.sha ?? '<missing>'} != ${context.commit}`);
    results.push({ id: listing.id, state: 'provider-visible', commit: source.sha });
  }
  return results;
}

function normalizedEmbeddedJson(text) {
  return text
    .replaceAll('\\u002F', '/')
    .replaceAll('\\u0026', '&')
    .replaceAll('\\"', '"');
}

function embeddedObjectRecords(text) {
  const records = [];
  const collect = (value) => {
    if (!value || typeof value !== 'object') return;
    if (!Array.isArray(value)) records.push(value);
    for (const nested of Object.values(value)) collect(nested);
  };
  try {
    collect(JSON.parse(text));
  } catch {
    // Provider pages may contain escaped JSON records inside HTML/script text.
  }
  const starts = [];
  let quoted = false;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === '{') starts.push(index);
    else if (char === '}' && starts.length > 0) {
      const start = starts.pop();
      try {
        collect(JSON.parse(text.slice(start, index + 1)));
      } catch {
        // Not every brace-delimited provider-page fragment is JSON.
      }
    }
  }
  return records;
}

export function verifyKiroDocument(document, context, selectedProvider = provider('kiro')) {
  const normalized = normalizedEmbeddedJson(document);
  const records = embeddedObjectRecords(normalized);
  const results = [];
  const sourceRef = selectedProvider.sourceRef;
  if (!sourceRef) throw new Error('Kiro marketplace contract is missing sourceRef');
  for (const listing of selectedProvider.listings) {
    const repository = `${repositoryUrl}/tree/${sourceRef}/${listing.sourcePath}`;
    const entry = records.find((candidate) => candidate.name === listing.id);
    if (!entry) throw new Error(`Kiro ${listing.id}: provider listing is missing`);
    if (entry.repositoryUrl !== repository) throw new Error(`Kiro ${listing.id}: wrong repository`);
    if (entry.pathInRepo !== listing.sourcePath) throw new Error(`Kiro ${listing.id}: expected path ${listing.sourcePath}`);
    if (entry.repositoryBranch !== sourceRef) {
      throw new Error(`Kiro ${listing.id}: expected branch ${sourceRef}`);
    }
    results.push({ id: listing.id, state: 'provider-visible', source: repository, branch: sourceRef });
  }
  return results;
}

async function fetchText(url) {
  const headers = { 'user-agent': 'qodo-skills-marketplace-release' };
  if (process.env.GITHUB_TOKEN && url.startsWith('https://api.github.com/')) {
    headers.authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  }
  const response = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.text();
}

export async function verifyMarketplace(providerId, context) {
  const selectedProvider = provider(providerId);
  if (selectedProvider.mode === 'reviewed-portal-snapshot') {
    throw new Error(`${selectedProvider.displayName} has no documented publishing API; use the protected marketplace-codex environment after portal publication`);
  }
  if (providerId === 'claude') {
    const document = JSON.parse(await fetchText(selectedProvider.directoryManifestUrl));
    return verifyClaudeDocument(document, context, selectedProvider);
  }
  if (providerId === 'kiro') {
    const results = verifyKiroDocument(await fetchText(selectedProvider.directoryUrl), context, selectedProvider);
    const sourceRef = selectedProvider.sourceRef;
    const source = JSON.parse(await fetchText(
      `https://api.github.com/repos/qodo-ai/qodo-skills/commits/${encodeURIComponent(sourceRef)}`,
    ));
    if (source.sha !== context.commit) {
      throw new Error(`Kiro follows ${sourceRef} at ${source.sha ?? '<missing>'}, not release commit ${context.commit}`);
    }
    return results.map((result) => ({ ...result, commit: source.sha }));
  }
  throw new Error(`${providerId}: no verifier implemented`);
}

function writeGithubOutput(values) {
  const path = process.env.GITHUB_OUTPUT;
  if (!path) return;
  for (const [name, value] of Object.entries(values)) appendFileSync(path, `${name}=${value}\n`);
}

function writeSummary(lines) {
  const path = process.env.GITHUB_STEP_SUMMARY;
  if (path) appendFileSync(path, `${lines.join('\n')}\n`);
}

async function main(argv) {
  const [command, ...rest] = argv;
  const args = argumentMap(rest);
  if (command === 'plan') {
    const selected = resolveSelection(Object.fromEntries(args));
    const matrix = JSON.stringify({ include: selected.map((id) => ({ provider: id })) });
    const verifiableMatrix = JSON.stringify({
      include: selected
        .filter((id) => provider(id).mode !== 'reviewed-portal-snapshot')
        .map((id) => ({ provider: id })),
    });
    const outputs = {
      matrix,
      verifiable_matrix: verifiableMatrix,
      has_verifiable: String(JSON.parse(verifiableMatrix).include.length > 0),
      selected: selected.join(','),
    };
    for (const id of marketplaceCatalog.providers.map((entry) => entry.id)) outputs[id] = String(selected.includes(id));
    writeGithubOutput(outputs);
    console.log(matrix);
    return;
  }
  const providerId = args.get('provider');
  const context = releaseContext(args.get('tag'), args.get('commit'));
  if (command === 'prepare') {
    const result = prepareMarketplace(providerId, context, args.get('output'));
    writeGithubOutput({ output: result.output, mode: result.release.providerMode });
    console.log(JSON.stringify(result.release));
    return;
  }
  if (command === 'verify') {
    const results = await verifyMarketplace(providerId, context);
    writeSummary([
      `## ${provider(providerId).displayName} marketplace verified`,
      '',
      `All selected listings resolve to \`${context.tag}\` at \`${context.commit}\`.`,
    ]);
    console.log(JSON.stringify(results));
    return;
  }
  if (command === 'attest' && providerId === 'codex') {
    writeSummary([
      '## Codex marketplace publication attested',
      '',
      `The protected \`marketplace-codex\` environment was approved for \`${context.tag}\` at \`${context.commit}\`.`,
      'This is a human release-owner attestation because OpenAI exposes portal publication, not a documented publishing API.',
    ]);
    console.log(JSON.stringify({ provider: providerId, state: 'release-owner-attested', ...context }));
    return;
  }
  throw new Error(`Unknown marketplace release command: ${command}`);
}

if (realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}

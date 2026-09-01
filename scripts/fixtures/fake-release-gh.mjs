#!/usr/bin/env node
/** Deterministic GitHub CLI double for executing the release shell path in CI. */
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';

const args = process.argv.slice(2);
const statePath = process.env.FAKE_GH_STATE;
if (!statePath) throw new Error('FAKE_GH_STATE is required');

const readState = () => {
  const state = existsSync(statePath)
    ? JSON.parse(readFileSync(statePath, 'utf8'))
    : { exists: false, draft: false, immutable: false, assets: [], downloads: 0, edits: 0 };
  const tag = process.env.FAKE_RELEASE_TAG
    ?? args.find((arg) => /^v\d+\.\d+\.\d+$/.test(arg)) ?? 'v0.0.0';
  return {
    ...state,
    name: state.name ?? `Qodo skills ${tag}`,
    body: state.body ?? (process.env.QODO_RELEASE_NOTES_FILE
      ? readFileSync(process.env.QODO_RELEASE_NOTES_FILE, 'utf8') : ''),
  };
};
const writeState = (state) => writeFileSync(statePath, `${JSON.stringify(state)}\n`);
const endpoint = args.find((arg) => arg.startsWith('repos/')
  || arg.startsWith('installation/') || arg.startsWith('https://uploads.github.com/')) ?? '';
const jqIndex = args.indexOf('--jq');
const query = jqIndex >= 0 ? args[jqIndex + 1] ?? '' : '';

if (args[0] === 'api' && endpoint.startsWith('installation/repositories')) {
  process.stdout.write(`${process.env.FAKE_INSTALLATION_REPOSITORIES ?? 'qodo-ai/qodo-skills'}\n`);
} else if (args[0] === 'api' && endpoint.endsWith('/immutable-releases')) {
  process.stdout.write(`${process.env.FAKE_IMMUTABLE_RELEASES ?? 'true'}\n`);
} else if (args[0] === 'api' && endpoint.includes('/rulesets?')) {
  process.stdout.write(`${process.env.FAKE_RULESET_IDS ?? '21488082'}\n`);
} else if (args[0] === 'api' && /\/rulesets\/[^/]+$/.test(endpoint)) {
  const creationRejected = query.includes('index("creation")') && query.includes('== null');
  const valid = process.env.FAKE_RULESET_VALID !== 'false'
    && (process.env.FAKE_RULESET_HAS_CREATION !== 'true' || creationRejected === false);
  process.stdout.write(`${valid}\n`);
} else if (args[0] === 'api' && endpoint.endsWith('/releases?per_page=100')) {
  const state = readState();
  if (process.env.FAKE_RELEASE_LOOKUP_ERROR === 'true') {
    process.stderr.write('release list unavailable\n');
    process.exit(1);
  }
  if (state.exists) {
    process.stdout.write(`123\t${state.draft}\n`);
    if (process.env.FAKE_DUPLICATE_RELEASES === 'true') {
      process.stdout.write(`124\t${state.draft}\n`);
    }
  }
} else if (args[0] === 'api' && /\/releases\/123$/.test(endpoint)) {
  const state = readState();
  if (!state.exists) process.exit(1);
  if (args[args.indexOf('--method') + 1] === 'PATCH') {
    const publishing = args.includes('draft=false');
    const containing = args.includes('draft=true');
    if (publishing === containing) throw new Error('Release patch must set exactly one draft state');
    writeState({
      ...state,
      draft: containing,
      immutable: publishing && process.env.FAKE_PUBLISHED_MUTABLE !== 'true',
      edits: state.edits + 1,
    });
  } else if (query === '.draft') process.stdout.write(`${state.draft}\n`);
  else if (query === '.immutable') process.stdout.write(`${state.immutable}\n`);
  else if (query === '.name') process.stdout.write(`${state.name}\n`);
  else if (query.includes('.upload_url')) process.stdout.write('https://uploads.github.com/repos/qodo-ai/qodo-skills/releases/123/assets\n');
  else if (query.includes('@base64')) process.stdout.write(`${Buffer.from(state.body).toString('base64')}\n`);
  else if (query === '.assets[].name') process.stdout.write(`${state.assets.join('\n')}\n`);
  else if (query.includes('[.id, .name]')) process.stdout.write(
    `${state.assets.map((name, index) => `${1000 + index}\t${name}`).join('\n')}\n`,
  );
  else if (query.includes('.assets[].name')) process.stdout.write(`${[...state.assets].sort().join(' ')}\n`);
  else throw new Error(`Unsupported release query: ${query}`);
} else if (args[0] === 'api' && endpoint.startsWith('https://uploads.github.com/')) {
  const state = readState();
  if (!state.exists || !state.draft) throw new Error('Numeric upload requires an existing draft');
  const assetPath = args[args.indexOf('--input') + 1];
  const assetName = new URL(endpoint).searchParams.get('name');
  if (!assetPath || !assetName || state.assets.includes(assetName)) throw new Error('Invalid numeric asset upload');
  mkdirSync(process.env.FAKE_GH_ASSETS, { recursive: true });
  copyFileSync(assetPath, join(process.env.FAKE_GH_ASSETS, assetName));
  writeState({ ...state, assets: [...state.assets, assetName] });
} else if (args[0] === 'api' && /\/releases\/assets\/\d+$/.test(endpoint)) {
  const state = readState();
  const assetIndex = Number(endpoint.match(/(\d+)$/)[1]) - 1000;
  const assetName = state.assets[assetIndex];
  if (!state.exists || !assetName || !args.includes('Accept: application/octet-stream')) {
    throw new Error('Invalid numeric asset download');
  }
  const content = process.env.FAKE_CORRUPT_DOWNLOAD === 'draft' && state.draft
    && assetName === 'qodo-skills-index.json' ? Buffer.from('corrupt\n')
    : readFileSync(join(process.env.FAKE_GH_ASSETS, assetName));
  process.stdout.write(content);
  writeState({ ...state, downloads: state.downloads + 1 });
} else if (args[0] === 'release' && args[1] === 'view') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '')) throw new Error('Invalid release view tag');
  process.exit(readState().exists ? 0 : 1);
} else if (args[0] === 'release' && args[1] === 'delete-asset') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '') || !args[3] || !args.includes('--yes')) {
    throw new Error('Release asset deletion must specify a valid tag, asset, and --yes');
  }
  const state = readState();
  writeState({
    ...state,
    assets: state.assets.filter((asset) => asset !== args[3]),
    deletedAssets: [...(state.deletedAssets ?? []), args[3]],
  });
} else if (args[0] === 'release' && (args[1] === 'create' || args[1] === 'upload')) {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '')) throw new Error('Invalid release mutation tag');
  if (args[1] === 'create' && (!args.includes('--draft') || !args.includes('--verify-tag'))) {
    throw new Error('Release creation must use --draft and --verify-tag');
  }
  if (args[1] === 'upload' && args.includes('--clobber')) {
    throw new Error('Release upload must never overwrite an existing asset');
  }
  const state = readState();
  const assetPattern = /(?:qodo-(?:skills-index|cli-managed-bundle)\.json(?:\.sha256)?|qodo-enterprise-manifest\.json(?:\.sha256)?|qodo-enterprise-bundle-v\d+\.\d+\.\d+\.tar\.gz(?:\.sha256)?)$/;
  if (args[1] === 'upload' && (!state.exists || !state.draft)) {
    throw new Error('Release upload requires an existing draft');
  }
  const assetPaths = args.filter((arg) => assetPattern.test(arg));
  const assetNames = assetPaths.map((path) => basename(path));
  if (assetNames.some((asset) => state.assets.includes(asset))) {
    throw new Error('Release upload must not replace an existing asset');
  }
  mkdirSync(process.env.FAKE_GH_ASSETS, { recursive: true });
  for (const path of assetPaths) copyFileSync(path, join(process.env.FAKE_GH_ASSETS, basename(path)));
  writeState({
    ...state,
    exists: true,
    draft: true,
    immutable: false,
    assets: [...state.assets, ...assetNames],
    ...(args[1] === 'create' ? {
      name: args[args.indexOf('--title') + 1],
      body: readFileSync(args[args.indexOf('--notes-file') + 1], 'utf8'),
    } : {}),
  });
} else if (args[0] === 'release' && args[1] === 'download') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '') || args[args.indexOf('--pattern') + 1] !== 'qodo-*') {
    throw new Error('Invalid release download');
  }
  const state = readState();
  if (state.draft) throw new Error('Draft releases cannot be resolved by tag');
  const dir = args[args.indexOf('--dir') + 1];
  mkdirSync(dir, { recursive: true });
  for (const asset of state.assets) copyFileSync(join(process.env.FAKE_GH_ASSETS, asset), join(dir, asset));
  const downloads = state.downloads + 1;
  if (
    process.env.FAKE_CORRUPT_DOWNLOAD === 'published'
  ) {
    writeFileSync(join(dir, 'qodo-skills-index.json'), 'corrupt\n');
  }
  writeState({ ...state, downloads });
} else {
  throw new Error(`Unsupported fake gh call: ${args.join(' ')}`);
}

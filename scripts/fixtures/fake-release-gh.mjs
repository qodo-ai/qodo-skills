#!/usr/bin/env node
/** Deterministic GitHub CLI double for executing the release shell path in CI. */
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';

const args = process.argv.slice(2);
const statePath = process.env.FAKE_GH_STATE;
if (!statePath) throw new Error('FAKE_GH_STATE is required');

const readState = () => existsSync(statePath)
  ? JSON.parse(readFileSync(statePath, 'utf8'))
  : { exists: false, draft: false, immutable: false, assets: [], downloads: 0, edits: 0 };
const writeState = (state) => writeFileSync(statePath, `${JSON.stringify(state)}\n`);
const endpoint = args.find((arg) => arg.startsWith('repos/')) ?? '';
const jqIndex = args.indexOf('--jq');
const query = jqIndex >= 0 ? args[jqIndex + 1] ?? '' : '';

if (args[0] === 'api' && endpoint.endsWith('/immutable-releases')) {
  process.stdout.write(`${process.env.FAKE_IMMUTABLE_RELEASES ?? 'true'}\n`);
} else if (args[0] === 'api' && endpoint.includes('/rulesets?')) {
  process.stdout.write(`${process.env.FAKE_RULESET_IDS ?? '21488082'}\n`);
} else if (args[0] === 'api' && /\/rulesets\/[^/]+$/.test(endpoint)) {
  const creationRejected = query.includes('index("creation")') && query.includes('== null');
  const valid = process.env.FAKE_RULESET_VALID !== 'false'
    && (process.env.FAKE_RULESET_HAS_CREATION !== 'true' || creationRejected === false);
  process.stdout.write(`${valid}\n`);
} else if (args[0] === 'api' && endpoint.includes('/releases/tags/')) {
  const state = readState();
  if (args.includes('--include')) {
    if (process.env.FAKE_RELEASE_LOOKUP_ERROR === 'true') {
      process.stderr.write('HTTP/2.0 503 Service Unavailable\n');
      process.exit(1);
    }
    process.stdout.write(`HTTP/2.0 ${state.exists ? '200 OK' : '404 Not Found'}\n`);
    if (!state.exists) process.exit(1);
  } else if (!state.exists) process.exit(1);
  else if (query === '.draft') process.stdout.write(`${state.draft}\n`);
  else if (query === '.immutable') process.stdout.write(`${state.immutable}\n`);
  else if (query.includes('.assets[].name')) process.stdout.write(`${[...state.assets].sort().join(' ')}\n`);
  else throw new Error(`Unsupported release query: ${query}`);
} else if (args[0] === 'release' && args[1] === 'view') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '')) throw new Error('Invalid release view tag');
  process.exit(readState().exists ? 0 : 1);
} else if (args[0] === 'release' && (args[1] === 'create' || args[1] === 'upload')) {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '')) throw new Error('Invalid release mutation tag');
  if (args[1] === 'create' && (!args.includes('--draft') || !args.includes('--verify-tag'))) {
    throw new Error('Release creation must use --draft and --verify-tag');
  }
  if (args[1] === 'upload' && !args.includes('--clobber')) {
    throw new Error('Release upload must use --clobber');
  }
  const state = readState();
  const assetPaths = args.filter((arg) => arg.endsWith('qodo-skills-index.json') || arg.endsWith('qodo-skills-index.json.sha256'));
  mkdirSync(process.env.FAKE_GH_ASSETS, { recursive: true });
  for (const path of assetPaths) copyFileSync(path, join(process.env.FAKE_GH_ASSETS, basename(path)));
  writeState({
    ...state,
    exists: true,
    draft: true,
    immutable: false,
    assets: assetPaths.map((path) => basename(path)),
  });
} else if (args[0] === 'release' && args[1] === 'download') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '') || args[args.indexOf('--pattern') + 1] !== 'qodo-skills-index.json*') {
    throw new Error('Invalid release download');
  }
  const state = readState();
  const dir = args[args.indexOf('--dir') + 1];
  mkdirSync(dir, { recursive: true });
  for (const asset of state.assets) copyFileSync(join(process.env.FAKE_GH_ASSETS, asset), join(dir, asset));
  const downloads = state.downloads + 1;
  if (
    (process.env.FAKE_CORRUPT_DOWNLOAD === 'draft' && downloads === 1)
    || (process.env.FAKE_CORRUPT_DOWNLOAD === 'published' && downloads === 2)
  ) {
    writeFileSync(join(dir, 'qodo-skills-index.json'), 'corrupt\n');
  }
  writeState({ ...state, downloads });
} else if (args[0] === 'release' && args[1] === 'edit') {
  if (!/^v\d+\.\d+\.\d+$/.test(args[2] ?? '') || !args.includes('--draft=false')) {
    throw new Error('Release publication must specify a valid tag and --draft=false');
  }
  const state = readState();
  writeState({
    ...state,
    draft: false,
    immutable: process.env.FAKE_PUBLISHED_MUTABLE !== 'true',
    edits: state.edits + 1,
  });
} else {
  throw new Error(`Unsupported fake gh call: ${args.join(' ')}`);
}

#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEFAULT_REPOSITORY = 'qodo-ai/qodo-skills';
const DEFAULT_GITHUB_API = 'https://api.github.com';
const DEFAULT_VERSION_URL = 'https://get.qodo.ai/version.json';
const WORKFLOW = 'ship-marketplaces.yml';
const DEFAULT_BRANCH = 'main';
const TAG_PATTERN = /^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const MAX_JSON_BYTES = 2 * 1024 * 1024;
const MAX_COMPATIBILITY_ASSET_BYTES = 8 * 1024 * 1024;

function requireTag(tag) {
  if (typeof tag !== 'string' || !TAG_PATTERN.test(tag)) {
    throw new Error(`invalid stable skills tag: ${JSON.stringify(tag)}`);
  }
  return tag;
}

function compareTags(left, right) {
  const a = TAG_PATTERN.exec(requireTag(left)).slice(1).map(BigInt);
  const b = TAG_PATTERN.exec(requireTag(right)).slice(1).map(BigInt);
  for (let index = 0; index < a.length; index += 1) {
    if (a[index] < b[index]) return -1;
    if (a[index] > b[index]) return 1;
  }
  return 0;
}

async function readBytes(fetchImpl, url, token = '', maximumBytes = MAX_JSON_BYTES) {
  const headers = {
    accept: 'application/vnd.github+json',
    'user-agent': 'qodo-marketplace-auto-start',
    'x-github-api-version': '2022-11-28',
  };
  if (token && url.startsWith('https://api.github.com/')) headers.authorization = `Bearer ${token}`;
  const response = await fetchImpl(url, { headers, signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new Error(`could not read ${url}: HTTP ${response.status}`);
  const declaredLength = Number(response.headers.get('content-length'));
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) {
    throw new Error(`response from ${url} exceeds ${maximumBytes} bytes`);
  }
  if (!response.body) return Buffer.alloc(0);
  const reader = response.body.getReader();
  const chunks = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > maximumBytes) {
      await reader.cancel();
      throw new Error(`response from ${url} exceeds ${maximumBytes} bytes`);
    }
    chunks.push(Buffer.from(value));
  }
  return Buffer.concat(chunks, length);
}

async function readJson(fetchImpl, url, token = '') {
  try {
    return JSON.parse((await readBytes(fetchImpl, url, token)).toString('utf8'));
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('could not read ')) throw error;
    throw new Error(`could not parse JSON from ${url}`, { cause: error });
  }
}

async function readWorkflowRuns(fetchImpl, baseUrl, token) {
  const runs = [];
  for (let page = 1; page <= 100; page += 1) {
    const payload = await readJson(fetchImpl, `${baseUrl}&page=${page}`, token);
    if (!payload || !Array.isArray(payload.workflow_runs)) {
      throw new Error('GitHub returned an invalid marketplace workflow-run list');
    }
    runs.push(...payload.workflow_runs);
    if (payload.workflow_runs.length < 100) return runs;
  }
  throw new Error('GitHub marketplace workflow-run pagination exceeded 100 pages');
}

function releaseTagFromRun(run) {
  if (run?.head_branch !== DEFAULT_BRANCH || typeof run.display_title !== 'string') return null;
  const prefix = 'Ship marketplaces ';
  if (!run.display_title.startsWith(prefix)) return null;
  const tag = run.display_title.slice(prefix.length);
  return TAG_PATTERN.test(tag) ? tag : null;
}

async function verifyCompatibilityAssets(fetchImpl, versionUrl, skills, tag, sourceCommit) {
  const version = tag.slice(1);
  const expected = {
    releaseIndex: `skills/releases/${tag}/qodo-skills-index.json`,
    releaseIndexChecksum: `skills/releases/${tag}/qodo-skills-index.json.sha256`,
    cliManagedBundle: `skills/releases/${tag}/qodo-cli-managed-bundle.json`,
    cliManagedChecksum: `skills/releases/${tag}/qodo-cli-managed-bundle.json.sha256`,
  };
  for (const [key, path] of Object.entries(expected)) {
    if (skills?.[key] !== path) throw new Error(`production compatibility ${key} does not match ${tag}`);
  }
  const base = new URL(versionUrl);
  const load = async (path, maximumBytes) => {
    const url = new URL(path, base);
    if (url.origin !== base.origin) throw new Error(`production compatibility asset escaped ${base.origin}`);
    return readBytes(fetchImpl, url.href, '', maximumBytes);
  };
  const [index, indexChecksum, bundle, bundleChecksum] = await Promise.all([
    load(expected.releaseIndex, MAX_COMPATIBILITY_ASSET_BYTES),
    load(expected.releaseIndexChecksum, 512),
    load(expected.cliManagedBundle, MAX_COMPATIBILITY_ASSET_BYTES),
    load(expected.cliManagedChecksum, 512),
  ]);
  const verifyDigest = (name, body, checksum) => {
    const expectedDigest = checksum.toString('utf8').trim().split(/\s+/u)[0];
    if (!/^[a-f0-9]{64}$/.test(expectedDigest)) throw new Error(`invalid production checksum for ${name}`);
    const actual = createHash('sha256').update(body).digest('hex');
    if (actual !== expectedDigest) throw new Error(`production checksum mismatch for ${name}`);
  };
  verifyDigest('qodo-skills-index.json', index, indexChecksum);
  verifyDigest('qodo-cli-managed-bundle.json', bundle, bundleChecksum);

  let indexDocument;
  let bundleDocument;
  try {
    indexDocument = JSON.parse(index.toString('utf8'));
    bundleDocument = JSON.parse(bundle.toString('utf8'));
  } catch (error) {
    throw new Error('production compatibility assets are not valid JSON', { cause: error });
  }
  if (![1, 2].includes(indexDocument?.schemaVersion) || indexDocument.packageVersion !== version) {
    throw new Error(`production compatibility index identity does not match ${tag}`);
  }
  if (indexDocument.schemaVersion === 2 && indexDocument.sourceCommit !== sourceCommit) {
    throw new Error(`production compatibility index source does not match ${sourceCommit}`);
  }
  if (
    bundleDocument?.distribution !== 'qodo-cli-managed' ||
    bundleDocument.packageVersion !== version ||
    bundleDocument.source?.tag !== tag
  ) {
    throw new Error(`production compatibility bundle identity does not match ${tag}`);
  }
}

export async function planMarketplaceAutoStart({
  requestedTag = '',
  repository = DEFAULT_REPOSITORY,
  githubApi = DEFAULT_GITHUB_API,
  versionUrl = DEFAULT_VERSION_URL,
  token = '',
  fetchImpl = fetch,
} = {}) {
  const version = await readJson(fetchImpl, versionUrl);
  const publicTag = requireTag(version?.skills?.releaseTag);
  const tag = requestedTag ? requireTag(requestedTag) : publicTag;
  if (tag !== publicTag) {
    throw new Error(`marketplace release ${tag} is not production-ready; public compatibility is ${publicTag}`);
  }

  const release = await readJson(
    fetchImpl,
    `${githubApi}/repos/${repository}/releases/tags/${encodeURIComponent(tag)}`,
    token,
  );
  if (
    !release ||
    release.tag_name !== tag ||
    release.draft !== false ||
    release.prerelease !== false ||
    release.immutable !== true
  ) {
    throw new Error(`skills release ${tag} is not published, stable, and immutable`);
  }

  const commit = await readJson(
    fetchImpl,
    `${githubApi}/repos/${repository}/commits/${encodeURIComponent(tag)}`,
    token,
  );
  if (!commit || typeof commit.sha !== 'string' || !/^[a-f0-9]{40}$/.test(commit.sha)) {
    throw new Error(`could not resolve the immutable commit for ${tag}`);
  }

  await verifyCompatibilityAssets(fetchImpl, versionUrl, version.skills, tag, commit.sha);

  const runsUrl =
    `${githubApi}/repos/${repository}/actions/workflows/${WORKFLOW}/runs?` +
    `event=workflow_dispatch&branch=${DEFAULT_BRANCH}&per_page=100`;
  const title = `Ship marketplaces ${tag}`;
  const workflowRuns = await readWorkflowRuns(fetchImpl, runsUrl, token);
  const existing = workflowRuns.find(
    (run) => run?.display_title === title && run?.head_branch === DEFAULT_BRANCH,
  );
  const priorTags = workflowRuns.map(releaseTagFromRun).filter(Boolean);
  const watermark = priorTags.sort(compareTags).at(-1) ?? null;
  if (watermark && compareTags(tag, watermark) < 0) {
    throw new Error(`refusing marketplace rollback from ${watermark} to ${tag}`);
  }

  return {
    schemaVersion: 1,
    repository,
    tag,
    sourceCommit: commit.sha,
    compatibilityVerified: true,
    watermark,
    needed: existing === undefined,
    existingRun: existing
      ? {
          id: existing.id,
          status: existing.status,
          conclusion: existing.conclusion ?? null,
          url: existing.html_url ?? null,
        }
      : null,
  };
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index];
    const value = argv[index + 1];
    if (!['--tag', '--repository', '--github-api', '--version-url'].includes(name) || value === undefined) {
      throw new Error(`unknown or incomplete argument: ${name}`);
    }
    const key = {
      '--tag': 'requestedTag',
      '--repository': 'repository',
      '--github-api': 'githubApi',
      '--version-url': 'versionUrl',
    }[name];
    options[key] = value;
    index += 1;
  }
  return options;
}

async function main() {
  const plan = await planMarketplaceAutoStart({
    ...parseArgs(process.argv.slice(2)),
    token: process.env.GH_TOKEN || process.env.GITHUB_TOKEN || '',
  });
  process.stdout.write(`${JSON.stringify(plan)}\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  main().catch((error) => {
    process.stderr.write(`marketplace-auto-start: ${error.message}\n`);
    process.exitCode = 1;
  });
}

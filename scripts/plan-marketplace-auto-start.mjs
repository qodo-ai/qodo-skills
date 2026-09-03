#!/usr/bin/env node

import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEFAULT_REPOSITORY = 'qodo-ai/qodo-skills';
const DEFAULT_GITHUB_API = 'https://api.github.com';
const DEFAULT_VERSION_URL = 'https://get.qodo.ai/version.json';
const WORKFLOW = 'ship-marketplaces.yml';
const TAG_PATTERN = /^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

function requireTag(tag) {
  if (typeof tag !== 'string' || !TAG_PATTERN.test(tag)) {
    throw new Error(`invalid stable skills tag: ${JSON.stringify(tag)}`);
  }
  return tag;
}

async function readJson(fetchImpl, url, token = '') {
  const headers = {
    accept: 'application/vnd.github+json',
    'user-agent': 'qodo-marketplace-auto-start',
    'x-github-api-version': '2022-11-28',
  };
  if (token && url.startsWith('https://api.github.com/')) headers.authorization = `Bearer ${token}`;
  const response = await fetchImpl(url, { headers, signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new Error(`could not read ${url}: HTTP ${response.status}`);
  try {
    return await response.json();
  } catch (error) {
    throw new Error(`could not parse JSON from ${url}`, { cause: error });
  }
}

async function findExistingRun(fetchImpl, baseUrl, title, token) {
  for (let page = 1; page <= 100; page += 1) {
    const payload = await readJson(fetchImpl, `${baseUrl}&page=${page}`, token);
    if (!payload || !Array.isArray(payload.workflow_runs)) {
      throw new Error('GitHub returned an invalid marketplace workflow-run list');
    }
    const existing = payload.workflow_runs.find((run) => run?.display_title === title);
    if (existing) return existing;
    if (payload.workflow_runs.length < 100) return null;
  }
  throw new Error('GitHub marketplace workflow-run pagination exceeded 100 pages');
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

  const title = `Ship marketplaces ${tag}`;
  const existing = await findExistingRun(
    fetchImpl,
    `${githubApi}/repos/${repository}/actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=100`,
    title,
    token,
  );

  return {
    schemaVersion: 1,
    repository,
    tag,
    sourceCommit: commit.sha,
    needed: existing === null,
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

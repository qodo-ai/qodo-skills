/** Atomically hold one cross-tag marketplace release across provider approval waits. */
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const LOCK_BRANCH = 'qodo-marketplace-release-lock';
const LOCK_REF = `refs/heads/${LOCK_BRANCH}`;
const MESSAGE_PREFIX = 'qodo-marketplace-release-lock\n';

function required(value, name, pattern) {
  if (!value || !pattern.test(value)) throw new Error(`${name} is missing or invalid`);
  return value;
}

export function releaseLockContext(environment = process.env) {
  return {
    repository: required(environment.GITHUB_REPOSITORY, 'GITHUB_REPOSITORY', /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/),
    runId: required(environment.GITHUB_RUN_ID, 'GITHUB_RUN_ID', /^[1-9][0-9]*$/),
    releaseTag: required(environment.RELEASE_TAG, 'RELEASE_TAG', /^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/),
    commit: required(environment.GITHUB_SHA, 'GITHUB_SHA', /^[a-f0-9]{40}$/i),
  };
}

function apiPath(context, suffix) {
  return `/repos/${context.repository}${suffix}`;
}

function lockMessage(owner) {
  return `${MESSAGE_PREFIX}${JSON.stringify(owner)}`;
}

function parseOwner(message) {
  if (typeof message !== 'string' || !message.startsWith(MESSAGE_PREFIX)) {
    throw new Error(`Marketplace release lock ${LOCK_REF} has invalid owner metadata`);
  }
  let owner;
  try {
    owner = JSON.parse(message.slice(MESSAGE_PREFIX.length));
  } catch {
    throw new Error(`Marketplace release lock ${LOCK_REF} has invalid owner metadata`);
  }
  if (
    !['active', 'released'].includes(owner?.state)
    || !/^[1-9][0-9]*$/.test(owner?.runId ?? '')
    || !/^v\d+\.\d+\.\d+$/.test(owner?.releaseTag ?? '')
    || Number.isNaN(Date.parse(owner?.createdAt ?? ''))
    || (owner.state === 'released' && Number.isNaN(Date.parse(owner?.releasedAt ?? '')))
  ) {
    throw new Error(`Marketplace release lock ${LOCK_REF} has invalid owner metadata`);
  }
  return owner;
}

async function readCommit(context, api, sha) {
  const commit = await api({ method: 'GET', path: apiPath(context, `/git/commits/${sha}`) });
  if (!/^[a-f0-9]{40}$/i.test(commit?.tree?.sha ?? '')) {
    throw new Error(`Marketplace release lock ${LOCK_REF} points to an invalid commit`);
  }
  return commit;
}

async function readLock(context, api) {
  let ref;
  try {
    ref = await api({ method: 'GET', path: apiPath(context, `/git/ref/heads/${LOCK_BRANCH}`) });
  } catch (error) {
    if (error.status === 404) return undefined;
    throw error;
  }
  if (ref?.object?.type !== 'commit' || !/^[a-f0-9]{40}$/i.test(ref.object.sha ?? '')) {
    throw new Error(`Marketplace release lock ${LOCK_REF} is not a commit ref`);
  }
  const commit = await readCommit(context, api, ref.object.sha);
  return { sha: ref.object.sha, tree: commit.tree.sha, owner: parseOwner(commit.message) };
}

async function createLockCommit(context, api, owner, parent) {
  const base = parent ?? {
    sha: context.commit,
    tree: (await readCommit(context, api, context.commit)).tree.sha,
  };
  return api({
    method: 'POST',
    path: apiPath(context, '/git/commits'),
    body: {
      message: lockMessage(owner),
      tree: base.tree,
      parents: [base.sha],
    },
  });
}

function owns(owner, context, state = 'active') {
  return owner?.state === state && owner.runId === context.runId && owner.releaseTag === context.releaseTag;
}

async function advanceLock(context, api, observed, owner) {
  const candidate = await createLockCommit(context, api, owner, observed);
  if (!/^[a-f0-9]{40}$/i.test(candidate?.sha ?? '')) {
    throw new Error('GitHub did not return a commit for the marketplace release lock');
  }
  try {
    if (observed) {
      await api({
        method: 'PATCH',
        path: apiPath(context, `/git/refs/heads/${LOCK_BRANCH}`),
        body: { sha: candidate.sha, force: false },
      });
    } else {
      await api({
        method: 'POST',
        path: apiPath(context, '/git/refs'),
        body: { ref: LOCK_REF, sha: candidate.sha },
      });
    }
  } catch (error) {
    if (![409, 422].includes(error.status)) throw error;
    return { advanced: false, current: await readLock(context, api).catch(() => undefined) };
  }
  return { advanced: true };
}

export async function acquireReleaseLock(context, api, now = new Date()) {
  const existing = await readLock(context, api);
  if (owns(existing?.owner, context)) return existing.owner;
  if (existing?.owner?.state === 'active') {
    let ownerRun;
    try {
      ownerRun = await api({
        method: 'GET',
        path: apiPath(context, `/actions/runs/${existing.owner.runId}`),
      });
    } catch (error) {
      if (error.status !== 404) throw error;
    }
    if (ownerRun && ownerRun.status !== 'completed') {
      throw new Error(
        `Marketplace release ${existing.owner.releaseTag} is still active: ${ownerRun.html_url ?? `run ${existing.owner.runId}`}`,
      );
    }
  }

  const owner = {
    state: 'active',
    runId: context.runId,
    releaseTag: context.releaseTag,
    createdAt: now.toISOString(),
  };
  const result = await advanceLock(context, api, existing, owner);
  if (result.advanced || owns(result.current?.owner, context)) return owner;
  if (result.current?.owner?.state === 'active') {
    throw new Error(`Marketplace release ${result.current.owner.releaseTag} acquired the release lock first`);
  }
  throw new Error('Marketplace release lock changed while it was being acquired; retry the workflow');
}

export async function releaseReleaseLock(context, api, now = new Date()) {
  const existing = await readLock(context, api);
  if (!owns(existing?.owner, context)) return false;
  const released = {
    ...existing.owner,
    state: 'released',
    releasedAt: now.toISOString(),
  };
  const result = await advanceLock(context, api, existing, released);
  return result.advanced || owns(result.current?.owner, context, 'released');
}

function githubApi(token, baseUrl = process.env.GITHUB_API_URL ?? 'https://api.github.com') {
  const root = new URL(baseUrl);
  if (root.protocol !== 'https:' || root.username || root.password || root.search || root.hash) {
    throw new Error('GITHUB_API_URL must be a credential-free HTTPS origin');
  }
  return async ({ method, path, body }) => {
    const response = await fetch(new URL(path.replace(/^\//, ''), `${root.toString().replace(/\/$/, '')}/`), {
      method,
      headers: {
        accept: 'application/vnd.github+json',
        authorization: `Bearer ${token}`,
        'x-github-api-version': '2022-11-28',
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
      signal: AbortSignal.timeout(15_000),
    });
    const text = await response.text();
    if (!response.ok) {
      const error = new Error(`GitHub API ${method} ${path} failed with ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return text ? JSON.parse(text) : {};
  };
}

async function main() {
  const command = process.argv[2];
  if (!['acquire', 'release'].includes(command)) {
    throw new Error('Usage: node scripts/marketplace-release-lock.mjs acquire|release');
  }
  const token = required(process.env.GITHUB_TOKEN, 'GITHUB_TOKEN', /\S/);
  const context = releaseLockContext();
  const api = githubApi(token);
  if (command === 'acquire') {
    const owner = await acquireReleaseLock(context, api);
    console.log(`Acquired marketplace release lock for ${owner.releaseTag} (run ${owner.runId}).`);
  } else {
    const released = await releaseReleaseLock(context, api);
    console.log(released ? 'Released marketplace release lock.' : 'Marketplace release lock is not owned by this run.');
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}

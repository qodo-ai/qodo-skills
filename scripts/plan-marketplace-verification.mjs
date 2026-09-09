/** Select immutable provider targets without publishing or acquiring the shipping lock. */
import { appendFileSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compareTags, readJson, readWorkflowRuns, requireTag } from './plan-marketplace-auto-start.mjs';

const repository = 'qodo-ai/qodo-skills';
const api = `https://api.github.com/repos/${repository}`;
const catalog = JSON.parse(readFileSync(new URL('../distribution/marketplaces.json', import.meta.url), 'utf8'));
const providers = catalog.providers.filter((entry) => entry.mode !== 'reviewed-portal-snapshot').map((entry) => entry.id);

async function readJobs(run, fetchImpl, token) {
  const jobs = [];
  for (let page = 1; page <= 100; page += 1) {
    // Bind evidence to the successful attempt, not jobs from another rerun.
    const result = await readJson(fetchImpl,
      `${api}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs?per_page=100&page=${page}`, token);
    if (!Array.isArray(result?.jobs)) throw new Error('GitHub returned an invalid shipping job list');
    jobs.push(...result.jobs);
    if (result.jobs.length < 100) return jobs;
  }
  throw new Error('Shipping job pagination exceeded 100 pages');
}

export async function resolveVerificationRelease(tag, { fetchImpl = fetch, token = '' } = {}) {
  requireTag(tag);
  const release = await readJson(fetchImpl, `${api}/releases/tags/${tag}`, token);
  if (release?.tag_name !== tag || release.immutable !== true || release.draft !== false || release.prerelease !== false) {
    throw new Error(`${tag} must be a published, stable, immutable release`);
  }
  const commit = await readJson(fetchImpl, `${api}/commits/${tag}`, token);
  if (!/^[a-f0-9]{40}$/.test(commit?.sha ?? '')) throw new Error(`Could not resolve release commit for ${tag}`);
  return { tag, commit: commit.sha };
}

export async function planMarketplaceVerification({ requestedTag = '', fetchImpl = fetch, token = '' } = {}) {
  const targets = new Map();
  if (requestedTag) {
    requireTag(requestedTag);
    // Explicit recovery can inspect a release whose old shipping workflow failed
    // on visibility. It does not assert successful shipping or mutate the provider.
    for (const provider of providers) targets.set(provider, { tag: requestedTag, shippingRun: null });
  } else {
    const runs = await readWorkflowRuns(fetchImpl,
      `${api}/actions/workflows/ship-marketplaces.yml/runs?event=workflow_dispatch&branch=main&status=success&per_page=100`, token);
    const candidates = [];
    for (const run of runs) {
      if (run.head_branch !== 'main' || run.event !== 'workflow_dispatch'
        || run.status !== 'completed' || run.conclusion !== 'success') continue;
      const match = /^Ship marketplaces (v\d+\.\d+\.\d+)$/.exec(run.display_title ?? '');
      if (!match) continue;
      requireTag(match[1]);
      if (!Number.isSafeInteger(run.id) || run.id <= 0
        || !Number.isSafeInteger(run.run_attempt) || run.run_attempt <= 0) {
        throw new Error('GitHub returned an invalid shipping run identity');
      }
      candidates.push({ run, tag: match[1] });
    }
    // An older tag rerun later must not move a provider's target backwards.
    candidates.sort((a, b) => compareTags(b.tag, a.tag) || b.run.id - a.run.id);
    for (const { run, tag } of candidates) {
      if (targets.size === providers.length) break;
      const jobs = await readJobs(run, fetchImpl, token);
      for (const provider of providers) {
        if (targets.has(provider)) continue;
        const successful = jobs.some((job) => job.status === 'completed' && job.conclusion === 'success'
          && [`ship-provider (${provider})`, `verify-provider-visible (${provider})`].includes(job.name));
        if (successful) targets.set(provider, {
          tag,
          shippingRun: `https://github.com/${repository}/actions/runs/${run.id}/attempts/${run.run_attempt}`,
        });
      }
    }
  }
  const releases = new Map();
  const include = [];
  for (const [provider, target] of targets) {
    if (!releases.has(target.tag)) {
      releases.set(target.tag, await resolveVerificationRelease(target.tag, { fetchImpl, token }));
    }
    include.push({ provider, ...releases.get(target.tag), shippingRun: target.shippingRun });
  }
  return { include, unshipped: providers.filter((provider) => !targets.has(provider)) };
}

async function main() {
  const plan = await planMarketplaceVerification({
    requestedTag: process.env.RELEASE_TAG || '',
    token: process.env.GITHUB_TOKEN || '',
  });
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT,
    `matrix=${JSON.stringify({ include: plan.include })}\nhas_targets=${plan.include.length > 0}\n`);
  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = ['## Provider verification targets', '',
      ...plan.include.map((entry) => `- ${entry.provider}: \`${entry.tag}\` at \`${entry.commit}\`${entry.shippingRun ? ` ([shipping run](${entry.shippingRun}))` : ' (manual inspection)'}`),
      ...plan.unshipped.map((provider) => `- ${provider}: no successful shipment found; visibility is unverified.`),
      '', 'This read-only workflow does not publish releases or change shipping results.', ''];
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, lines.join('\n'));
  }
  console.log(JSON.stringify(plan));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => { console.error(error.message); process.exitCode = 1; });
}

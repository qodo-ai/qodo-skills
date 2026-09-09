/** Run the current verifier against the immutable release's marketplace contract. */
import { appendFileSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyMarketplace } from './marketplace-release.mjs';
import { resolveVerificationRelease } from './plan-marketplace-verification.mjs';

export async function checkVisibility(provider, context, contract, verify = verifyMarketplace) {
  const selected = contract.providers?.find((entry) => entry.id === provider);
  if (!selected || !['claude', 'kiro'].includes(provider) || !selected.listings?.length) {
    throw new Error(`Missing verifiable marketplace contract for ${provider}`);
  }
  const target = {
    verification: selected.mode === 'provider-tracked-branch' ? 'branch-source' : 'release-commit',
    sourceRef: selected.sourceRef,
  };
  try {
    const listings = await verify(provider, context, selected);
    return { provider, ...context, ...target, state: 'provider-visible', listings };
  } catch (error) {
    return { provider, ...context, ...target, state: 'unverified', error: error.message };
  }
}

export function visibilitySummary(result) {
  const moving = result.verification === 'branch-source';
  return [
    `## ${result.provider}: ${result.state}`, '',
    `${moving ? 'Reference' : 'Expected'} release: \`${result.tag}\` at \`${result.commit}\`.`, '',
    result.error ? `Verification failed: ${result.error}` : moving
      ? `Every configured listing tracks \`${result.sourceRef}\`, observed at \`${result.listings[0].commit}\`. This verifies the moving source, not an immutable release pin.`
      : 'Every configured listing resolves to this release.', '',
    'Shipping status is independent. This workflow only reads provider state.', '',
  ].join('\n');
}

async function main() {
  const { PROVIDER, RELEASE_TAG, RELEASE_COMMIT, RELEASE_CATALOG, GITHUB_STEP_SUMMARY } = process.env;
  const context = await resolveVerificationRelease(RELEASE_TAG, { token: process.env.GITHUB_TOKEN || '' });
  if (context.commit !== RELEASE_COMMIT) throw new Error('Release commit differs from the verification plan');
  const contract = JSON.parse(readFileSync(RELEASE_CATALOG, 'utf8'));
  const result = await checkVisibility(PROVIDER, context, contract);
  if (GITHUB_STEP_SUMMARY) appendFileSync(GITHUB_STEP_SUMMARY, visibilitySummary(result));
  console.log(JSON.stringify(result));
  if (result.state !== 'provider-visible') process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => { console.error(error.message); process.exitCode = 1; });
}

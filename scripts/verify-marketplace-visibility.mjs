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
  try {
    const listings = await verify(provider, context, selected);
    return { provider, ...context, state: 'provider-visible', listings };
  } catch (error) {
    return { provider, ...context, state: 'unverified', error: error.message };
  }
}

async function main() {
  const { PROVIDER, RELEASE_TAG, RELEASE_COMMIT, RELEASE_CATALOG, GITHUB_STEP_SUMMARY } = process.env;
  const context = await resolveVerificationRelease(RELEASE_TAG, { token: process.env.GITHUB_TOKEN || '' });
  if (context.commit !== RELEASE_COMMIT) throw new Error('Release commit differs from the verification plan');
  const contract = JSON.parse(readFileSync(RELEASE_CATALOG, 'utf8'));
  const result = await checkVisibility(PROVIDER, context, contract);
  if (GITHUB_STEP_SUMMARY) appendFileSync(GITHUB_STEP_SUMMARY, [
    `## ${PROVIDER}: ${result.state}`, '',
    `Expected release: \`${context.tag}\` at \`${context.commit}\`.`, '',
    result.error ? `Verification failed: ${result.error}` : 'Every configured listing resolves to this release.', '',
    'Shipping status is independent. This workflow only reads provider state.', '',
  ].join('\n'));
  console.log(JSON.stringify(result));
  if (result.state !== 'provider-visible') process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => { console.error(error.message); process.exitCode = 1; });
}

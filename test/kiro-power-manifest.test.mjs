import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const marketplaces = JSON.parse(readFileSync(join(root, 'distribution', 'marketplaces.json'), 'utf8'));
const kiro = marketplaces.providers.find((provider) => provider.id === 'kiro');

test('the core Kiro Power uses the requested review metadata', () => {
  const listing = kiro.listings.find((entry) => entry.package === 'qodo');
  const manifest = JSON.parse(readFileSync(join(root, listing.sourcePath, 'plugin.json'), 'utf8'));

  assert.equal(manifest.name, listing.id);
  assert.equal(manifest.displayName, listing.displayName);
  assert.equal(manifest.description, listing.description);
  assert.equal(listing.displayName, 'Qodo Code Review');
  assert.equal(
    listing.description,
    'Qodo code review, code intelligence, and PR resolution workflows for your local agent.',
  );
});

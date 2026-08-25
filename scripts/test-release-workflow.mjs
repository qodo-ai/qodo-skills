/** Verify that release publication fails closed before creating mutable artifacts. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const workflow = readFileSync(join(root, '.github', 'workflows', 'release.yml'), 'utf8');

const immutabilityPreflight = workflow.indexOf('immutable-releases');
const tagCreation = workflow.indexOf('git tag -a');
const releaseCreation = workflow.indexOf('gh release create');

assert.ok(immutabilityPreflight >= 0, 'release workflow must check repository immutability');
assert.ok(tagCreation > immutabilityPreflight, 'immutability must be checked before creating a tag');
assert.ok(releaseCreation > immutabilityPreflight, 'immutability must be checked before creating a release');
assert.match(workflow, /git rev-list -n 1 \"\$\{TAG\}\"/);
assert.match(workflow, /\.assets\[\]\.name/);

console.log('Release workflow safety test passed.');

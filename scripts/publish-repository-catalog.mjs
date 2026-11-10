/** Publish one data-only prerelease snapshot without entering the marketplace release train. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPOSITORY_CATALOG_NAME, writeRepositoryCatalog } from './build-repository-catalog.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));

export function publishRepositorySnapshot({ repositoryRoot = root, sourceCommit, outputDirectory, run = (command, args) => execFileSync(command, args, { cwd: repositoryRoot, encoding: 'utf8' }) }) {
  assert.match(sourceCommit ?? '', /^[a-f0-9]{40}$/);
  assert.equal(run('git', ['rev-parse', 'HEAD']).trim(), sourceCommit, 'source must be the exact checked-out commit');
  assert.match(run('git', ['remote', 'get-url', 'origin']).trim(), /^(?:git@github\.com:|https:\/\/github\.com\/)qodo-ai\/qodo-skills(?:\.git)?$/);
  run('git', ['merge-base', '--is-ancestor', sourceCommit, 'origin/main']);
  assert.equal(run('git', ['status', '--porcelain', '--untracked-files=all']).trim(), '', 'snapshot source must be clean');
  const tag = `catalog-${sourceCommit}`;
  const tagRows = run('git', ['ls-remote', '--tags', 'origin', `refs/tags/${tag}`, `refs/tags/${tag}^{}`]).trim();
  if (tagRows) {
    const refs = new Map(tagRows.split(/\r?\n/).map((line) => line.split(/\s+/)).map(([sha, name]) => [name, sha]));
    assert.equal(refs.get(`refs/tags/${tag}^{}`) ?? refs.get(`refs/tags/${tag}`), sourceCommit, 'existing tag must name the same source');
  }
  writeRepositoryCatalog(repositoryRoot, sourceCommit, outputDirectory);
  const names = [REPOSITORY_CATALOG_NAME, `${REPOSITORY_CATALOG_NAME}.sha256`];
  const gh = (args) => run('gh', [...args, '--repo', 'qodo-ai/qodo-skills']);
  let release;
  try { release = JSON.parse(gh(['release', 'view', tag, '--json', 'isDraft,isPrerelease,assets'])); }
  catch (error) { if (!/release not found|HTTP 404/i.test(String(error.stderr ?? error.message))) throw error; }
  if (release) {
    assert.equal(release.isPrerelease, true, 'catalog snapshots must remain prereleases');
    assert.ok(release.assets.every((asset) => names.includes(asset.name)), 'refuse an unexpected snapshot asset inventory');
  } else {
    gh(['release', 'create', tag, '--target', sourceCommit, '--draft', '--prerelease', '--latest=false', '--title', `Repository catalog ${sourceCommit.slice(0, 12)}`, '--notes', `Data-only opt-in skill catalog at ${sourceCommit}. This does not publish marketplaces or alter default installation.`]);
    release = { isDraft: true, isPrerelease: true, assets: [] };
  }
  const verify = (name) => {
    const scratch = mkdtempSync(join(tmpdir(), 'qodo-catalog-download-'));
    try {
      gh(['release', 'download', tag, '--pattern', name, '--dir', scratch]);
      assert.ok(readFileSync(join(scratch, name)).equals(readFileSync(join(outputDirectory, name))), 'published snapshot bytes must be immutable');
    } finally { rmSync(scratch, { recursive: true, force: true }); }
  };
  for (const name of names) {
    if (release.assets.some((asset) => asset.name === name)) verify(name);
    else {
      assert.equal(release.isDraft, true, 'a published snapshot cannot acquire missing assets');
      gh(['release', 'upload', tag, join(outputDirectory, name)]);
      verify(name);
    }
  }
  if (release.isDraft) gh(['release', 'edit', tag, '--draft=false', '--prerelease', '--latest=false']);
  return { tag, sourceCommit, assets: names, marketplacePublication: false };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assert.equal(process.env.GITHUB_REPOSITORY, 'qodo-ai/qodo-skills');
  assert.equal(process.env.GITHUB_REF, 'refs/heads/main');
  const sourceCommit = process.env.SOURCE_COMMIT;
  const outputDirectory = process.env.CATALOG_OUTPUT_DIR;
  assert.ok(outputDirectory, 'CATALOG_OUTPUT_DIR is required');
  console.log(JSON.stringify(publishRepositorySnapshot({ sourceCommit, outputDirectory })));
}

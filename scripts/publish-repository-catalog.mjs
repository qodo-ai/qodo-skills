/** Publish one data-only prerelease snapshot without entering the marketplace release train. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPOSITORY_CATALOG_NAME, writeRepositoryCatalog } from './build-repository-catalog.mjs';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const endpoint = 'repos/qodo-ai/qodo-skills/releases';

export function runRepositoryPublisherCommand(repositoryRoot, command, args) {
  return execFileSync(command, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 65 * 1024 * 1024, timeout: 120_000 });
}

export function publishRepositorySnapshot({ repositoryRoot = root, sourceCommit, outputDirectory, run = (command, args) => runRepositoryPublisherCommand(repositoryRoot, command, args) }) {
  assert.match(sourceCommit ?? '', /^[a-f0-9]{40}$/);
  assert.equal(run('git', ['rev-parse', 'HEAD']).trim(), sourceCommit, 'source must be the exact checked-out commit');
  assert.match(run('git', ['remote', 'get-url', 'origin']).trim(), /^(?:git@github\.com:|https:\/\/github\.com\/)qodo-ai\/qodo-skills(?:\.git)?$/);
  run('git', ['merge-base', '--is-ancestor', sourceCommit, 'origin/main']);
  assert.equal(run('git', ['status', '--porcelain', '--untracked-files=all']).trim(), '', 'snapshot source must be clean');
  const tag = `catalog-${sourceCommit}`;
  const verifyTag = () => {
    const rows = run('git', ['ls-remote', '--tags', 'origin', `refs/tags/${tag}`, `refs/tags/${tag}^{}`]).trim();
    if (!rows) return false;
    const refs = new Map(rows.split(/\r?\n/).map((line) => line.split(/\s+/)).map(([sha, name]) => [name, sha]));
    assert.equal(refs.get(`refs/tags/${tag}^{}`) ?? refs.get(`refs/tags/${tag}`), sourceCommit, 'existing tag must name the same source');
    return true;
  };
  verifyTag();
  writeRepositoryCatalog(repositoryRoot, sourceCommit, outputDirectory);
  const names = [REPOSITORY_CATALOG_NAME, `${REPOSITORY_CATALOG_NAME}.sha256`];
  const api = (args) => run('gh', ['api', ...args]);
  // Release-by-tag cannot discover drafts. List (including drafts), then use numeric IDs.
  const matches = JSON.parse(api(['--paginate', '--slurp', `${endpoint}?per_page=100`])).flat().filter((item) => item.tag_name === tag);
  assert.ok(matches.length <= 1, 'multiple releases claim this catalog source');
  let release = matches[0] ?? JSON.parse(api(['--method', 'POST', endpoint, '-f', `tag_name=${tag}`, '-f', `target_commitish=${sourceCommit}`, '-F', 'draft=true', '-F', 'prerelease=true', '-f', 'make_latest=false', '-f', `name=Repository catalog ${sourceCommit.slice(0, 12)}`, '-f', `body=Data-only opt-in skill catalog at ${sourceCommit}. This does not publish marketplaces or alter default installation.`]));
  assert.ok(Number.isSafeInteger(release.id) && release.id > 0, 'release must have a numeric ID');
  const releaseEndpoint = `${endpoint}/${release.id}`;
  const refresh = () => { release = JSON.parse(api([releaseEndpoint])); };
  const validate = () => {
    assert.equal(release.tag_name, tag);
    assert.equal(release.prerelease, true, 'catalog snapshots must remain prereleases');
    assert.equal(release.target_commitish, sourceCommit, 'release must target the exact source');
    assert.ok(release.assets.every((asset) => names.includes(asset.name)), 'refuse an unexpected snapshot asset inventory');
    if (!release.draft) assert.equal(release.immutable, true, 'published catalog must be immutable before consumer rollout');
  };
  const verify = (name) => {
    const asset = release.assets.find((item) => item.name === name);
    assert.ok(asset && Number.isSafeInteger(asset.id) && asset.id > 0, 'release asset must have a numeric ID');
    const bytes = api(['-H', 'Accept: application/octet-stream', `${endpoint}/assets/${asset.id}`]);
    assert.ok(Buffer.from(bytes).equals(readFileSync(join(outputDirectory, name))), 'published snapshot bytes must be immutable');
  };
  validate();
  // Reserve the exact source atomically before publication can lock the tag.
  // A competing creator is acceptable only if it reserved the same commit.
  if (!verifyTag()) {
    try { api(['--method', 'POST', 'repos/qodo-ai/qodo-skills/git/refs', '-f', `ref=refs/tags/${tag}`, '-f', `sha=${sourceCommit}`]); }
    catch (error) { if (!verifyTag()) throw error; }
    assert.equal(verifyTag(), true, 'catalog tag must be reserved before publishing');
  }
  for (const name of names) {
    refresh(); validate();
    if (!release.assets.some((asset) => asset.name === name)) {
      assert.equal(release.draft, true, 'a published snapshot cannot acquire missing assets');
      const upload = new URL(release.upload_url.replace(/\{.*$/, ''));
      assert.equal(upload.origin, 'https://uploads.github.com');
      assert.equal(upload.pathname, `/${releaseEndpoint}/assets`);
      upload.searchParams.set('name', name);
      api(['--method', 'POST', '-H', 'Content-Type: application/octet-stream', '--input', join(outputDirectory, name), upload.toString()]);
      refresh(); validate();
    }
    verify(name);
  }
  verifyTag();
  if (release.draft) {
    release = JSON.parse(api(['--method', 'PATCH', releaseEndpoint, '-F', 'draft=false', '-f', 'make_latest=false']));
    if (release.immutable !== true) {
      try { api(['--method', 'PATCH', releaseEndpoint, '-F', 'draft=true']); }
      catch { throw new Error('CRITICAL: published catalog is mutable and could not return to draft; stop consumer rollout'); }
      throw new Error('Published catalog is mutable; enable release immutability before consumer rollout');
    }
  }
  refresh(); validate();
  assert.equal(release.draft, false);
  assert.equal(verifyTag(), true, 'published catalog tag must resolve to the source');
  for (const name of names) verify(name);
  return { tag, sourceCommit, assets: names, marketplacePublication: false };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assert.equal(process.env.GITHUB_REPOSITORY, 'qodo-ai/qodo-skills');
  assert.equal(process.env.GITHUB_REF, 'refs/heads/main');
  const sourceCommit = process.env.SOURCE_COMMIT;
  const outputDirectory = process.env.CATALOG_OUTPUT_DIR;
  const repositoryRoot = process.env.SOURCE_ROOT;
  assert.ok(outputDirectory && repositoryRoot, 'CATALOG_OUTPUT_DIR and SOURCE_ROOT are required');
  console.log(JSON.stringify(publishRepositorySnapshot({ repositoryRoot, sourceCommit, outputDirectory })));
}

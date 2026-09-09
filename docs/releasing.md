# Releasing Qodo skills

Start with the [Actions guide](../.github/workflows/README.md) to find the right workflow.

## 1. Merge source changes, then review one release PR

Contributors edit canonical files under `skills/` and catalog display metadata, open a normal PR,
wait for checks, and merge. Existing versions and generated files stay unchanged. No local commands,
Node installation, or Conventional Commit format are required. New skills need a canonical file,
catalog entry with an initial version, and the existing skill-specific validation coverage.

**CI: Validate distribution** generates an ephemeral release preview for source PRs and main pushes,
then runs the full validation matrix. It rejects edits to generated files, mismatched source versions,
unsupported removals, missing catalog entries, and incomplete release data. A prepared release PR
is checked directly without regenerating away mistakes in its committed artifacts.

After successful main-push validation, **Release: Prepare PR** maintains one PR from
`automation/skills-release`. It follows the Release Please pattern using this repository's existing
Node generator; it does not require the stock Release Please action or another version manifest.
The baseline is the first-parent commit that added the current immutable release record. All source
changes since that snapshot are accumulated: existing changed skills get one patch bump, new skills
use `initial` and a package minor, and packaging-only changes get a package patch. Reverted changes
drop out; if none remain, the bot closes its release PR. Source changes to artifact builders are
included even when skill bodies did not change.

The bot only executes code already merged to main, checks that main still matches the validated run,
and uses an explicit lease on its fixed branch. It never commits to contributor branches. Repeated
runs preserve the same proposed version and do not push an identical tree on the same base. If an
unrecognized branch already occupies that name, it stops for inspection. **Prepare skills release
PR** also offers a main-only manual rerun. If initial branch publication succeeded but PR creation
failed, inspect and delete the orphan branch in GitHub, then rerun the action.

A release owner selects **Approve workflows to run** if shown in the release PR merge box, waits
for the current checks, reviews the generated packages and release record, and merges. GitHub's
repository-token PR events require this approval; see [the trigger documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
The repository must permit Actions to create pull requests. No extra App credentials are needed for
release-PR preparation. Updates to the bot PR are regenerated; source edits belong in ordinary PRs.

Kiro reads `main/kiro-power` and `main/kiro-power-standards`. Only the release PR updates these generated
snapshots. Canonical `skills/` on main can contain unreleased changes. Consumers that intentionally
read canonical main directly see those source changes earlier.

For explicit minor/major releases or recovery, a maintainer can still prepare a complete release PR:

```sh
npm run release:prepare -- --summary "Explain the compatibility change" --skill qodo-review=minor
npm test
```

Do not merge competing prepared releases. Close the bot PR before coordinating a manual release;
automation resumes from its release record after merge. Removal remains unsupported until an
immutable removal record is designed. Operational publisher and validator changes can advance
independently when they do not change installed packages. `marketplace-release.mjs` builds provider
packets and is versioned: its fixes enter the next release, since shipping executes the selected tag.

## 2. Publish an immutable GitHub release

The repository administrator must enable GitHub release immutability before the first release.
Do not place an administrator PAT or a shared QAR release credential in this public repository.
The normal release workflow uses its scoped `GITHUB_TOKEN` for publication. Pre-publication
immutability verification uses a dedicated `qodo-skills-release-bot` GitHub App
with only `Administration: read`, `Contents: write`, and `Metadata: read`; the protected
`skills-release` environment stores its numeric App id as
`QODO_SKILLS_RELEASE_APP_ID` and its private key as
`QODO_SKILLS_RELEASE_APP_PRIVATE_KEY`. The workflow mints a short-lived token restricted to
`qodo-ai/qodo-skills` only after environment approval. The release workflow uses the same
`skills-release` gate to mint an Administration-read token and verify immutability before it
creates a tag or draft; publication still uses the normal scoped workflow token.

Before the first release and after any protection change, a repository administrator must run:

```sh
GITHUB_REPOSITORY=qodo-ai/qodo-skills scripts/audit-release-protections.sh
```

The audit uses the administrator's existing `gh` session to verify otherwise hidden bypass actors,
the dedicated App identity and permissions, one active selected-repository installation, presence of
an environment reviewer, release immutability, and exact ruleset shapes. The protected release workflow mints an installation-wide token narrowed to read-only Administration and
require its complete repository list to be exactly `qodo-ai/qodo-skills`; GitHub exposes that list
only to an App installation token, not to the administrator's normal OAuth/PAT session. The token is
revoked by the action after the job. No administrator credential is stored in Actions.
Kiro reads `main`; marketplace shipping does not mint an App write token or promote a separate
branch. The `skills-release` environment gates immutable publication and holds its App credentials;
`marketplace-kiro` gates Kiro's provider handoff. Configure `skills-release` with required reviewers,
protected-branch restrictions, and both App settings before using the release workflow. Keep the
existing `marketplace-kiro` environment for provider handoffs and its credentials while older release
runs still reference it. Neither environment selects Kiro's source branch. The unused legacy
branch and its ruleset do not need to be deleted or changed for this transition.
Keep exactly one active, no-exclusion, no-bypass **Immutable release tags** ruleset on
`refs/tags/v*`; it permits creation but blocks every tag update and deletion. The preflight
paginates the complete repository ruleset collection before resolving that exact ruleset and
explicitly rejects a `creation` restriction. GitHub requires `Administration: read` for the
immutable-release settings endpoint, so the workflow mints a short-lived, repository-scoped App
token for that pre-publication check. The checked-in audit, runtime preflight, and publication programs are covered behaviorally:
missing credentials, disabled immutability, duplicate/invalid rulesets, forbidden creation rules,
draft corruption, draft resume, publication, and immutable retry all fail closed.
Merging a release record onto main starts **Release: Publish skills** automatically. The existing
`skills-release` approval and runtime compatibility preflight still apply; a missing compatible CLI
release blocks publication. Rerun the captured release run after resolving a transient failure.
Manual dispatch remains available for a fully prepared main snapshot or reviewed draft recovery.
Ordinary source merges do not start publication. The workflow:

1. captures the release commit and verifies it remains an ancestor of main before publication;
   subsequent source merges do not change the validated SHA or enter that release;
2. installs the lockfile-pinned validation dependencies and validates the release package;
3. uses the protected release App to verify repository immutability, then requires the exact
   protected-tag ruleset before creating any tag or release;
4. creates annotated tag `v<package-version>`, pushes it without force, and verifies the protected
   remote tag peels to the validated SHA immediately before publication;
5. materializes the resolved release commit as a clean detached worktree and, before the
   publication token is exposed, runs that tree's enterprise, release-index, and release-note
   builders; the generated schema-v2 index records the exact resolved commit. Publication uses only
   those prepared outputs plus that tree's CLI-managed bundle, requires the index commit and package
   version to match the release, and requires the draft title and body to match exactly;
6. publishes the verified draft, which makes the release immutable;
7. verifies the published release is immutable, the protected tag is unchanged, and all published
   assets still match the validated checkout byte-for-byte;
8. on an idempotent rerun, downloads all eight existing assets, verifies their checksums, and compares
   them byte-for-byte with the validated checkout before reporting success.

GitHub's release-by-tag REST endpoint does not expose draft releases. The publisher therefore finds
both drafts and public releases through the paginated release list, rejects duplicate tag claims,
and addresses the selected release by immutable numeric id. If reviewed release automation advances
`main` after a draft was created, recovery may use the older tagged commit only when that tag is an
ancestor of current `main` and an existing draft for the tag is present. Recovery checks out that
exact tagged commit into a separate clean worktree; both enterprise packaging and every potentially
missing release input are read from it, never from current `main`. The publisher revalidates the
source worktree, draft title, and draft body immediately before mutation, and every downloaded draft
asset must match before the draft can become public. Draft uploads and downloads use the numeric
release and asset REST endpoints because GitHub's tag-oriented CLI cannot resolve drafts. An older
tag without its draft fails closed; tags and assets are never moved, deleted, or overwritten.

After that workflow succeeds, `qodo-ai/qodo-in-cli`'s hourly **release: publish skills compatibility
channel** watcher selects the newest immutable release. The workflow verifies the public
release again, publishes the compact index and CLI-managed bundle under tag-scoped paths in the
canary bucket, and then waits at the existing protected production environment before copying the
same bytes to `get.qodo.ai`. It updates only these same-origin `version.json` fields:

- `skills.releaseTag`
- `skills.releaseIndex` and `skills.releaseIndexChecksum`
- `skills.cliManagedBundle` and `skills.cliManagedChecksum`

Do not promote marketplaces until the production pointers resolve to the selected tag and both
checksums verify. CLI releases preserve the `skills` object while changing their separate
`channels` entry.

The protected production approval remains mandatory. For recovery, a release owner may manually
dispatch the same workflow with an exact immutable tag; the watcher becomes a no-op once production
advertises that tag and rejects rollback to an older release.

The index is metadata for stale-version notices. The CLI-managed bundle keeps only proven roots
from earlier Qodo CLI releases current; it is never a new-install source. The enterprise archive contains the complete
Claude, Codex, Kiro, and portable package projections with `enterprise-bundle` provenance; core is
default and Standards remains optional. Neither artifact grants write authority or contains the
Qodo CLI.

GitHub drafts are mutable by trusted repository release writers until publication. The protected
tag prevents commit drift; the second post-publication download detects any draft-asset race before
marketplace promotion. A mismatch burns that version and requires incident handling plus a new
patch release; it is never accepted as a successful release.

## 3. Ship selected marketplaces

Once the protected compatibility pointer advertises the immutable tag, the hourly
**Marketplaces: Start shipping** watcher dispatches **Marketplaces: Ship release** once with `all`. The action
validates the tag/version, downloads the advertised compatibility index and bundle, verifies their
checksums and release identity, and byte-compares all four files with the immutable GitHub release
assets before regenerating the exact provider packet. It rejects a tag below the highest successful
default-branch marketplace run. The watcher serializes automatic launches and rechecks immediately
before dispatch; a simultaneous manual launch is safely arbitrated by the downstream atomic release
lock rather than Actions' lossy pending-run concurrency. If any default-branch workflow run already exists for the tag,
automatic dispatch does not loop; use the manual `claude`, `codex`, `kiro`, or `all` selector for a
deliberate retry or partial recovery.

Only one release tag may be active across providers. Same-tag retries are grouped idempotently; any
attempt atomically advances `refs/heads/qodo-marketplace-release-lock` to an owner commit before
preparation and holds it through provider approval. Every acquire/release is an append-only,
non-force fast-forward from the exact commit observed, so concurrent stale-owner recovery or cleanup
cannot remove a replacement lock. An active owner blocks every other tag; after cancellation or
runner loss, the next dispatch may advance the chain only when the Actions API reports the owner run
completed. This avoids GitHub's lossy single-pending concurrency slot and cannot admit simultaneous
cross-tag releases.

| Provider | Automation | Completion evidence |
|---|---|---|
| Claude Code | packet generation and protected handoff; separate scheduled catalog verification | both selected listings expose the released commit/path |
| Codex | exact portal packet with deterministic per-listing ZIPs, SHA-256 checksums, and protected release-owner gate | portal review/publish completed, then protected environment approved |
| Kiro | packet generation and protected handoff; separate scheduled directory verification | selected Powers use `main` and the configured paths; record its observed commit |

The action prepares every selected packet first. Claude and Kiro shipping jobs then wait in
`marketplace-claude` and `marketplace-kiro` for the release owner's handoff approval.
Kiro's generated source changes with release PR merges to `main`; shipping does not advance a separate branch.
New Kiro shipments require a release with the main-source contract (v2.0.4 onward); an older
contract is rejected before preparation rather than silently skipping its required promotion.
These jobs finish with **awaiting provider verification**; public catalog propagation does not fail
shipping or hold its release lock. Preparation and protection-check errors still fail shipping.
Codex stays human-gated because its documented flow requires portal
submission, review, and explicit publication. Its `marketplace-codex` approval is an attestation
after provider publication, not a substitute for it. All three environments require reviewers.

**Marketplaces: Verify listings** is a separate read-only workflow. It runs after successful
shipping, every 15 minutes, and on manual dispatch. Its default target is the highest successfully
shipped tag **per provider**, using the selected provider's successful job in that shipping attempt.
A Codex-only run cannot advance the Claude/Kiro target; rerunning an older tag cannot move it back.
Without successful shipping evidence, the provider is reported as unverified and is not checked.
The observer does not approve environments, acquire shipping locks, promote branches, or publish.

Each check validates release immutability and resolves its exact commit. The current trusted
verifier reads the marketplace contract from that commit, so later code fixes work without
silently changing the release's expected paths or branch. Under the moving-source Kiro contract,
it verifies `main` and records the current source commit; it does not require `main` to stay at
the reference release SHA. Older immutable contracts retain their original exact-pin checks.
Claude and Kiro run independently;
wrong/missing listings, stale pins, branch mismatches, and request failures fail the observer.
Its job summaries retain the expected tag/SHA and the mismatch. A green shipping run means our
shipping steps completed; provider acceptance requires a green visibility check as well.

For an already published release whose old shipping run failed on visibility, inspect it without
repeating promotion or approval:

```sh
gh workflow run verify-marketplace-visibility.yml --ref main -f release_tag=v2.0.2
```

An explicit tag is a manual inspection, not evidence of successful shipping. Leave it empty for
normal tracking. Both workflows must be merged onto the default branch for their new behavior;
rerunning an old shipping run continues to use its original workflow definition.

Anthropic's official catalog already tracks both `qodo` and `qodo-standards` in
[`releases-only`](https://github.com/anthropics/claude-plugins-official/blob/517b2fcd1b60fa2181ac52dcf8492361ba341180/.github/bump-tracking.json).
Its daily [SHA updater](https://github.com/anthropics/claude-plugins-official/blob/517b2fcd1b60fa2181ac52dcf8492361ba341180/.github/workflows/bump-plugin-shas.yml)
opens update PRs; checks and upstream merge still determine when listings become visible.
The observer verifies the resulting catalog rather than assuming a schedule or PR proves publication.

For Codex, upload the archive named by each `submissions/<listing>.json` record and verify it against
`release.json`, its submission record, and `bundles/SHA256SUMS` by running
`node verify-codex-packet.mjs` from the packet root. The verifier is included in the packet, uses
only Node built-ins, and rejects inconsistent metadata, hashes, sizes, missing/extra archives,
invalid starter prompts, missing branding, and submission/manifest interface drift. It also checks
local headers, CRCs, the full central directory and end record against the same deterministic ZIP
inventory, so extractor-visible names cannot bypass manifest checks. The ZIP
contains only the native `.codex-plugin/plugin.json`, without a wrapper or generic root manifest.
The latter remains in the source projections for non-portal consumers.

Enterprise schema v1 is a separate consumer contract: current QAR rejects unrecognized
projection files and Codex interface fields. The enterprise builder omits Codex directory artwork
and references. It also omits Kiro's banner, README image block, and directory-only `displayName`.
It preserves all skills, native manifests, starter prompts and provenance. Public marketplace
packages retain their artwork and display metadata. Do not extend the enterprise schema's
allowlist implicitly with a marketplace change.

Codex listing presentation is configured in `distribution/codex-submissions.json`:
`starterSkills` explicitly selects at most three installed skills, whose prompts remain authored
once in the catalog. It does not change installed skill membership. `shortDescription` is limited
to 30 characters. Branding is vendored under `distribution/assets/codex/`. Run `npm run adapters`
after changes; merged packaging fixes are collected in the next release PR.
Do not edit a published ZIP or replace an immutable release.

For the ownership cutover, submit `qodo` as an initial company-owned listing using **Business — Qodo**
in the company organization. The earlier listing was personally owned; its removal was requested,
not confirmed. Do not assume its installed users migrate automatically. Once the company listing
is live, change its release type to `update` for subsequent releases of that same record.
`qodo-standards` remains a separate optional listing.

The portal may warn about `metadata` in SKILL.md. Preserve Qodo's provenance/version fields:
they are not UI configuration. Each skill already ships its generated `agents/openai.yaml`
interface. Every package contains only its catalog's canonical skill names. Portal acceptance and review
are still required; local checks do not guarantee approval. The
[OpenAI submission errors reference](https://developers.openai.com/plugins/deploy/submission-errors)
(checked: 2026-09-05) is the contract behind these checks.

Kiro's provider listings use `main/kiro-power` for core and `main/kiro-power-standards` for
optional Standards. `directory-entries.json` carries those source URLs, paths, branches and
package descriptions. The existing core listing already uses `main`; adding the separate
`qodo-standards` directory entry still requires provider acceptance.

Kiro follows a moving branch. Merged source changes can therefore become available independently
of immutable GitHub releases or marketplace handoff approval. The observer validates the full
repository/path/branch/clone-URL records, resolves `main`, and reports its observed commit. It does
not claim the source matches the packet's reference release. The verifier reads JSON documents
and Next.js Flight data embedded in directory HTML without executing provider scripts. A missing
listing or incorrect source still fails verification. No branch promotion, App write token, or
legacy Kiro branch ruleset is required by marketplace shipping. Immutable release publication
keeps its separate App audit, protected approval, and no-bypass tag protections.

Core listing identity remains `qodo`; Qodo Standards remains the separately installable
`qodo-standards` listing. **Marketplaces: Ship release** selects providers, not individual listings, and
ships every configured listing for each selected provider together. Optionality is an installation
choice, not a separate release selector. Never replace the core listing during a source migration.

## 4. Provider acceptance

For every selected provider, record:

1. provider-visible source path and observed commit/version; distinguish moving Kiro `main` from a release pin;
2. fresh core install with exactly four canonical skill entries;
3. upgrade from the currently published version without duplicates;
4. Qodo Standards absent until explicitly installed;
5. `qodo-setup`, one read workflow, and one approval-gated write workflow;
6. host-owned update and new-session activation.

Source CI or packet creation alone is not release completion.

## 5. skills.sh channel

No publication API is required: skills.sh installs from this repository. After the immutable tag
is validated and **before any provider promotion**, smoke-test a core install and update on
representative non-marketplace agents, including multi-agent and project/global scope. Use explicit
`--skill` selection so the optional package cannot appear by accident.

## 6. QAR enterprise channel

When adopting v2.0.0, update QAR's reviewed `infra/skills-bundle/topology.json` together with
`infra/skills-bundle/bundle.lock.json`. Remove `qodo-pr-resolver` from the core Claude, Codex, and
Kiro `projectionSkills`; portable already uses canonical names. QAR requires an exact topology
match, so its current v1.1.0 topology rejects the new bundle. Update the pin only after the new
immutable assets are published and verified; changing topology alone breaks the existing pin.

Every immutable skills release carries `qodo-enterprise-manifest.json`, the deterministic
`qodo-enterprise-bundle-v<version>.tar.gz`, separate core/Standards Agent Skills Discovery v0.2
indexes, and one digest-pinned archive per skill. The manifest carries the package's
`minimumCliVersion`; QAR must reject the bundle when its independent CLI lock is older. QAR pins that release independently from
its CLI pin, verifies every byte while building the backend image, and serves it from the existing
`/toolbox` origin. The hourly **distribution bundles: sync promoted CLI + skills pins** workflow,
delivered by `qodo-agent-runtime#594`,
reads the protected public CLI pointer and the newest immutable GitHub skills release. It updates
the CLI lock first, validates the skills minimum against that selected runtime, builds and tests
both bundles, and opens or refreshes one reviewed dependency PR. The separate CLI-only and
skills-only workflows remain manual recovery controls. Until that QAR change is merged, the manual
pin workflows remain the authoritative path.

The discovery section has its own runtime minimum. QAR enforces the greater of the package-wide
minimum and the discovery minimum, so compatibility assets can retain their older floor without
allowing a discovery-capable bundle to pair with an incapable CLI.

The archive and discovery feeds are enterprise distribution inputs, not hidden CLI payloads. After
authentication, the QAR-supplied CLI launches its build-pinned skills engine against the same-origin
core feed; Standards uses a separate feed and remains explicit. The CLI embeds no skill body,
agent registry, or archive installer. It forces `DO_NOT_TRACK=1`, and client runtime needs no public
registry or package-manager access.

The CLI reads QAR's same-origin compact index, CLI-managed bundle, and enterprise pointer. The
compatibility updater still touches only proven historical CLI-managed roots. The enterprise
checker never mutates roots in the background or falls back to a public origin. It emits
`qodo agents update --enterprise`; the user then reviews the lifecycle engine's overwrite summary
and confirms the update.

Gate: deterministic rebuild, manifest/archive/discovery digests, no credential or CLI bytes, core
and Standards isolation, QAR same-origin download, private-origin no-egress behavior,
telemetry-disabled pinned-helper use at Node 20.6, clean-machine delegated import, prompted update,
retry, and a new agent session.

## Rollback

- Skill regression: prepare and publish a new patch restoring the last-good behavior, then ship
  that patch through the affected lifecycle owners.
- Provider packaging regression: publish a new immutable patch containing the last-good packaging,
  then promote that patch through the provider's supported reviewed update flow. For Kiro, restore
  the last-good source through an ordinary reviewed revert on `main`; do not rewrite history.
- Runtime regression: use the independent Qodo CLI rollback; do not smuggle a binary change into a
  skill release.

Never mutate a published tag, release asset, or provider cache in place.

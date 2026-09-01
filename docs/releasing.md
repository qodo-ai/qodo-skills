# Releasing Qodo skills

## 1. Prepare one atomic pull request

Edit only canonical files under `skills/` and catalog metadata, then run:

```sh
npm run release:prepare -- \
  --summary "Improve local review guidance" \
  --skill qodo-review=patch
npm test
```

`release:prepare` increments the affected skill and package versions, regenerates Claude, Codex,
Kiro, and release-index artifacts, and writes `releases/v<version>.json`. CI rejects a changed
workflow without a version bump, generated drift, a thin loader, package leakage, or an incomplete
release record.

The pull request must state:

- user-visible behavior and compatibility impact;
- canonical skills and packages changed;
- native hosts actually tested;
- any provider acceptance still pending.

## 2. Publish an immutable GitHub release

The repository administrator must enable GitHub release immutability before the first release.
Do not place an administrator PAT or a shared QAR release credential in this public repository.
The normal release workflow uses its scoped `GITHUB_TOKEN` for publication. Pre-publication
immutability verification and Kiro promotion use a dedicated `qodo-skills-release-bot` GitHub App
with only `Administration: read`, `Contents: write`, and `Metadata: read`; the protected
`marketplace-kiro` environment stores its numeric App id as
`QODO_SKILLS_RELEASE_APP_ID` and its private key as
`QODO_SKILLS_RELEASE_APP_PRIVATE_KEY`. The workflow mints a short-lived token restricted to
`qodo-ai/qodo-skills` only after environment approval. The release workflow uses the same
`marketplace-kiro` gate to mint an Administration-read token and verify immutability before it
creates a tag or draft; publication still uses the normal scoped workflow token.

Before the first release and after any protection change, a repository administrator must run:

```sh
GITHUB_REPOSITORY=qodo-ai/qodo-skills scripts/audit-release-protections.sh
```

The audit uses the administrator's existing `gh` session to verify otherwise hidden bypass actors,
the dedicated App identity, permissions, and active installation on this repository, presence of an environment reviewer, release
immutability, and exact ruleset shapes. No administrator credential is stored in Actions.
Protect creation, update, deletion, and force-push on `refs/heads/marketplace-kiro`, with the release
App as the sole always-bypass actor. This prevents another repository writer from claiming the
provider-visible branch before the first promotion while still allowing the approved release job to
create it.
Keep exactly one active, no-exclusion, no-bypass **Immutable release tags** ruleset on
`refs/tags/v*`; it permits creation but blocks every tag update and deletion. The preflight
paginates the complete repository ruleset collection before resolving that exact ruleset and
explicitly rejects a `creation` restriction. GitHub requires `Administration: read` for the
immutable-release settings endpoint, so the workflow mints a short-lived, repository-scoped App
token for that pre-publication check. The checked-in audit, runtime preflight, and publication programs are covered behaviorally:
missing credentials, disabled immutability, duplicate/invalid rulesets, forbidden creation rules,
draft corruption, draft resume, publication, and immutable retry all fail closed.
After the compatible CLI release is live and the skills PR is merged, a release owner dispatches
**Release skills** from the current `main` head. Rerunning it is idempotent. The workflow:

1. requires the dispatched SHA to be the exact `main` head before and after validation; a merge
   after that final check does not change the validated release SHA;
2. installs the lockfile-pinned validation dependencies and validates the release package;
3. uses the protected release App to verify repository immutability, then requires the exact
   protected-tag ruleset before creating any tag or release;
4. creates annotated tag `v<package-version>`, pushes it without force, and verifies the protected
   remote tag peels to the validated SHA immediately before publication;
5. builds the deterministic enterprise archive, then creates or resumes a draft release containing
   the compact index, data-only CLI-managed bundle, enterprise manifest, enterprise archive, and
   all four SHA-256 files;
6. publishes the verified draft, which makes the release immutable;
7. verifies the published release is immutable, the protected tag is unchanged, and both published
   assets still match the validated checkout byte-for-byte;
8. on an idempotent rerun, downloads both existing assets, verifies their checksum, and compares
   them byte-for-byte with the validated checkout before reporting success.

After that workflow succeeds, dispatch **release: publish skills compatibility channel** in
`qodo-ai/qodo-in-cli` with the immutable `v<package-version>` tag. The workflow verifies the public
release again, publishes the compact index and CLI-managed bundle under tag-scoped paths in the
canary bucket, and then waits at the existing protected production environment before copying the
same bytes to `get.qodo.ai`. It updates only these same-origin `version.json` fields:

- `skills.releaseTag`
- `skills.releaseIndex` and `skills.releaseIndexChecksum`
- `skills.cliManagedBundle` and `skills.cliManagedChecksum`

Do not promote marketplaces until the production pointers resolve to the selected tag and both
checksums verify. CLI releases preserve the `skills` object while changing their separate
`channels` entry.

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

Run **Ship marketplaces** with the immutable tag and any combination of `claude`, `codex`, `kiro`,
or `all`. The action validates the tag/version, regenerates the exact provider packet, and uploads
one artifact per selected provider.

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
| Claude Code | packet generation, protected submission pause, then official catalog verification | both selected listings expose the released commit/path |
| Codex | exact portal packet plus protected release-owner gate | portal review/publish completed, then protected environment approved |
| Kiro | packet generation, protected release-branch promotion, then live directory verification | selected Powers expose `marketplace-kiro` at the released commit and paths |

The action prepares every selected packet first. Claude and Kiro verification jobs then wait in
`marketplace-claude` and `marketplace-kiro` so a release owner can complete any provider submission
without starting a second workflow; after approval, the job verifies the live listing and fails if
it is not the selected release. Codex stays human-gated because its documented flow requires portal
submission, review, and explicit publication. Its `marketplace-codex` approval is an attestation
after provider publication, not a substitute for it. All three environments require reviewers.

Kiro's provider listing must point to `marketplace-kiro`, not `main`. After protected-environment
approval, the workflow advances that protected branch without force to the immutable release SHA
using a freshly minted, repository-scoped `qodo-skills-release-bot` installation token, then
requires the live directory and branch head to match exactly.
Before any branch mutation, a checked-in preflight requires exactly one active **Kiro marketplace
release** branch ruleset with update/deletion/force-push protection, no exclusions, and exactly one
always-bypass release identity. The bypass must be the dedicated App's `Integration` actor, while
any branch pattern broader than the Kiro source is rejected. The environment must require at least
one release reviewer. Admin bypass, self-review prevention, and deployment-branch filtering are not
initial-cutover gates; this accepted posture is weaker than enforcing independent approval and may
be hardened later without changing the token architecture. The runtime preflight checks all
settings visible to the short-lived App token; the administrator audit is the authority for hidden
bypass configuration.

Core listing identity remains `qodo`; Qodo Standards remains the separately installable
`qodo-standards` listing. **Ship marketplaces** selects providers, not individual listings, and
ships every configured listing for each selected provider together. Optionality is an installation
choice, not a separate release selector. Never replace the core listing during a source migration.

## 4. Provider acceptance

For every selected provider, record:

1. provider-visible exact commit/path and version;
2. fresh core install with four canonical capabilities plus the expected `qodo-pr-resolver`
   compatibility alias (five installed skill entries total);
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

Every immutable skills release carries `qodo-enterprise-manifest.json` plus the deterministic
`qodo-enterprise-bundle-v<version>.tar.gz` and checksums. The manifest carries the package's
`minimumCliVersion`; QAR must reject the bundle when its independent CLI lock is older. QAR pins that release independently from
its CLI pin, verifies every byte while building the backend image, and serves it from the existing
`/toolbox` origin. Its separate dependency workflow opens the reviewed skills-pin PR.

The archive is an enterprise distribution input, not a hidden CLI payload. A customer deployment
imports the host-specific package or portable local source through its approved plugin rollout.
The manifest requires `DO_NOT_TRACK=1` whenever that rollout invokes the skills CLI; direct host
imports need no skills CLI at all.
The CLI reads QAR's same-origin compact index and CLI-managed bundle. It never copies enterprise
archive contents into an agent root; only roots already proven to be CLI-managed are refreshed.

Gate: deterministic rebuild, manifest/archive/index checksums, no credential or CLI bytes, core and
Standards isolation, QAR same-origin download, private-origin no-egress behavior, telemetry-disabled
skills-CLI use when applicable, and a customer
plugin update followed by a new agent session.

## Rollback

- Skill regression: prepare and publish a new patch restoring the last-good behavior, then ship
  that patch through the affected lifecycle owners.
- Provider packaging regression: publish a new immutable patch containing the last-good packaging,
  then promote that patch through the provider's supported reviewed update flow. This forward-only
  rule is mandatory for Kiro because its protected release branch cannot be rewound.
- Runtime regression: use the independent Qodo CLI rollback; do not smuggle a binary change into a
  skill release.

Never mutate a published tag, release asset, or provider cache in place.

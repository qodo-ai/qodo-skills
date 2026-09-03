# Qodo marketplace cutover and release strategy

## Outcome

Qodo moves skill ownership out of the CLI without creating a second architecture:

> Qodo authors skills once; every installed root has one lifecycle owner. Marketplaces, skills.sh,
> or the enterprise bundle update skills; the CLI-managed channel updates only roots created by
> earlier Qodo CLI releases; the CLI updates the runtime.

- Claude Code, Codex, and Kiro receive complete generated skills through their official listings.
- Compatible agents without a Qodo listing use the skills.sh lifecycle through Qodo's pinned,
  embedded upstream engine: the CLI performs the selected, consented install and verifies the
  resulting receipt and bytes. No separate npm or `npx` step is left to the user.
- On-prem QAR deployments pin the independently released CLI and skills assets. QAR exposes
  path-scoped Agent Skills Discovery v0.2 feeds for core and Standards. After login, the CLI invokes
  a build-pinned, telemetry-disabled skills lifecycle engine; that engine owns agent discovery and
  installation while the enterprise bundle remains the content lifecycle owner.
- `qodo-standards` remains a separate optional package everywhere.
- Existing users who keep the copies originally installed by the CLI continue receiving current
  skills automatically; marketplace migration is optional, not a support deadline.
- The CLI authenticates and runs tools, updates itself, prints lifecycle guidance, emits stale-skill
  notices, and maintains only hash-exact CLI-managed copies through a separate compatibility channel.
- No task-time playbook loader or Qodo-authored agent-path copier ships in the cutover. Public and
  enterprise commands are authenticated launchers for a build-pinned skills lifecycle engine; the
  CLI owns orchestration, consent, immutable-source verification, and rollback, while the upstream
  engine owns agent mappings and target materialization.

## Why this design

The alternative—thin provider skills that load current workflows from the CLI—was tested in a
blinded behavioral A/B on Codex and Claude. Task quality was within the parity threshold, but the
design failed absolute gates:

| Host | Quality delta | Loader ordering | Median latency | Decision |
|---|---:|---:|---:|---|
| Codex | +0.885 pp | 25/33 | +16.709% | Fail |
| Claude | -0.760 pp | 34/35 | +17.448% | Fail |

Codex also exposed unsafe resilience/authority behavior in loaded cases. Embedded skills remove
the extra ordering, latency, cache, and authority-widening boundary while retaining the canonical
source/generation model.

## Release topology

```text
skills/<name>/ (authored once)
          │
          ├── packages/             Claude Code complete skills
          ├── codex-packages/       Codex complete skills
          ├── kiro-power*/          Kiro Agent Plugins power packages
          ├── skills/               skills.sh source
          ├── enterprise archive    offline projections and compatibility artifact
          ├── discovery feeds       core + optional Standards, one digest-pinned archive per skill
          └── CLI-managed bundle    current bytes for proven earlier CLI-managed roots

qodo CLI ── login + runtime + tool help + version notice + pinned skills launcher
        ├── public: selected install/update through the pinned engine; never mutates unattended
        ├── compatibility: updates only roots carrying CLI-managed ownership proof
        └── enterprise: delegates same-origin feed installation after authentication and consent

QAR /toolbox ── independently pinned CLI + enterprise skills assets
             └── path-scoped v0.2 feeds and digest-pinned archives; no runtime public egress
```

## Automated release train

The repositories pull verified state from the lifecycle owner immediately upstream; no
cross-repository administrator token is stored in the public skills repository.

```text
immutable qodo-skills release
        ├── hourly qodo-in-cli compatibility canary
        │       ↓ protected production approval
        │   get.qodo.ai skills pointer
        │       └── qodo-skills enqueues one all-provider marketplace run
        └── QAR combines it with the protected CLI pointer
                └── opens or refreshes one compatible CLI + skills pin PR

QAR Release Please merge
        ↓ automatic build-once beta promotion
MP1 rollout
        ↓ all replicas digest-bound + authenticated clean install + exact tuple receipt
protected production + ST + on-prem distribution promotion
```

The pull model is idempotent. A watcher does nothing when its target already advertises the selected
release. The marketplace watcher byte-verifies the protected compatibility assets against the
immutable release, rejects releases below its successful default-branch run watermark, and rechecks
immediately before dispatch. The downstream atomic release lock safely arbitrates a simultaneous
manual launch. The QAR synchronizer resolves and verifies data-only locks without credentials,
attests their path-independent tuple digest in a run-scoped artifact, and restores those exact bytes
on separate validation and writer runners. Only the writer mints the scoped PR token, after the
artifact has passed the composed distribution smoke test. It uses one stable branch and PR for the
complete distribution tuple. The original manual compatibility, marketplace, CLI-pin, and
skills-pin workflows remain recovery controls. Production environments, provider publication, PR
merge, and customer deployment remain human-owned gates.

## Cutover sequence

The architecture is final; the operational rollout is staged so every step has an independent
rollback.

### 0. Close production prerequisites

- Confirm the existing provider-visible `qodo` listing identity in Claude, Codex, and Kiro.
- Record each current version, source commit/path, and reinstall/rollback procedure.
- Confirm Codex can update the existing listing from `qodo-in-harness` to the released
  `qodo-skills/codex-packages/qodo` snapshot without a new identity.
- Create protected GitHub environments `marketplace-claude`, `marketplace-kiro`, and
  `marketplace-codex` with required release-owner reviewers.
- Enable immutable releases in `qodo-ai/qodo-skills`.
- Install the dedicated `qodo-skills-release-bot` GitHub App on `qodo-ai/qodo-skills` with only
  `Administration: read`, `Contents: write`, and `Metadata: read`. Store its App id and private key only in the protected
  `marketplace-kiro` environment as `QODO_SKILLS_RELEASE_APP_ID` and
  `QODO_SKILLS_RELEASE_APP_PRIVATE_KEY`, and require at least one release reviewer. For the initial
  cutover, admin bypass remains enabled, self-review is allowed, and protected branches may deploy;
  the team accepts this weaker approval posture and can harden it independently later.
- Run `GITHUB_REPOSITORY=qodo-ai/qodo-skills scripts/audit-release-protections.sh` with a repository
  administrator's existing `gh` session before release. The audit verifies hidden bypass actors and
  one active selected-repository App installation. The protected release preflight then uses a
  short-lived, installation-wide read-only token to require the App's exact repository list to be
  only `qodo-ai/qodo-skills`; the normal administrator token cannot query that App-token-only API.
  No administrator or shared QAR credential is stored in this public repository.
- Keep exactly one active, no-exclusion, no-bypass **Immutable release tags** ruleset on
  `refs/tags/v*`; tag creation is allowed, but updates and deletion are blocked. Release preflight
  searches every ruleset page and rejects duplicate matches or a creation restriction.
- Create exactly one active **Kiro marketplace release** ruleset for
  `refs/heads/marketplace-kiro`: block creation, update, deletion, and force-push; exclude
  nothing; and grant always-bypass only to the dedicated App's `Integration` actor. The approved
  workflow mints a short-lived token scoped to this repository and advances the branch without a
  force push. The release workflow uses the same protected App only to verify repository
  immutability before creating a tag or draft. Repoint both existing Kiro listing URLs from `main` to this branch before the first
  marketplace-owned release.

Gate: every item is verified from provider/repository state. A source manifest is not evidence of
a live marketplace listing.

### 1. Release the compatible CLI first

Ship the CLI that:

- logs in before it offers skill guidance;
- reports official marketplace state for Claude, Codex, and Kiro;
- detects known skills.sh-compatible local agents and supports multiple selection;
- when none is detected, reads the current skills.sh agent catalog, excludes marketplace-owned
  IDs, and preserves each selected agent's supported project/global scope;
- explains which detected agents are marketplace-owned and which can be completed immediately;
- after one explicit confirmation, installs and byte-verifies core for selected non-marketplace
  agents; Qodo Standards remains a separate opt-in;
- has no `qodo skills install` and no task-time workflow endpoint;
- enrolls only byte-exact copies from shipped CLI releases, including the live `next.36` bytes;
- immediately refreshes enrolled copies from its embedded cutover snapshot, then follows the
  checksummed CLI-managed qodo-skills channel in the background;
- never adds a missing skill, never touches marketplace/enterprise roots, honors the historical
  `autoManage: false` preference, and preserves any user edit or unknown copy;
- refreshes only the checksummed compact skill index and emits non-fatal stale notices;
- retains explicit `qodo skills cleanup` for migration: it holds a validated root identity and
  atomically quarantines exact immutable-release copies without recursively deleting bytes.

The first compatible release is `0.1.0-next.37`. Do not publish a skill package whose declared
`minimumCliVersion` is newer than the live runtime channel. Because marketplace and skills.sh
updates can still arrive before a particular machine updates, every skill probes `qodo --version`
without provenance flags and offers the runtime's already-recorded update origin before auth.

Gate: clean install and upgrade on macOS/Linux/Windows; login; catalog refresh; machine-readable
help; marketplace status outcomes; multi-agent skills.sh command; optional package isolation;
`next.36` CLI-created roots update to the exact canonical bytes; marketplace, user-modified, unknown,
and opted-out roots remain byte-identical; failed replacement restores the active copy.

Rollback: roll back the runtime independently. Existing CLI-managed skills keep their last verified
copy and recoverable predecessor; marketplace skills remain owned by their host.

### 2. Publish one complete canonical skills release

- Before publishing `v1.0.10`, merge and deploy qodo-agent-runtime#587. It adds backward-compatible
  schema-v2 parsing, requires the index `sourceCommit` to equal the enterprise manifest commit,
  preserves the exact v2 bytes under the immutable release path, and serves a checksum-matched
  schema-v1 projection from the existing stale-notice endpoint for pre-`.40` CLIs. It does not
  advance the QAR skills pin.
- Merge the canonical/provider PR, then rebase and merge its stacked distribution PR containing
  both the CLI-managed and enterprise release assets. The next release is `v1.0.10`; it adds the
  immutable source identity required by the public installer without changing skill bodies.
- Release validation derives changes from both canonical files and the catalog: packaging-only
  changes require a package release, every semantic-version delta must match its release record,
  catalog-only bumps cannot disappear from release notes, `initial` cannot target an existing
  skill, and deletion is blocked until the release schema defines an explicit tombstone.
- After the compatible CLI is live, dispatch **Release skills** manually from current `main`; the
  workflow verifies the selected SHA is current before and after validation, pushes a protected
  annotated tag, verifies its peeled remote SHA, creates or resumes a draft, verifies both assets
  before publication, and then re-verifies the immutable tag and assets after publication.
- CI executes those checked-in preflight and publication programs with a stateful fake GitHub CLI,
  including credential/ruleset failures, corrupted draft rejection and resume, successful
  publication, and idempotent immutable verification. The release asset inventory includes a
  schema-v2 compact index generated from the detached release worktree with its exact source commit,
  the data-only CLI-managed bundle, the enterprise bundle, and their checksums. Publication rejects
  an index whose commit or package version differs from the resolved release.
- After the immutable GitHub release is verified, the hourly **release: publish skills compatibility
  channel** watcher in `qodo-ai/qodo-in-cli` selects that newest immutable release. Its canary job verifies the immutable
  release and checksums, copies the compact index and CLI-managed bundle to tag-scoped
  `get.qodo.ai` paths, and advances only the `skills` pointers in `version.json`. The protected
  production job still requires approval and promotes the exact canary bytes. An exact tag may be
  dispatched manually for recovery. CLI release jobs preserve those pointers when they update the
  independent runtime channel.
- Smoke-test skills.sh core installation on representative non-marketplace agents before provider
  promotion.

Gate: `npm test`, immutable release verification, tag-scoped canary and production compatibility
assets plus exact same-origin `version.json` pointers, four canonical core capabilities, standards
opt-in, full embedded body/provenance checks, and skills.sh project/global update without package
broadening. Marketplace packages may also expose the generated `qodo-pr-resolver` compatibility
name, which is the same canonical resolver workflow and not a fifth capability.

Rollback: publish a new immutable patch. Never replace the release asset.

### 2a. Prepare the on-prem enterprise lane

- The immutable skills release includes the deterministic enterprise compatibility archive plus
  path-scoped Agent Skills Discovery v0.2 indexes for `qodo` and `qodo-standards`. Every feed entry
  points to a deterministic, SHA-256-pinned single-skill archive with `enterprise-bundle`
  provenance. Core and Standards never share an index.
- QAR pins the skills version and hashes in a lock separate from its CLI lock, verifies and bakes
  both during the backend image build, and serves each discovery index at
  `/toolbox/skills/<package>/.well-known/agent-skills/index.json` and its digest-pinned archives at
  `/toolbox/skills/<package>/artifacts/<asset>`. The index-relative `../../artifacts/<asset>` URL
  resolves to that same package-scoped route; it does not escape `/toolbox/skills/<package>`.
- QAR's hourly target-owned synchronizer, delivered by `qodo-agent-runtime#594`, reads the protected
  public CLI pointer and newest immutable GitHub skills release, updates
  the CLI lock before validating the skills minimum, verifies and smoke-tests the combined tuple,
  and opens or refreshes one dependency PR. Public artifacts never execute on the runner that holds
  the repository write token: a credential-free resolver publishes the exact verified locks as a
  run-scoped artifact, a separate validator restores and smoke-tests those bytes, and only then does
  a fresh writer restore the same tuple and mint its scoped token. An unchanged automation branch
  preserves its head, reviews, and approvals. Until that PR is merged, the separate single-pin
  workflows remain authoritative; afterward they remain manual recovery controls.
- The compatible CLI fetches from the recorded QAR origin, so an on-prem client never falls back to
  public GitHub. Historical CLI-managed roots and new enterprise roots retain separate receipts and
  lifecycle owners.
- After login, `qodo agents install --enterprise` opens the lifecycle engine's current detected-agent
  multi-select and installs core globally. Qodo Standards remains absent unless explicitly selected.
  Automation may pass current agent IDs with `--agent ... --yes`; the lifecycle engine, not Qodo's
  CLI source, validates those IDs. A newly supported agent therefore needs only a reviewed helper
  pin/release, never a new Qodo-owned mapping or copier.
- The launcher suppresses only the parent process's build-derived agent-detection markers so running
  setup from Codex or Claude cannot bypass multi-select and consent; it does not maintain target
  paths or agent IDs.
- The Qodo CLI release embeds a reproducible packaging build of exact-pinned `skills@1.5.15`, the
  newest tested release that both supports discovery v0.2 and executes at Qodo's Node 20.6 floor.
  It materializes that helper by SHA-256 under Qodo's private runtime directory and forces
  `DO_NOT_TRACK=1`. No npm, npx, skills.sh, GitHub, or marketplace access occurs on the client.
- Background maintenance checks only the QAR version pointer. When newer content exists it emits
  the exact `qodo agents update --enterprise` action. Updates are never unattended: the user sees
  the lifecycle engine's overwrite summary and confirms it. This remains the policy until the
  upstream engine can prove modified-root preservation; local edits are not silently discarded.
- The discovery manifest declares `minimumCliVersion: 0.1.0-next.39` independently from the
  package-wide `.37` minimum. QAR rejects the feed until its CLI lock reaches that version.

Gate: deterministic archive and discovery-feed rebuild; exact manifest/archive/index digests; QAR
offline image build and route tests; private-origin no-egress; telemetry-disabled pinned-helper
import at Node 20.6; uncached digest-bound MP1 tuple evidence from every declared replica; fresh
authenticated clean-machine import of exactly the four core skills into Codex and Claude; Standards
and unrelated skills absent; CLI and installer bytes verified before execution; the MP1 key scoped
only to login; an authenticated same-origin identity request after installation; live runtime
evidence of the promoted image digest; an immutable acceptance receipt binding QAR image digest,
commit, CLI, and skills; production promotion of that accepted image digest only;
prompted upgrade; retry; new-session activation; and a pre-`.40` CLI accepting the generated
schema-v1 pointer and checksum. A later QAR **repin** PR cannot become merge-ready
until the immutable qodo-skills release exists at the exact bytes in its lock; the backward-compatible
schema parser must land before that release is published.

Rollback: publish a new immutable skills patch and advance only the QAR skills pin. The CLI pin is
unchanged unless runtime compatibility independently requires it.

### 3. Promote Claude and Kiro

After the protected compatibility pointer is live, the hourly marketplace watcher verifies the
advertised index and bundle checksums, release identity, and exact equality with the immutable
GitHub release assets, then automatically starts one **Ship
marketplaces** run with all providers selected. Selection is provider-level: the action
ships every configured listing for each selected provider, including both `qodo` and the separately
installable `qodo-standards`. It then pauses each provider verification in its protected environment
while the release owner completes any provider submission. Approve a provider only when its listing
is expected to be visible; the resumed job verifies the exact release and fails closed otherwise.
An existing default-branch run for the tag suppresses duplicate automatic dispatch, including after
failure. The watcher rejects a tag below the highest successful default-branch release, serializes
automatic launches, and rechecks immediately before dispatch. A simultaneous manual dispatch may
create a second run, but the downstream atomic release lock admits exactly one owner without using
GitHub Actions' lossy pending-run concurrency.
Release owners use the manual provider selector to retry or recover only the required providers.
Only one release tag may be active across providers: any attempt fails visibly while a different
tag owns the atomic `refs/heads/qodo-marketplace-release-lock`. The owner holds it through provider
approval. Acquire, stale recovery, and release append commits with non-force fast-forward updates,
so a contender can advance only the exact owner commit it inspected and cleanup cannot remove a
replacement. A later dispatch may supersede a stale owner only after GitHub marks its run completed.
This avoids GitHub's lossy single-pending queue, launch races, and old-tag rerun semantics.

- Preserve the existing `qodo` listing identity and repoint it to the generated core path.
- Publish `qodo-standards` only as a separate optional listing.
- Kiro uses its current Agent Plugins power contract (`plugin.json` plus nested `skills/`), not the
  retired `POWER.md`/`steering/` package layout.
- Kiro packages a generated, user-reviewed permission template for the stable `qodo read *`
  gateway. The runtime admits only catalog entries explicitly marked non-mutating, so new read
  tools do not require another permission-pattern release; all other Qodo commands remain on ask.
- Kiro follows the protected `marketplace-kiro` branch, which the approved release job advances
  fast-forward to the immutable tag before verifying the provider-visible listing. It never follows
  day-to-day `main`.
- Wait for provider-visible exact commit/path before behavioral acceptance.

Gate per provider: fresh install, in-place upgrade, exactly four canonical core capabilities plus
the expected generated resolver compatibility alias (five core-package skill entries), optional standards absence,
setup/login, one read workflow, one approval-gated write workflow, update and new-session activation.

Rollback: publish/repoint to a new last-good patch through the provider-supported flow. Kiro is
strictly forward-only because the protected release branch cannot be rewound.

### 4. Promote Codex and deprecate the old source

Use the all-provider run's Codex packet, update the existing Qodo
listing through the OpenAI portal, wait for review, and publish. Only after publication may the
release owner approve `marketplace-codex`.

Gate: provider-visible identity unchanged; exact qodo-skills release snapshot; fresh install;
upgrade from the current qodo-in-harness-backed version; core-only membership; optional standards
separate; normal CLI login/runtime behavior.

After the gate passes:

1. merge the qodo-in-harness deprecation PR;
2. disable new releases from the old source;
3. retain history and rollback artifacts for two normal release cycles;
4. archive only after those cycles remain healthy.

Rollback: while the window is open, restore the existing listing to the recorded last-good source
or ship a new canonical patch. Never create a second core listing.

### 5. Migrate existing CLI-first users

Migration is optional. A user who does nothing remains on the supported CLI-managed channel and
receives current skill bodies whenever automatic updates are enabled and the configured release
origin is reachable. A user with automatic updates disabled or an offline machine keeps the last
verified copy and receives no false claim of freshness.

- If the official plugin is installed, ask for a new session and verify Qodo.
- If a listing is visible, direct the user to the host’s install action.
- If no listing exists, use detected agents or the current read-only skills.sh catalog to select
  one or more non-marketplace agents, confirm once, then install and verify them in the requested
  scope through the pinned engine.
- Install Qodo Standards only after an explicit selection.
- Retire exact CLI copies only after the new owner works in a fresh session.

Claude’s dedicated root can be retired normally. Codex checks both the current shared root and the
historical `$CODEX_HOME/skills` root. Shared `.agents/skills` roots require `--force-shared` only
after every consumer has migrated. Any edit, symlink, extra file, unknown version, or hash mismatch
is preserved; an exact shipped copy is moved to a recoverable hidden quarantine, never recursively
deleted.

## Update experience after cutover

1. The marketplace or skills.sh publishes/observes the new complete skill.
2. The CLI’s daily bounded metadata refresh may notice that the loaded skill version is stale. For
   enterprise installs this is a detached QAR pointer check, never an unattended root mutation.
3. The current Qodo command succeeds and emits `QODO_NOTICE` on stderr.
4. The skill finishes the current task, inventories its lifecycle owner read-only, shows the fully
   resolved scope-preserving action, and asks once.
5. The lifecycle owner updates the skill. For skills.sh-owned roots, the shown action is the exact
   `qodo agents update --agent <ids> --yes` command; the user then starts a new agent session.

The CLI never runs `npx skills` in the background and never rewrites marketplace files. New
optional skills are discoverable but never auto-installed.

## Release-day gates

| Gate | Evidence required | Blocks |
|---|---|---|
| Source | exact merged heads, full CI, generated-drift checks | GitHub release |
| Repository | successful administrator audit, dedicated repository-scoped release App, immutable releases enabled, no-bypass `v*` tag ruleset, protected `marketplace-kiro` branch, protected tag SHA, and post-publication immutable asset bytes | all promotion |
| Automation | protected compatibility pointer, one marketplace run per tag, one reviewed QAR tuple PR, credential-isolated tuple validation | downstream promotion |
| Claude | official catalog exact SHA/path | Claude completion |
| Kiro | live Agent Plugins power on `marketplace-kiro` at the exact release SHA/path | Kiro completion |
| Codex | portal review + publish + protected attestation | Codex completion and old-repo deprecation |
| Behavior | fresh install, upgrade, package isolation, setup/read/write/update | provider sign-off |
| Migration | no duplicate/shadowed skill; cleanup preserves user changes | broad rollout |
| On-prem | immutable enterprise asset hashes, QAR pin/routes, no-egress, MP1 authenticated exact-core install receipt, accepted image digest, core-only customer import and upgrade | enterprise rollout |

No gate is satisfied by an announcement, packet, or green workflow that does not prove the named
external state.

The generic-agent acceptance fixture must also add a synthetic agent that is absent from the
bundled CLI snapshot but present in the live catalog, then prove it is selectable, retains its
declared scope, and cannot route a marketplace-owned ID through skills.sh.

## Go/no-go

Go only when:

- CLI and skills PR heads are independently green and review-clean;
- release immutability, the dedicated least-privilege release App, protected `marketplace-kiro`, and
  all three marketplace environment protections are configured;
- rollback identities/artifacts are recorded;
- selected provider publication owners are available;
- fresh-install and upgrade fixtures are ready.

Stop the rollout for a provider if its identity changes, exact source cannot be verified, core
installs standards, an upgrade creates duplicates, login/tool discovery fails, or rollback cannot
be executed. Other providers may proceed independently because promotion is selectable.

# Qodo marketplace cutover and release strategy

## Outcome

Qodo moves skill ownership out of the CLI without creating a second architecture:

> Qodo authors skills once; every installed root has one lifecycle owner. Marketplaces and the
> enterprise bundle update plugin roots; the CLI-managed channel updates only roots created by
> earlier Qodo CLI releases;
> the CLI updates the runtime.

- Claude Code, Codex, and Kiro receive complete generated skills through their official listings.
- Compatible agents without a Qodo listing use skills.sh.
- On-prem QAR deployments pin and serve one immutable enterprise archive beside the independently
  pinned CLI; customer deployment tooling owns plugin rollout.
- `qodo-standards` remains a separate optional package everywhere.
- Existing users who keep the copies originally installed by the CLI continue receiving current
  skills automatically; marketplace migration is optional, not a support deadline.
- The CLI authenticates and runs tools, updates itself, prints lifecycle guidance, emits stale-skill
  notices, and maintains only hash-exact CLI-managed copies through a separate compatibility channel.
- No task-time playbook loader or general-purpose CLI skill installer ships in the cutover.

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
          ├── enterprise archive    Claude/Codex/Kiro/portable offline projections
          └── CLI-managed bundle    current bytes for proven earlier CLI-managed roots

qodo CLI ── login + runtime + tool help + version notice
        ├── never creates a new skill installation after cutover
        └── updates only roots carrying CLI-managed ownership proof

QAR /toolbox ── independently pinned CLI + enterprise skills assets
             └── same-origin checksummed metadata; no public-network dependency at runtime
```

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
  `Contents: write` and `Metadata: read`. Store its App id and private key only in the protected
  `marketplace-kiro` environment as `QODO_SKILLS_RELEASE_APP_ID` and
  `QODO_SKILLS_RELEASE_APP_PRIVATE_KEY`, and require at least one release reviewer. For the initial
  cutover, admin bypass remains enabled, self-review is allowed, and protected branches may deploy;
  the team accepts this weaker approval posture and can harden it independently later.
- Run `GITHUB_REPOSITORY=qodo-ai/qodo-skills scripts/audit-release-protections.sh` with a repository
  administrator's existing `gh` session before release. The audit verifies hidden bypass actors;
  no administrator or shared QAR credential is stored in this public repository.
- Keep exactly one active, no-exclusion, no-bypass **Immutable release tags** ruleset on
  `refs/tags/v*`; tag creation is allowed, but updates and deletion are blocked. Release preflight
  searches every ruleset page and rejects duplicate matches or a creation restriction.
- Create exactly one active **Kiro marketplace release** ruleset for
  `refs/heads/marketplace-kiro`: block update, deletion, and force-push; permit creation; exclude
  nothing; and grant always-bypass only to the dedicated App's `Integration` actor. The approved
  workflow mints a short-lived token scoped to this repository and advances the branch without a
  force push. Repoint both existing Kiro listing URLs from `main` to this branch before the first
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
- prints exact core and optional-package commands without executing them;
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

- Merge the canonical/provider PR, then rebase and merge its stacked distribution PR containing
  both the CLI-managed and enterprise release assets. Do not publish the intermediate package
  version: the first cutover release is the complete `v1.0.7` tag.
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
  publication, and idempotent immutable verification. The release asset inventory includes the
  compact index, the data-only CLI-managed bundle, the enterprise bundle, and their checksums.
- After the immutable GitHub release is verified, dispatch **release: publish skills compatibility
  channel** in `qodo-ai/qodo-in-cli` with that exact tag. Its canary job verifies the immutable
  release and checksums, copies the compact index and CLI-managed bundle to tag-scoped
  `get.qodo.ai` paths, and advances only the `skills` pointers in `version.json`. The protected
  production job promotes the exact canary bytes. CLI release jobs preserve those pointers when
  they update the independent runtime channel.
- Smoke-test skills.sh core installation on representative non-marketplace agents before provider
  promotion.

Gate: `npm test`, immutable release verification, tag-scoped canary and production compatibility
assets plus exact same-origin `version.json` pointers, four canonical core capabilities, standards
opt-in, full embedded body/provenance checks, and skills.sh project/global update without package
broadening. Marketplace packages may also expose the generated `qodo-pr-resolver` compatibility
name, which is the same canonical resolver workflow and not a fifth capability.

Rollback: publish a new immutable patch. Never replace the release asset.

### 2a. Prepare the on-prem enterprise lane

- The immutable skills release includes a deterministic enterprise manifest, archive, and
  checksums. The archive stamps `enterprise-bundle` provenance into complete Claude, Codex, Kiro,
  and portable projections while preserving core/Standards package isolation.
- QAR pins the skills version and hashes in a lock separate from its CLI lock, verifies and bakes
  both during the backend image build, and serves the skills index, CLI-managed bundle, and archive
  under `/toolbox`.
- The compatible CLI fetches the CLI-managed bundle from the recorded QAR origin, so an on-prem
  client never falls back to public GitHub. Only previously enrolled CLI-managed roots are updated;
  enterprise plugin imports remain customer-controlled.
- A customer deployment imports the matching host package through its approved local plugin
  lifecycle. If that importer uses the skills CLI, every command runs with `DO_NOT_TRACK=1`, as
  declared by the bundle manifest. Qodo Standards remains a separate explicit choice.

Gate: deterministic archive rebuild; exact manifest/archive/index checksums; QAR offline image
build and route tests; private-origin no-egress; telemetry-disabled skills-CLI import when used;
fresh core import; Standards absent; enterprise
bundle upgrade; new-session activation. The QAR PR cannot become merge-ready until the pinned
immutable qodo-skills release exists at the exact bytes in its lock.

Rollback: publish a new immutable skills patch and advance only the QAR skills pin. The CLI pin is
unchanged unless runtime compatibility independently requires it.

### 3. Promote Claude and Kiro

Run **Ship marketplaces** with Claude and Kiro selected. Selection is provider-level: the action
ships every configured listing for each selected provider, including both `qodo` and the separately
installable `qodo-standards`. It then pauses each provider verification in its protected environment
while the release owner completes any provider submission. Approve a provider only when its listing
is expected to be visible; the resumed job verifies the exact release and fails closed otherwise.
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

Run **Ship marketplaces** with Codex selected, download the exact packet, update the existing Qodo
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
  one or more non-marketplace agents, then print exact scope-preserving commands.
- Install Qodo Standards only after an explicit selection.
- Retire exact CLI copies only after the new owner works in a fresh session.

Claude’s dedicated root can be retired normally. Codex checks both the current shared root and the
historical `$CODEX_HOME/skills` root. Shared `.agents/skills` roots require `--force-shared` only
after every consumer has migrated. Any edit, symlink, extra file, unknown version, or hash mismatch
is preserved; an exact shipped copy is moved to a recoverable hidden quarantine, never recursively
deleted.

## Update experience after cutover

1. The marketplace or skills.sh publishes/observes the new complete skill.
2. The CLI’s daily bounded metadata refresh may notice that the loaded skill version is stale.
3. The current Qodo command succeeds and emits `QODO_NOTICE` on stderr.
4. The skill finishes the current task, inventories its lifecycle owner read-only, shows the fully
   resolved scope-preserving action, and asks once.
5. The lifecycle owner updates the skill; the user starts a new agent session.

The CLI never runs `npx skills` in the background and never rewrites marketplace files. New
optional skills are discoverable but never auto-installed.

## Release-day gates

| Gate | Evidence required | Blocks |
|---|---|---|
| Source | exact merged heads, full CI, generated-drift checks | GitHub release |
| Repository | successful administrator audit, dedicated repository-scoped release App, immutable releases enabled, no-bypass `v*` tag ruleset, protected `marketplace-kiro` branch, protected tag SHA, and post-publication immutable asset bytes | all promotion |
| Claude | official catalog exact SHA/path | Claude completion |
| Kiro | live Agent Plugins power on `marketplace-kiro` at the exact release SHA/path | Kiro completion |
| Codex | portal review + publish + protected attestation | Codex completion and old-repo deprecation |
| Behavior | fresh install, upgrade, package isolation, setup/read/write/update | provider sign-off |
| Migration | no duplicate/shadowed skill; cleanup preserves user changes | broad rollout |
| On-prem | immutable enterprise asset hashes, QAR pin/routes, no-egress, core-only import and upgrade | enterprise rollout |

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

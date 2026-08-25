# Qodo marketplace cutover and release strategy

## Outcome

Qodo moves skill ownership out of the CLI without creating a second architecture:

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

- Claude Code, Codex, and Kiro receive complete generated skills through their official listings.
- Compatible agents without a Qodo listing use skills.sh.
- `qodo-standards` remains a separate optional package everywhere.
- The CLI authenticates and runs tools, updates itself, prints lifecycle guidance, emits stale-skill
  notices, and performs only hash-exact cleanup of its retired copies.
- No task-time playbook loader and no CLI skill installer/updater ship in the cutover.

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
          ├── kiro-power*/          Kiro complete skills
          └── skills/               skills.sh source

qodo CLI ── login + runtime + tool help + version notice
        └── never installs, updates, or serves workflow instructions
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
- Configure `QODO_RELEASE_ADMIN_TOKEN` with repository `Administration: read` only. The workflow
  uses it solely to verify immutability; normal `GITHUB_TOKEN` remains the publication credential.
- Keep exactly one active, no-exclusion, no-bypass **Immutable release tags** ruleset on
  `refs/tags/v*`; tag creation is allowed, but updates and deletion are blocked. Release preflight
  searches every ruleset page and rejects duplicate matches or a creation restriction.

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
- has no `qodo skills install`, no direct updater, and no task-time workflow endpoint;
- refreshes only the checksummed compact skill index and emits non-fatal stale notices;
- retains explicit, hash-exact `qodo skills cleanup` for migration.

Gate: clean install and upgrade on macOS/Linux/Windows; login; catalog refresh; machine-readable
help; marketplace status outcomes; multi-agent skills.sh command; optional package isolation; no
skill-root mutation during ordinary startup.

Rollback: roll back only the runtime. Existing skills remain owned by their current host.

### 2. Publish the canonical skills release

- Merge the atomic qodo-skills PR with canonical version bumps and generated provider packages.
- After the compatible CLI is live, dispatch **Release skills** manually from current `main`; the
  workflow verifies the selected SHA is current before and after validation, pushes a protected
  annotated tag, verifies its peeled remote SHA, creates or resumes a draft, verifies both assets
  before publication, and then re-verifies the immutable tag and assets after publication.
- CI executes those checked-in preflight and publication programs with a stateful fake GitHub CLI,
  including credential/ruleset failures, corrupted draft rejection and resume, successful
  publication, and idempotent immutable verification.
- Smoke-test skills.sh core installation on representative non-marketplace agents before provider
  promotion.

Gate: `npm test`, immutable release verification, core-only four-skill membership, standards
opt-in, full embedded body/provenance checks, and skills.sh project/global update without package
broadening.

Rollback: publish a new immutable patch. Never replace the release asset.

### 3. Promote Claude and Kiro

Run **Ship marketplaces** with Claude and Kiro selected. The action prepares both packets, then
pauses each provider verification in its protected environment while the release owner completes
any provider submission. Approve a provider only when its listing is expected to be visible; the
resumed job verifies the exact release and fails closed otherwise.

- Preserve the existing `qodo` listing identity and repoint it to the generated core path.
- Publish `qodo-standards` only as a separate optional listing.
- Wait for provider-visible exact commit/path before behavioral acceptance.

Gate per provider: fresh install, in-place upgrade, exactly four core skills, optional standards
absence, setup/login, one read workflow, one approval-gated write workflow, update and new-session
activation.

Rollback: publish/repoint to a new last-good patch through the provider-supported flow.

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

- If the official plugin is installed, ask for a new session and verify Qodo.
- If a listing is visible, direct the user to the host’s install action.
- If no listing exists, use detected agents or the current read-only skills.sh catalog to select
  one or more non-marketplace agents, then print exact scope-preserving commands.
- Install Qodo Standards only after an explicit selection.
- Remove retired CLI copies only after the new owner works in a fresh session.

Claude’s dedicated root can be cleaned normally. Shared `.agents/skills` roots require
`--force-shared` only after every consumer has migrated. Any edit, symlink, extra file, or hash
mismatch is preserved.

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
| Repository | admin-read preflight credential, immutable releases enabled, no-bypass `v*` tag update/deletion ruleset, protected tag SHA, and post-publication immutable asset bytes | all promotion |
| Claude | official catalog exact SHA/path | Claude completion |
| Kiro | live Power exact repository/branch/path | Kiro completion |
| Codex | portal review + publish + protected attestation | Codex completion and old-repo deprecation |
| Behavior | fresh install, upgrade, package isolation, setup/read/write/update | provider sign-off |
| Migration | no duplicate/shadowed skill; cleanup preserves user changes | broad rollout |

No gate is satisfied by an announcement, packet, or green workflow that does not prove the named
external state.

The generic-agent acceptance fixture must also add a synthetic agent that is absent from the
bundled CLI snapshot but present in the live catalog, then prove it is selectable, retains its
declared scope, and cannot route a marketplace-owned ID through skills.sh.

## Go/no-go

Go only when:

- CLI and skills PR heads are independently green and review-clean;
- release immutability, its admin-read preflight credential, and all three marketplace environment
  protections are configured;
- rollback identities/artifacts are recorded;
- selected provider publication owners are available;
- fresh-install and upgrade fixtures are ready.

Stop the rollout for a provider if its identity changes, exact source cannot be verified, core
installs standards, an upgrade creates duplicates, login/tool discovery fails, or rollback cannot
be executed. Other providers may proceed independently because promotion is selectable.

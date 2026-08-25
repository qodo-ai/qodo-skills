# Marketplace migration and release plan

This is an ordered migration, not a three-PR atomic merge. Each stage has an independent rollback
and an evidence gate. The invariant is:

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

## Stage 0 — production prerequisites (no user-visible change)

- Confirm the existing identities and source paths in the provider consoles:
  - Claude: `qodo@claude-plugins-official` → current source, then generated `packages/qodo/`.
  - Kiro: Qodo Power → `qodo-ai/qodo-skills/kiro-power`.
  - Codex: existing Qodo entry, currently sourced from `qodo-in-harness/codex-qodo`.
- Confirm the provider can repoint that existing Codex entry to `qodo-ai/qodo-skills/packages/qodo`
  without
  creating a new plugin identity.
- Record the last known-good provider versions, source SHAs, artifacts, and reinstall steps.

**Gate:** all three listing identities and rollback artifacts are confirmed from provider-visible
state. Repository configuration alone is not evidence.

## Stage 1 — release the runtime-compatible CLI first

Release the `qodo-in-cli` change before changing any listing:

- `qodo setup` authenticates, discovers installed local agents, and reports official marketplace
  state and native next steps only when the provider snapshot exposes Qodo.
- `qodo agents status --json` reports installed, available, not listed, action required, or error.
- `qodo agents install` is idempotent, never invents a marketplace ID, and never mutates a
  marketplace-owned plugin or cache.
- Kiro remains a provider-UI step because the curated install is owned by Kiro.
- ordinary startup no longer writes marketplace-managed skills;
- `qodo skills install` remains the explicit offline fallback;
- `qodo skills cleanup` removes only byte-exact generated fallback copies and refuses shared roots
  without explicit acknowledgement; retained provenance metadata never grants deletion authority.

**Gate:** fresh CLI install, upgrade from the preceding CLI, login, catalog refresh, and all
marketplace status outcomes pass on macOS, Linux, and Windows. Do not remove legacy skill copies.

**Rollback:** roll back only the CLI release. Existing plugins and fallback skills keep working.

## Stage 2 — publish canonical skills and cut Claude/Kiro over in place

Merge and publish `qodo-skills` v1.0.2 only after Stage 1 is available:

- canonical skills remain under `skills/`;
- Claude preserves its official core plugin ID while repointing to `packages/qodo/`;
- Kiro continues using the existing `kiro-power/` source path, now a generated Agent Plugins 1.0
  projection;
- `qodo-standards` is submitted as a separate optional Claude plugin and Kiro Power sourced from
  `packages/qodo-standards/` and `kiro-power-standards/`;
- the same release contains package-local Codex manifests, but the Codex listing remains unchanged
  until Stage 3.

Update Claude and Kiro core source SHAs through their existing listings. Do not create replacement
core listings; the optional standards capability has its own explicit identity.

**Gate per provider:** provider-visible version/source SHA, fresh install, upgrade of an existing
0.x install, `qodo-setup`, one read-only workflow, one approval-gated write workflow, and host-owned
update replacement. Restart the host where required.

**Rollback:** publish a new canonical patch restoring the last good behavior and repoint the
provider to that immutable patch. Never move v1.0.2 or mutate a cached package.

## Stage 2B — enable direct connections for agents without a marketplace

The same immutable `qodo-skills` release publishes `qodo-skills-direct.json` and its SHA-256.
After Stage 1's CLI is available and the Stage 2 release exists, validate the direct channel:

- a repository administrator enables GitHub immutable releases before publication, and the
  release workflow proves the published release's `immutable` API field is true;
- setup detects only installed agents without an official Qodo marketplace path;
- consent says “Connect Qodo to <agent>?” and explains automatic official-skill updates;
- interactive setup locks the four-skill core and offers `qodo-standards`; non-interactive setup
  never manufactures consent or writes a direct skill root;
- selected package IDs persist per target; updates never add a newly published optional package;
- the CLI verifies the release checksum, every safe relative path, each file digest, and the
  aggregate content digest before writing;
- the complete release is staged and swapped under a per-root recovery journal into only the
  recorded Qodo skill directories; backups remain until ownership state is durably committed;
- a normal Qodo skill invocation checks in a detached process at most once per day;
- local edits, removals, unexpected files, symlinks, offline requests, and checksum failures keep
  the prior release and pause updates for that target;
- marketplace-managed agents and every skill root owned by a detected marketplace host are
  excluded, and the new release loads on the next agent session.

**Gate:** repository-level release immutability, clean connection, automatic update, restart
activation, shared-root deduplication, conflict preservation, checksum failure, interrupted
update, and opt-out pass on macOS, Linux, and Windows.

Direct eligibility is capability-based, not an allowlist. The first cutover should run native
smoke tests for the agents observed in current production telemetry—Cursor, OpenCode, Hermes Agent,
GitHub Copilot, and Replit—but that list prioritizes acceptance evidence and does not constrain the
generic bundle. A newly recognized CLI registry entry with a verified project or global skills
directory and no official Qodo marketplace path automatically uses the same channel.

**Rollback:** leave the installed last-good release in place and publish a new immutable patch.
Do not mutate an existing release asset or fall back to the CLI's embedded compatibility snapshot.

## Stage 3 — repoint the existing Codex listing and deprecate the old repository

Repoint the existing Codex listing from `qodo-in-harness/codex-qodo` to the exact released
`qodo-skills` commit at `packages/qodo/`. Do not submit a replacement core plugin. Publish
`qodo-standards` only as a distinct optional entry. Verify:

- the provider-visible plugin ID is unchanged;
- the provider-visible source commit is the approved `qodo-skills` release;
- exactly the four core skills load and no embedded runtime is present;
- `qodo-get-rules` is absent until the optional Qodo Standards package is explicitly installed;
- a fresh install works;
- an existing 0.1.4 installation upgrades in place rather than creating a duplicate.

Only after those checks pass may the separate `qodo-in-harness` deprecation PR merge. Keep its last
known-good artifact and history available for the rollback window; disable new releases and mark
the repository archived only after two successful normal release cycles.

**Gate:** official marketplace shows the released version; fresh install and upgrade from 0.1.4
both load only their declared package skills; the separately installed CLI logs in and updates normally.

**Rollback:** repoint the existing listing to the last known-good harness source while the rollback
window is open, or to a new canonical patch after the source move is stable. Never create a second
listing or mutate an old tag.

## Stage 3B — add Cursor's native marketplace without dual ownership

Cursor accepts generated Agent Plugins 1.0 packages. Submit `packages/qodo/` and, separately,
`packages/qodo-standards/` through Cursor's reviewed marketplace flow. Until the core listing is provider-visible,
Cursor remains on the generic direct channel; repository readiness is not listing acceptance.

**Gate:** provider-visible Qodo listing, exact released source/version, clean install, native skill
discovery and invocation, marketplace-owned update, and migration from a direct-connected install
without duplicate skills. Only after those pass may a CLI release mark Cursor marketplace-owned.
That release preserves the prior direct copy until the user verifies the plugin and explicitly
cleans it up.

**Rollback:** leave Cursor on the direct channel or revert the listing source to the last accepted
immutable release. Never let the marketplace and direct updater own the same Cursor skill root.

## Stage 4 — migrate existing CLI-first users

On their next explicit setup, users see one of four honest outcomes:

1. official plugin already installed — start a new agent session;
2. official plugin visible — CLI offers the host's native install command;
3. Kiro detected — install through the Powers UI;
4. listing not yet visible — keep the generated fallback and retry later.

Only after a user verifies the marketplace plugin should they run the cleanup command. Claude's
dedicated root can be cleaned directly. Codex's `.agents/skills` root requires `--force-shared`
because other agents may still consume it.

**Gate:** support can recover every partial state without editing marketplace caches or deleting
user-authored skills.

## Stage 5 — retire the fallback in a later CLI release

Keep the fallback for at least two normal CLI release cycles. Remove it only when:

- all three official listings pass fresh-install and existing-install upgrade checks;
- migration telemetry and support volume meet the agreed threshold for two consecutive releases;
- no supported local host still depends on CLI file copying;
- rollback runbooks have been exercised from clean machines;
- the removal is announced as a separate CLI change.

## Required acceptance matrix

| Scenario | Expected result |
|---|---|
| CLI first, no agents | Login succeeds; no plugin success is claimed |
| CLI first, Claude listing visible | Exact official ID and native user-scope install step are reported; Claude owns installation |
| CLI first, Codex listing visible under any marketplace name | Discovered plugin ID and marketplace are reported; Codex owns installation |
| CLI first, listing rollout incomplete | `not_listed`; fallback remains untouched |
| Plugin first, CLI missing | `qodo-setup` points to the verified CLI installer and stops |
| Plugin first, CLI logged out | `qodo-setup` runs the one supported login flow |
| Existing official plugin | No reinstall; user is told to start a new session |
| Existing CLI-managed skill with edits/no provenance | Never removed |
| Existing managed skill in dedicated Claude root | Explicit cleanup removes only that copy |
| Existing managed skill in shared `.agents` root | Cleanup refuses without acknowledgement |
| Marketplace update fails | Previous cached plugin remains; CLI remains independently usable |
| Runtime update fails | Plugin remains; runtime rollback does not change skill artifacts |
| Offline environment | Explicit generated fallback remains available during the compatibility window |
| Agent without an official marketplace path | Consent-driven direct connection; verified release installs and updates automatically |
| Direct-connected skill was edited or removed | Preserve the target, report a conflict, and pause its automatic updates |

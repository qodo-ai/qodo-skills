# Marketplace migration and release plan

This is an ordered migration, not a three-PR atomic merge. Each stage has an independent rollback
and an evidence gate. The invariant is:

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

## Stage 0 — production prerequisites (no user-visible change)

- Confirm the existing identities and source paths in the provider consoles:
  - Claude: `qodo@claude-plugins-official` → `qodo-ai/qodo-skills` root.
  - Kiro: Qodo Power → `qodo-ai/qodo-skills/kiro-power`.
  - Codex: existing Qodo entry → `qodo-in-harness/codex-qodo` package identity.
- Create the `codex-production` GitHub environment with required human approval.
- Configure `NPM_TOKEN` there only if the existing Codex listing consumes npm.
- Configure `QODO_IN_HARNESS_DISPATCH_TOKEN` in `qodo-skills`, scoped only to dispatch
  `qodo-in-harness`.
- Record the last known-good provider versions, source SHAs, artifacts, and reinstall steps.

**Gate:** all three listing identities and rollback artifacts are confirmed from provider-visible
state. Repository configuration alone is not evidence.

## Stage 1 — release the runtime-compatible CLI first

Release the `qodo-in-cli` change before changing any listing:

- `qodo setup` authenticates, discovers installed local agents, and offers official marketplace
  installs only when the provider snapshot exposes Qodo.
- `qodo agents status --json` reports installed, available, not listed, action required, or error.
- `qodo agents install` is idempotent and never invents a marketplace ID.
- Kiro remains a provider-UI step because the curated install is owned by Kiro.
- ordinary startup no longer writes marketplace-managed skills;
- `qodo skills install` remains the explicit offline fallback;
- `qodo skills cleanup` removes only exact `vendor: qodo` fallback copies and refuses shared roots
  without explicit acknowledgement.

**Gate:** fresh CLI install, upgrade from the preceding CLI, login, catalog refresh, and all
marketplace status outcomes pass on macOS, Linux, and Windows. Do not remove legacy skill copies.

**Rollback:** roll back only the CLI release. Existing plugins and fallback skills keep working.

## Stage 2 — publish canonical skills and cut Claude/Kiro over in place

Merge and publish `qodo-skills` v1.0.0 only after Stage 1 is available:

- canonical skills remain under `skills/`;
- Claude continues using the existing repository root and official plugin ID;
- Kiro continues using the existing `kiro-power/` source path, now a generated Agent Plugins 1.0
  projection;
- the release tags the exact reviewed commit and dispatches the Codex import train.

Update Claude and Kiro source SHAs through their existing listings. Do not create new listings.

**Gate per provider:** provider-visible version/source SHA, fresh install, upgrade of an existing
0.x install, `qodo-setup`, one read-only workflow, one approval-gated write workflow, and host-owned
update replacement. Restart the host where required.

**Rollback:** publish a new canonical patch restoring the last good behavior and repoint the
provider to that immutable patch. Never move v1.0.0 or mutate a cached package.

## Stage 3 — migrate Codex through its existing package

The skills release opens a generated `qodo-in-harness` PR. Review that PR for:

- exact upstream tag and commit;
- content hash and six expected skill versions;
- removal of the embedded CLI runtime and all independent skill launchers;
- preservation of the `qodo` plugin and `@qodo/codex-plugin` identities;
- isolated marketplace/cache install with no `runtime/` directory.

After merge, run `Release Codex plugin` with the exact version through the protected production
environment. Publishing an artifact is not listing acceptance.

**Gate:** official marketplace shows the released version; fresh install and upgrade from 0.1.4
both load the six canonical skills; the separately installed CLI logs in and updates normally.

**Rollback:** publish a new Codex patch generated from the last known-good canonical tag. Do not
restore an embedded runtime and do not mutate the old package/tag.

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
| CLI first, Claude listing visible | Exact official ID installs at user scope |
| CLI first, Codex listing visible under any marketplace name | Discovered plugin ID installs |
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


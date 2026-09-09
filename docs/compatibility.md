# Compatibility contract

## Delivery matrix

| Host class | Install/update owner | Qodo package source |
|---|---|---|
| Claude Code official listing | Claude marketplace | `packages/qodo` |
| Codex official listing | Codex marketplace/portal | `codex-packages/qodo` |
| Kiro official listing | Kiro Powers tracking `main` | `kiro-power` |
| Compatible host without a listing | skills.sh | canonical `skills/` |

`qodo-standards` is a separate optional package on every surface. It is never included in core
install or update operations.

## Runtime compatibility

The current package declares `runtime.minimumCliVersion` in `distribution/catalog.json`; every
canonical skill repeats that value in an unadorned `qodo --version` gate before it sends newer
provenance flags. Skills require a compatible Qodo CLI that supports:

- `qodo read whoami --json`;
- `qodo read tools [<group> [<tool>]] --json`;
- the fail-closed `qodo read <group> <tool>` gateway for cached catalog entries explicitly marked
  non-mutating;
- provenance flags `--skill`, `--skill-version`, `--distribution`, and `--host`;
- non-fatal `QODO_NOTICE` output on stderr.

Skills must discover exact tool names and schemas at runtime. Examples in a skill are illustrative;
the cached catalog is authoritative for the current account and workspace.

Kiro's generated `qodo-read-only.permissions.yaml` contains only exact version probes and the
stable `qodo read *` prefix for supported executable spellings. It is a user-reviewed template,
never an automatically applied permission mutation. New read tools require no permission-template
change: they become reachable only when the runtime catalog explicitly marks them non-mutating.

## Release compatibility rules

1. A workflow-body change increments that skill version.
2. Any skill change increments the package version and regenerates all provider projections.
3. Generated packages contain the full canonical workflow and match its release version.
4. A core update cannot add Qodo Standards.
5. A provider identity/source migration is backward compatible only when it upgrades the existing
   listing in place and does not create a duplicate skill identity.
6. The CLI and skill release independently. A skill that raises `minimumCliVersion` must ship the
   compatible CLI first, probe without new flags, and degrade to the runtime's recorded update
   origin without misclassifying incompatibility as an authentication failure.
7. Rollback is a new immutable patch, never mutation of a published tag or asset.
8. Every distribution exposes exactly its package's canonical skill names. Starting with package
   v2.0.0, the `qodo-pr-resolver` compatibility skill is removed; update existing prompts to
   `qodo-review-resolver`. Historical CLI receipt aliases remain migration metadata and do not
   create additional skills.

## Acceptance

For each selected provider, release evidence must include:

- provider-visible version and source commit/path (Kiro tracks `main`; record its observed commit separately from immutable release pins);
- fresh install;
- upgrade from the currently published Qodo version;
- exactly four canonical core skill entries after core-only install, with matching names across
  distributions;
- Qodo Standards absent until explicitly installed;
- login/setup, one read workflow, and one approval-gated write workflow;
- host-owned update followed by a new session;
- no duplicate or shadowed copy from an earlier distribution channel.

For skills.sh, repeat the same behavioral checks on representative detected agents and verify both
project/global scope, multi-agent selection, exact package membership, update without broadening,
and preservation of user edits.

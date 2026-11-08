---
name: qodo-setup
description: Set up Qodo in a coding agent — install the CLI, sign in, and verify tools. Use after plugin installation, on setup requests, or when a Qodo skill finds a missing CLI or login.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.12"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
---

# Set up Qodo

Verify connection/tools, then return to the task. Skill installation is not readiness. Never handle credentials. Resolve references relative to this SKILL.md.

## Connected MCP

Inspect host-connected QAR schemas and call a harmless read. Check isError before structuredContent. Catalog visibility proves neither read nor write access; never test-write. Host/QAR own auth. Report missing tools, MT-AUTH-FORBIDDEN or connection errors without requesting API keys. For MCP-only setup, hand back. Use the same deployment if CLI access is requested/needed for local collection.

## Runtime

PowerShell: resolve the verified native/Node invocation in [runtime.md](references/runtime.md). POSIX: probe `qodo --version`, then `"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version` if missing. For missing runtime, follow that verified installation procedure. Setup requests cover installation subject to host approvals; plugin installation alone does not.
Keep the executable as `<qodo>`. Require CLI **2.0.0 or newer** before authentication. Compatible versions continue below without update preflight.

### Compatibility recovery

For old/unparseable versions, stop authenticated calls and explain. Before update checks/changes, test only whether QODO_UPDATE_BASE_URL is set; never print/change it. If set, stop for user resolution. All routes preserve origin, exact versions and update holds; never replace an exact version with a channel.
For parsed1.x, normal `qodo update` reaches approved stable2.x only if that origin enables migration. Require a newer compatible same-origin2.x target from the selected route's supported check. If legacy aliases serve1.x, check latest-2 before proposing `qodo update --channel latest-2`. Missing/failed checks stop; never assume activation or unrelated future-major authority.
For unparseable version/no supported updater, use the checksum-pinned installer reference. Preserve supported customer selectors/settings; normal verified installation selects the approved version. Explain the route; reuse covering runtime/installation authority or ask once before changing it. Make one approved attempt, reprobe unadorned version, and stop on denial/failure/incompatibility without another route, skill edits or an auth diagnosis.

## Connect and verify

Run `<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.12 --distribution skills-sh`. Reuse success. On failure read [authentication.md](references/authentication.md) before login; preserve deployment, never fall back to Cloud. Wait for login and recheck identity. Stop on denial/cancellation; diagnostic approval is not blanket authority.
Only after identity succeeds run `<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.12 --distribution skills-sh`. Require the task's capability. On failure report signed in but tools unavailable, the exact error and that command as retry; do not log in again. Reuse verified execution context with required host approvals.

## Handoff

Runtime/login setup does not authorize enterprise installation/maintenance. Disclose packages/maintenance; preserve opt-outs, edits, owners and optional choices. Never install optional Standards. For QODO_NOTICE/repeated Kiro read approvals read [host-recovery.md](references/host-recovery.md). CLI owns credentials, transport and updates; lifecycle owners update skills.
Report verified scope and one next action. Never claim readiness after failure, disable Keychain, copy credentials, change host permissions or offer unrestricted approvals. Readiness does not guarantee a later call succeeds.

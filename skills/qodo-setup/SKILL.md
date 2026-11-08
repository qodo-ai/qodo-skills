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

## Description

Verify the available Qodo path. Skill installation does not prove account or tool access.

## Prerequisites

A shell for CLI setup or a host-connected QAR MCP server. Never handle credentials.

## Instructions

### Connected MCP path

Inspect connected QAR tool schemas and annotations. With harmless input, call one
read-only tool; catalog visibility does not prove read access. Check `isError` before
`structuredContent`; an execution error is not readiness. A read cannot prove write
authorization: report writes as unverified until a user-authorized action. Never make
a test write. The host and QAR own MCP auth. Report missing tools, `MT-AUTH-FORBIDDEN`,
and connection errors as MCP access issues; never ask for an API key. For MCP-only setup,
report the verified scope and hand off here. Skip every CLI step below. Continue only if CLI access was
requested or is needed for local collection, using the same deployment.

Resolve `references/...` links relative to this installed `SKILL.md` directory.
Runtime/login setup does not authorize enterprise installation or maintenance.
For requested enterprise installs, disclose packages and maintenance before approval;
preserve opt-outs, edits, owners and optional-package choices.

### 1. Find or install the runtime

In PowerShell, resolve the verified native/Node invocation in [runtime.md](references/runtime.md)
first; `qodo` below represents that invocation. On POSIX, probe PATH directly:

```sh
qodo --version
```

If missing on POSIX, try `"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version`.
For a missing runtime, follow the verified installation reference; for an old/unparseable runtime, use the gate below. Setup requests cover installation subject
to host approvals; plugin installation alone does not. Retain the selected deployment.

Keep the executable as `<qodo>`. Require Qodo CLI **2.0.0 or newer** before authentication.

### Runtime compatibility recovery

If the version already meets the minimum, continue to Connect without an update preflight.
Otherwise stop authenticated calls and explain the compatibility issue. Before update checks or
runtime changes, test only whether `QODO_UPDATE_BASE_URL` is set; never print/change it. If set,
stop for the user to resolve the override. Preserve the recorded distribution origin, explicit
version choices and update holds on every route; never substitute a channel for an exact version.
For parsed1.x, ordinary `qodo update` can reach approved stable2.x when its origin enables migration.
Use supported update checks for the selected route and require a newer compatible same-origin2.x target.
If legacy aliases still serve1.x, check the supported `latest-2` recovery route before proposing
`qodo update --channel latest-2`. Missing/failed checks stop; do not assume migration is active.
This exception covers only approved1.x-to-stable2.x; it grants no unrelated future-major authority.
For an unparseable runtime or no supported updater, use the checksum-pinned installation procedure
in [runtime.md](references/runtime.md). Honor exact versions, holds and supported customer installer
selectors, preserving origin/settings. Let a normal verified installer select the approved version.
Explain the chosen route; reuse covering installation/runtime-update authority or ask once before
changing the runtime. Make one approved attempt, then rerun the unadorned version probe. On denial,
failure or continued incompatibility, stop without another route, skill edits or an auth diagnosis.

### 2. Connect

Run:

```sh
<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.12 --distribution skills-sh
```

Reuse a successful identity check. On failure, read
[authentication.md](references/authentication.md) before choosing login.

For Cloud, run `<qodo> login` when signed out. For customer deployments, preserve the
documented login endpoint; never fall back to Cloud. Wait for login, then recheck identity.

Reuse the successful execution context, requesting each required host approval. A diagnostic
approval is not blanket permission. Stop on cancellation or denied permission.

### 3. Verify tools

Only after identity succeeds, run:

```sh
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.12 --distribution skills-sh
```

Require a usable catalog and the task's capability; unrelated tools do not establish access.
If refresh fails, report that sign-in succeeded but tools are unavailable, with the exact error
and `<qodo> tools --refresh` as the retry. Do not log in again for a catalog failure.

## Configuration

The CLI owns credentials, transport and runtime updates; the package's
lifecycle owner updates skills. For `QODO_NOTICE` updates or repeated Kiro read approvals,
read [host-recovery.md](references/host-recovery.md) only when encountered.

## Error Handling

Give the actual error and one next action. Never report readiness after a failed
identity, canceled login or unavailable catalog. Never disable the keychain, copy credentials,
change host permission files, or offer unrestricted command approvals to make setup pass.

## 4. Hand off

Confirm Qodo connection and relevant tool readiness, then return to the authorized task.
Readiness does not prove a later tool call succeeds. Do not install optional Standards.

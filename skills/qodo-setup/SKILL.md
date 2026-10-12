---
name: qodo-setup
description: Set up Qodo in a coding agent — install the CLI, sign in, and verify tools. Use after plugin installation, on setup requests, or when a Qodo skill finds a missing CLI or login.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.9"
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

Run:

```sh
qodo --version
```

If missing, try `"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version` on POSIX.
For PowerShell or a missing CLI, read [runtime.md](references/runtime.md).
Follow that procedure. Setup requests cover CLI installation subject to host approvals;
plugin installation alone does not.

Keep the working executable as `<qodo>`. Require Qodo CLI **0.1.0-next.37 or newer**.
If older or unparseable, follow the runtime reference before any authenticated command.

### 2. Connect

Run:

```sh
<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.9 --distribution skills-sh
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
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.9 --distribution skills-sh
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

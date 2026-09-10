---
name: qodo-setup
description: Set up Qodo in a coding agent — install the CLI, sign in, and verify tools. Use after plugin installation, on setup requests, or when a Qodo skill finds a missing CLI or login.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.8"
  recommended: "true"
  package: "qodo"
  distribution: "marketplace"
  instruction_mode: "embedded"
---

# Set up Qodo

## Description

Install, connect and verify Qodo in this conversation. Plugin installation does not connect an account.

## Prerequisites

A shell and browser sign-in. Never request or read credentials.

## Instructions

Resolve `references/...` links relative to this installed `SKILL.md` directory.
Runtime/login setup does not authorize enterprise installation or maintenance.
For a separately requested enterprise install, disclose selected installations, packages and verified-source
automatic maintenance before approval. Preserve opt-outs, edits, owners and optional-package choices.

### 1. Find or install the runtime

Run:

```sh
qodo --version
```

If missing, try `"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version` on POSIX.
For PowerShell or a missing CLI, read [runtime.md](references/runtime.md).
Follow that procedure and continue. Setup requests cover CLI installation, subject to host
approvals and user restrictions. Plugin installation alone is not authorization.

Keep the working executable as `<qodo>`. Require Qodo CLI **0.1.0-next.37 or newer**.
If older or unparseable, follow the runtime reference before any authenticated command.

### 2. Connect

Run:

```sh
<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.8 --distribution marketplace --host codex
```

If successful, retain the verified identity and continue to step 3 without repeating it.
For a failed check, read [authentication.md](references/authentication.md) to distinguish
missing credentials, sandbox access, and other failures before choosing login.

For Qodo Cloud, announce and run `<qodo> login` when signed out. For any customer deployment,
read the authentication reference first: preserve its exact login endpoint and never guess
or fall back to Cloud. Wait for login to finish, then rerun the identity command above.
Browser opening alone is not success.

Remember the execution context where identity or login worked. Use that context for later
credential-dependent commands, requesting each required host approval; a diagnostic approval
does not grant blanket permission. Do not repeat a known-failing sandbox probe after login.
Stop on cancellation or denied permission.

### 3. Verify tools

Only after identity succeeds, run:

```sh
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.8 --distribution marketplace --host codex
```

Require a successful, nonempty usable catalog. Inspect structured results with bounded output
(exit status, error, tool count and relevant names); do not dump every tool schema.
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

Confirm verified readiness in plain prose, then suggest one next action supported by the
catalog and loaded skills, e.g. “Qodo is connected and ready. Ask ‘Explain this codebase.’”
Mention account or deployment when useful. Omit routine versions, counts and repeated summaries.
Do not launch another workflow or install optional Standards during setup.

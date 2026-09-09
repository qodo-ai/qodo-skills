---
name: qodo-setup
description: Set up Qodo in a local coding agent — install the CLI, sign in, and verify tools. Use after plugin installation, on a setup request, or when another Qodo skill finds a missing CLI or login.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.6"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
---

# Set up Qodo

## Description

Complete setup in this conversation: find or install the CLI, sign in, and verify tools.
Plugin installation does not connect an account.

## Prerequisites

A local shell and a user for browser sign-in. Never request or read credentials.

## Instructions

### 1. Find or install the runtime

Run:

```sh
qodo --version
```

If missing, try `"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version` on POSIX.
For PowerShell or a missing CLI, read [runtime.md](references/runtime.md).
Install through that procedure and continue here without requiring a second setup request.
A setup request covers the CLI install; honor host approvals and user restrictions.
Plugin installation alone does not authorize installing software.

Keep the working executable as `<qodo>`. Require Qodo CLI **0.1.0-next.37 or newer**.
If older or unparseable, follow the runtime reference before any authenticated command.

### 2. Connect

Run:

```sh
<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.6 --distribution skills-sh
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
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.6 --distribution skills-sh
```

Require a successful, nonempty usable catalog. Inspect structured results with bounded output
(exit status, error, tool count and relevant names); do not dump every tool schema.
If refresh fails, report that sign-in succeeded but tools are unavailable, with the exact error
and `<qodo> tools --refresh` as the retry. Do not log in again for a catalog failure.

## Configuration

Keep executable, deployment, execution context and provenance throughout setup.
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

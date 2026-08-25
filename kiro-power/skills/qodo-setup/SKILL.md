---
name: qodo-setup
description: Connect Qodo to the current local coding agent — verify the Qodo CLI, guide a secure installation when it is missing, complete browser login, and confirm managed tools are ready. Use after installing the Qodo plugin, when the user asks to set up or connect Qodo, or when another Qodo skill reports that the CLI is missing or logged out.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.3"
  recommended: "true"
  package: "qodo"
  distribution: "kiro-power"
  instruction_mode: "embedded"
---

# Set up Qodo

## Description

Turn a marketplace install into one guided first-use flow: find the local runtime,
authenticate the human through Qodo's browser login, and verify that this agent can use
the managed tools. Never ask the user to paste credentials into chat.

## Prerequisites

- The Qodo plugin or skills.sh package is installed for the current coding agent.
- The user is present to approve a checksum-verified CLI install and complete browser login.
- No credential, token, or invented installer checksum is copied into the conversation.

## Instructions

Follow the four-stage workflow below: preserve lifecycle notices, resolve the runtime, authenticate
the user, verify identity and tool readiness, then show the branded handoff exactly once.

## Handle a skill update notice

A Qodo command can emit `QODO_NOTICE <json>` to stderr while still succeeding. When
`code` is `qodo_skill_update_available`, keep the command's result and finish the current
task. Then follow the notice's `steps`: do read-only inventory first, resolve the installed
Qodo package and scope, show the exact lifecycle-owner update command or UI action, and ask
once before any mutation. If the user declines, keep the current version usable.

Never invoke a different lifecycle owner, guess a placeholder, or install an optional package
implicitly. After an approved update, ask for the host restart named by the notice; the current
session may still have the old skill loaded.

## 1. Find the runtime

Run:

```sh
qodo --version --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro
```

If a POSIX shell reports `qodo: command not found`, retry the standard user-scoped location:

```sh
"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro
```

In Windows PowerShell, use the native launcher:

```powershell
$qodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Join-Path $qodoHome 'bin/qodo.cmd') --version --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro
```

Keep the working command for every later step. Do not rewrite PATH automatically.

If neither command exists, tell the user:

> The Qodo marketplace plugin is installed, but its local runtime is not. Install the
> checksum-verified Qodo CLI from https://get.qodo.ai, then ask me to “Set up Qodo” again.

Stop there. Do not invent a checksum, pipe a remote script into a shell, use a package from
an unofficial registry, or install software without the user's approval.

## 2. Check authentication

Run `<qodo> whoami --json --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro`.

In a sandboxed environment, any failed `whoami` can be a blocked keychain rather than a logged-out
user. Ask for approval to retry that exact read-only command once outside the sandbox. The approval
applies only to that diagnostic retry. If it succeeds, continue normally; only treat the user as
logged out when the approved retry also fails.

- Success and an identified account: continue to verification.
- After the sandbox diagnostic above when applicable, `Not logged in`, missing credentials, or a
  non-zero authentication result: run
  `<qodo> login`. This is the only supported login path.
- An `unknown command` for `whoami` means the runtime is too old; ask the user to update it
  from the same official installer source, then stop.

`qodo login` may open a browser. Tell the user what is happening before you run it. Wait for
the command to finish; never claim login succeeded from a browser opening alone. If the
user cancels or login fails, preserve the error message, explain that Qodo is still not
connected, and stop without invoking other Qodo skills.

For a customer deployment, preserve the deployment-specific command the installer or user
provided, such as `qodo login --auth-url <their-url>`. Never replace an explicit endpoint
with cloud defaults.

## 3. Verify readiness

After login, run both:

```sh
<qodo> whoami --json --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.3 --distribution kiro-power --host kiro
```

Read the structured results. Readiness requires both a successful authenticated identity
and a usable tool catalog. A successful process launch by itself is not enough.

If catalog refresh fails while `whoami` succeeds, report that authentication is complete
but managed tools are not ready, including the returned error and the safe retry
`qodo tools --refresh`. Do not send the user through login again unless `whoami` fails.

## Configuration

Keep the first working Qodo executable path and any explicit `--auth-url` for the entire setup.
Stamp exact skill/version/distribution provenance on the first Qodo call. Marketplace or skills.sh
owns this skill package; the CLI owns login, runtime, and tool-catalog refresh.

## Error Handling

Stop on missing runtime, canceled login, failed identity, or unavailable tools and report the exact
safe next action. Never convert a browser opening, process launch, or partial catalog refresh into a
successful readiness claim.

## 4. Hand off

When both checks pass, show this once using counts from the refreshed catalog:

```
# ✅ Qodo Ready

Account: **connected**
Managed tools: **<N> available**
Runtime: **<version from qodo --version>**
---
```

Only show the ready block after both identity and catalog checks succeed. It is a verified
handoff, not a startup banner: do not show it while login is pending, after a partial setup, or
when the tool count is unknown. Then offer the shortest relevant next action:

- “Review my local changes” → `qodo-review`
- “Load our coding standards” → use `qodo-get-rules` only when it is available. Otherwise,
  explain that it belongs to the optional **Qodo Standards** add-on; install that add-on through
  the current agent marketplace, or use `qodo agents install --standards --json` to detect local
  compatible agents and print their separate exact skills.sh commands without installing anything.
- “Explain this codebase” → `qodo-codebase-wisdom`
- “Show the Qodo findings on this PR” → `qodo-review-resolver`

Do not run one of those workflows until the user asks. Setup establishes capability; it
does not infer permission to review, edit, post, or administer standards.

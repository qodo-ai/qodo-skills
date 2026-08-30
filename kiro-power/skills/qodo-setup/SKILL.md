---
name: qodo-setup
description: Connect Qodo to the current local coding agent — verify the Qodo CLI, guide a secure installation when it is missing, complete browser login, and confirm managed tools are ready. Use after installing the Qodo plugin, when the user asks to set up or connect Qodo, or when another Qodo skill reports that the CLI is missing or logged out.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.4"
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
qodo --version
```

If a POSIX shell reports `qodo: command not found`, retry the standard user-scoped location:

```sh
"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version
```

In Windows PowerShell, use the native launcher:

```powershell
$qodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Join-Path $qodoHome 'bin/qodo.cmd') --version
```

Keep the working command for every later step. Do not rewrite PATH automatically.

If neither command exists, tell the user:

> The Qodo skill is installed, but its local runtime is not. Obtain the checksum-verified Qodo CLI
> from https://get.qodo.ai or your organization's Qodo administrator, then ask me to “Set up Qodo”
> again.

Stop there. Do not invent a checksum, pipe a remote script into a shell, use a package from
an unofficial registry, or install software without the user's approval.

If an executable was found, evaluate its output before continuing. The unadorned version probe is
intentionally compatible with older Qodo CLIs. This skill requires Qodo CLI **0.1.0-next.37 or newer**.
If the version is older or cannot be parsed, do not run `whoami` or `login` and do not
describe the failure as an authentication problem. Explain that the skill is newer than the runtime,
show `<qodo> update` as the update command for the runtime's already-recorded origin, and ask once
before running it. For a customer deployment, keep its organization-provided update origin; never
switch it to the public service. After an approved update, rerun the unadorned version probe and
continue only when it satisfies the minimum. If the user declines or the update fails, stop with the
current skill and user files unchanged.

## 2. Check authentication

Run `<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.4 --distribution kiro-power --host kiro`.

In a sandboxed environment, any failed `whoami` can be a blocked keychain rather than a logged-out
user. Ask for approval to retry that exact read-only command once outside the sandbox. The approval
applies only to that diagnostic retry. If it succeeds, continue normally; only treat the user as
logged out when the approved retry also fails.

- Success and an identified account: continue to verification.
- After the sandbox diagnostic above when applicable, `Not logged in`, missing credentials, or a
  non-zero authentication result: run
  `<qodo> login`. This is the only supported login path.
- An `unknown command` or `unknown option` after the successful version gate is a runtime-contract
  failure, not an authentication failure. Report the exact error and stop; do not send the user
  through login.

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
<qodo> read whoami --json --skill qodo-setup --skill-version 1.0.4 --distribution kiro-power --host kiro
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.4 --distribution kiro-power --host kiro
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

When the host is Kiro and safe reads prompt repeatedly, explain the optional persistent rule before
the next read. The only broad pattern to offer is `<qodo> read *`: that CLI gateway rejects every
managed tool not explicitly marked non-mutating by the live catalog. Keep the version probe as its
own exact `<qodo> --version` rule. Never suggest `<qodo> *` or `<qodo> codebase *`, and never edit
Kiro permission files from the agent. The user may choose Kiro's **Always allow** action and scope,
or review the generated `qodo-read-only.permissions.yaml` supplied with the Qodo Power.

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

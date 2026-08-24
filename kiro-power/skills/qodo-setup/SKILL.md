---
name: qodo-setup
description: >-
  Connect Qodo to the current local coding agent — verify the Qodo CLI, guide a secure installation when it is missing, complete browser login, and confirm managed tools are ready. Use after installing the Qodo plugin, when the user asks to set up or connect Qodo, or when another Qodo skill reports that the CLI is missing or logged out.
metadata:
  vendor: qodo
  version: "1.0.1"
  recommended: "true"
  package: "qodo"
  distribution: "kiro-power"
---

# Set up Qodo

Turn a marketplace install into one guided first-use flow: find the local runtime,
authenticate the human through Qodo's browser login, and verify that this agent can use
the managed tools. Never ask the user to paste credentials into chat.

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

If the shell reports `qodo: command not found`, retry the standard user-scoped location:

```sh
"${QODO_HOME:-$HOME/.qodo}/bin/qodo" --version
```

Keep the working command for every later step. Do not rewrite PATH automatically.

If neither command exists, tell the user:

> The Qodo marketplace plugin is installed, but its local runtime is not. Install the
> checksum-verified Qodo CLI from https://get.qodo.ai, then ask me to “Set up Qodo” again.

Stop there. Do not invent a checksum, pipe a remote script into a shell, use a package from
an unofficial registry, or install software without the user's approval.

## 2. Check authentication

Run `<qodo> whoami --json --skill qodo-setup --skill-version 1.0.1 --distribution kiro-power`.

- Success and an identified account: continue to verification.
- `Not logged in`, missing credentials, or a non-zero authentication result: run
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
<qodo> whoami --json --skill qodo-setup --skill-version 1.0.1 --distribution kiro-power
<qodo> tools --refresh --json --skill qodo-setup --skill-version 1.0.1 --distribution kiro-power
```

Read the structured results. Readiness requires both a successful authenticated identity
and a usable tool catalog. A successful process launch by itself is not enough.

If catalog refresh fails while `whoami` succeeds, report that authentication is complete
but managed tools are not ready, including the returned error and the safe retry
`qodo tools --refresh`. Do not send the user through login again unless `whoami` fails.

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
  the current agent marketplace, or use `qodo agents install --package qodo-standards` for a
  CLI-managed direct connection.
- “Explain this codebase” → `qodo-codebase-wisdom`
- “Show the Qodo findings on this PR” → `qodo-review-resolver`

Do not run one of those workflows until the user asks. Setup establishes capability; it
does not infer permission to review, edit, post, or administer standards.

---
name: qodo-setup
description: >-
  Connect Qodo to the current local coding agent — verify the Qodo CLI, guide a secure installation when it is missing, complete browser login, and confirm managed tools are ready. Use after installing the Qodo plugin, when the user asks to set up or connect Qodo, or when another Qodo skill reports that the CLI is missing or logged out.
metadata:
  vendor: qodo
  version: "1.0.0"
  recommended: "true"
---

# Set up Qodo

Turn a marketplace install into one guided first-use flow: find the local runtime,
authenticate the human through Qodo's browser login, and verify that this agent can use
the managed tools. Never ask the user to paste credentials into chat.

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

Run `<qodo> whoami --json --skill qodo-setup`.

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
<qodo> whoami --json --skill qodo-setup
<qodo> tools --refresh --json --skill qodo-setup
```

Read the structured results. Readiness requires both a successful authenticated identity
and a usable tool catalog. A successful process launch by itself is not enough.

If catalog refresh fails while `whoami` succeeds, report that authentication is complete
but managed tools are not ready, including the returned error and the safe retry
`qodo tools --refresh`. Do not send the user through login again unless `whoami` fails.

## 4. Hand off

When both checks pass, lead with: “Qodo is connected and ready in this coding agent.” Then
offer the shortest relevant next action:

- “Review my local changes” → `qodo-review`
- “Load our coding standards” → `qodo-get-rules`
- “Explain this codebase” → `qodo-codebase-wisdom`
- “Show the Qodo findings on this PR” → `qodo-review-resolver`

Do not run one of those workflows until the user asks. Setup establishes capability; it
does not infer permission to review, edit, post, or administer standards.

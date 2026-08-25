---
name: "qodo"
displayName: "Qodo AI Code Review and Governance"
description: "AI code review inside Kiro. Catches bugs, cross-repo breakages, and standards gaps in local changes before a PR is opened, then resolves findings on PRs already in flight with fix suggestions you apply in Kiro. Shorter review cycles, fewer issues reaching main."
keywords: ["qodo rules", "get qodo rules", "qodo get rules", "get rules", "load qodo rules", "load rules", "fetch qodo rules", "activate qodo rules", "qodo coding rules", "resolve qodo pr", "qodo pr findings", "fix qodo review findings", "qodo review comments", "qodo pre-pr review", "qodo review my changes", "review local changes with qodo", "qodo codebase", "ask qodo about the code", "qodo cross-repo", "qodo understand code"]
author: "Qodo"
---

# Qodo

Use this power for Qodo developer workflows. It acts as a router: it reads the request, infers which Qodo capability applies, and loads only the steering file that capability needs.

## How Kiro Uses This Power

1. Kiro loads this `POWER.md` into the initial context window.
2. Kiro infers the user's intent from the prompt.
3. Kiro loads only the one steering file that matches that intent (never all of them). Setup/auth-only questions stay here.

## Onboarding

**Data flow at a glance** (what this power reads / sends / writes — no MCP server, no background daemon, no inbound listener):

- **All four capabilities delegate to the Qodo CLI.** get-rules, pr-resolver, and codebase-wisdom invoke only their named catalog tools after confirming `mutating: false`; pre-pr-review uses the top-level `qodo review` managed agent (not a catalog tool). The managed reads send queries or repository identifiers to Qodo. `qodo review` sends the selected repository metadata, tracked diff (excluding `.qodo/` metadata), eligible untracked patches, and supplied context to Qodo for analysis.
- **Read-only describes repository/forge effects and the named managed reads.** The catalog tools do not change Qodo rules or PR-review state; `qodo review` creates an analysis task but does not change repository or forge state. A requested fix may edit local code only after confirmation. This power never commits or pushes; it hands local changes back to the user.
- **Secrets are never printed.** The CLI holds credentials under `~/.qodo/` (written by `qodo login`); never echo, `cat`, or log that directory, tokens, or raw tool JSON. In-scope tracked changes are sent as-is; the CLI excludes `.qodo/` metadata and filters untracked files that are gitignored, secret-like, non-regular, unreadable, binary, oversized, or beyond its scan/size caps.
- The CLI may maintain its own local catalog and installed managed skills on launch, so do not describe launching `qodo` as filesystem-write-free.

### Qodo CLI (used by all four capabilities)

- The CLI requires **Node.js ≥ 20**. GUI-launched agents run shells with a minimal PATH, so `qodo` may be **`command not found`** — use **`~/.qodo/bin/qodo`** (or `$QODO_HOME/bin/qodo`) and keep using it. If that file is missing too, install with `curl -fsSL https://get.qodo.ai/install.sh | sh`.
- **Always use the `qodo` CLI for capability execution.** `qodo review` self-collects the branch, HEAD, diff, untracked files, and commit-message summary; `qodo codebase` / `pull-request` / `cross-repo` read code and history server-side; `qodo rules search` retrieves rules. Don't precede a Qodo read with `git status` / `git log` / `git diff`, and don't bypass codebase-wisdom with source-file pre-reading. The only sanctioned non-`qodo` discovery calls are one provider metadata read (`gh pr view … --json`, `glab mr view`, etc.) for a PR URL/head and one optional `git remote get-url origin` for a rules scope.
- **Authenticate first.** Each capability's first `qodo` call is `qodo whoami --json`, run without surfacing its raw output. On failure, tell the user to run `qodo login` and stop. For managed tools, inspect `qodo tools --json` internally and invoke only the named entry when `mutating: false`.
- **Stale tool catalog:** if authentication succeeds but a managed leaf is absent/unknown, run `qodo tools --refresh` once and retry discovery once. If it remains absent or is not explicitly non-mutating, stop. Refresh updates the local CLI catalog; it does not change Qodo rules, reviews, or forge state.
- Pass `--json` to anything you parse. Managed-tool errors use `{"error":{"code",…}}`; branch on `not_logged_in`, `MT-RATE-LIMITED` (back off), `MT-TOOL-LOOP` (stop, change approach), and `MT-UPSTREAM-DOWN` (wait briefly and retry once). `qodo review` also has a stable `closed_preview` error: surface its `message` and `hint` unchanged, then stop without retrying.

## When To Load Steering Files

Load only the one file that matches the request, and match the **most specific** intent. Any request to **get / load / fetch / pull / "activate" rules** is `get-rules` — never codebase-wisdom. A request to **review a diff or an existing PR** is pre-pr-review or pr-resolver. codebase-wisdom is only for **questions about how existing code works**. Do not load unrelated steering files "just in case."

- **`steering/get-rules.md`** — **any request to get, load, fetch, pull, or "activate" the Qodo rules** ("get rules", "load qodo rules", "activate get rules", "what rules apply here"), or to apply the Qodo coding rules relevant to a coding task before writing/editing/refactoring/reviewing code. "Rules" + a get/load/fetch/activate verb is **always** this file.
- **`steering/pr-resolver.md`** — read a PR/MR's Qodo review: check status and freshness, report open findings, and prepare local fixes only when explicitly requested; never commit or push.
- **`steering/pre-pr-review.md`** — review local (uncommitted/unpushed) changes before a PR exists (`qodo review`). Once a PR exists, use pr-resolver instead.
- **`steering/codebase-wisdom.md`** — understand how **existing code** works, its history, or cross-repo coupling ("how does X work", "who changed X", "what would changing X affect") — especially for repos not checked out locally or spanning repos. **Not for getting/loading Qodo rules (use get-rules)** or reviewing a diff/PR (use pre-pr-review / pr-resolver).

Setup/auth/config or CLI-install questions: stay in this `POWER.md` (see Onboarding); load no steering file.

## Multi-File Retrieval Rules

- One capability → one steering file. Do not load a second unless the user explicitly asks for two.
- pr-resolver and pre-pr-review may use codebase-wisdom's read tools to locate code while fixing — that's the same `qodo` CLI, so no separate steering file is needed.
- Load **no** steering file for setup/auth/config; use this `POWER.md` only.

## Available Steering Files

- `steering/get-rules.md` — load the most relevant Qodo coding rules via the CLI's managed `qodo rules search` (read-only; it does not modify the rule set).
- `steering/pr-resolver.md` — delegates to the non-mutating `qodo pr-review-session findings` tool (structured, provider-agnostic; local fixes are separately confirmed and handed back uncommitted).
- `steering/pre-pr-review.md` — delegates to the top-level `qodo review` managed agent (review local changes before a PR; never pushes or creates a PR).
- `steering/codebase-wisdom.md` — delegates to `qodo codebase` / `qodo pull-request` / `qodo cross-repo` read tools (cited findings; never posts to the forge).

## License and support
This power integrates with the Qodo CLI. **License: Proprietary.** Use of this power, the Qodo CLI, and Qodo services is governed by the [Qodo Terms of Use](https://www.qodo.ai/terms/).

- [Privacy Policy](https://www.qodo.ai/privacy-policy/)
- [Support](https://help.qodo.ai/hc/en-us/requests/new)

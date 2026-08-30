---
name: qodo-codebase-wisdom
description: Understand how code works, how a change was done before, and which repos are coupled — to answer a question, plan a code change, debug a regression, or scope a fix, using the qodo CLI's managed tools. Use when a task needs to understand a codebase, its history, or how its repos relate — especially for a repo you don't have checked out or work spanning repos — "how does X work", "where is X defined", "who changed X", "explain this service", "plan the change for X", "what would changing X affect", "which repos depend on X", "why did X regress / when did it break", "has this been fixed before", "how did we solve X".
owner: Qodo
metadata:
  vendor: qodo
  version: "1.1.2"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
---

# Codebase Wisdom

## Description

Use the `qodo` CLI to learn how code works, how a change was done before, and how repos
are coupled — then hand back **cited findings**. This feeds answering a question, planning
a change, debugging a regression, or scoping a fix. It reaches repos you don't have on disk
and spans repo boundaries. You drive qodo's **read** tools only; you never post to the forge.

## Prerequisites

- The Qodo CLI is installed and the user can authenticate with `qodo login`.
- The workspace exposes the required read-only Codebase, pull-request, or cross-repo tools.
- The current provider-owned Qodo skill package is loaded in this agent session.

## Instructions

Follow the detailed workflow below in order: preserve update notices, confirm the live tool
contract, resolve the repository, narrow the search, and return only evidence-backed findings.

## Handle a skill update notice

A Qodo command can emit `QODO_NOTICE <json>` to stderr while still succeeding. When
`code` is `qodo_skill_update_available`, keep the command's result and finish the current
task. Then follow the notice's `steps`: do read-only inventory first, resolve the installed
Qodo package and scope, show the exact lifecycle-owner update command or UI action, and ask
once before any mutation. If the user declines, keep the current version usable.

Never invoke a different lifecycle owner, guess a placeholder, or install an optional package
implicitly. After an approved update, ask for the host restart named by the notice; the current
session may still have the old skill loaded.

## Runtime compatibility gate

First resolve the executable using the `qodo: command not found` fallback below. Before any other
Qodo command, run `<qodo> --version` exactly as shown, with no provenance flags.
This unadorned probe is intentionally compatible with older Qodo CLIs. This skill requires Qodo
CLI **0.1.0-next.37 or newer**.

If the version is older or cannot be parsed, do not run `whoami`, `login`, or a managed tool and
do not describe the failure as an authentication problem. Explain that the skill is newer than the
runtime, show `qodo update` as the update command for the runtime's already-recorded origin, and ask
once before running it. For a customer deployment, keep its organization-provided update origin;
never switch it to the public service. After an approved update, rerun the unadorned version probe
and continue only when it satisfies the minimum. If the user declines or the update fails, stop with
the current skill and user files unchanged.

## Quick start

```
qodo --version                                             # compatibility probe — run this FIRST
qodo read whoami --json --skill qodo-codebase-wisdom --skill-version 1.1.2 --distribution skills-sh
qodo read codebase search-repos --query "payments" --json      # resolve a repo slug — do this FIRST
qodo read codebase grep --repo owner/repo --pattern "chargeCard" --json
qodo read codebase read-file --repo owner/repo --path src/pay.py --json
qodo read codebase blame --repo owner/repo --path src/pay.py --json
qodo read pull-request similar --repo owner/repo --query "retry failed charge" --json
qodo read cross-repo relations --repo owner/repo --json
qodo read tools codebase --json                           # the safe group's tools + exact flags (offline)
```

Add `--json` to anything you parse. **Before calling a tool, confirm its exact name, flags,
with `qodo read tools <group> [<tool>] --json`** (renders offline) —
the tool names below are illustrative, not guaranteed current.

**`qodo: command not found`?** That's PATH, not a missing install: GUI-launched agents (e.g.
the Claude Code desktop app) run shells with a minimal PATH. Retry with the absolute path
`~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo` if set) and keep using it for every `qodo`
command here. Only if that file is missing too is qodo actually not installed; tell the
user to obtain a checksum-pinned installer command from Qodo or their organization's
administrator. Installers are served from https://get.qodo.ai, but never invent a digest
or pipe an installer directly into a shell.

**Sandbox auth diagnostic.** In a sandboxed environment, if `qodo read whoami` fails for any reason
(including `Not logged in`), ask the user to approve one exact read-only retry of `qodo read whoami`
outside the sandbox before recommending login or refreshing tools. Keychain failures can be
reported as generic auth failures, so the sandboxed result alone is not diagnostic. That approval
applies only to this single diagnostic retry: do not reuse it, request persistent approval, or move
later Qodo commands outside the sandbox automatically. If the retry succeeds, continue with normal
per-command permission checks. If it still fails, follow the normal auth troubleshooting below.

## Preflight

1. **Auth first.** Run `qodo read whoami`. After the sandbox retry above when applicable, a non-zero
   exit → tell the user to run `qodo login`, then stop. Never guess creds. `Not logged in` /
   `No tool catalog cached` are authentication setup
   failures. If `whoami` succeeds but a group is unknown, run `qodo tools --refresh` once. If the
   CLI reports `tool_unavailable` or says Codebase tools are unavailable for the account/workspace,
   stop and explain that a workspace admin must enable access; do not send an authenticated user
   through login again or loop on refresh.
2. Resolve the repo. Named repo → `--repo owner/repo`. Inside a git repo with none named →
   omit `--repo` (autodetected from origin). Otherwise `qodo read codebase search-repos --query
   "<name>" --json` and **never guess a slug**. Multiple matches → ask the user which; zero
   matches → say so and stop, don't invent one.

## Route to a tool group

| The task needs… | Group | Representative tools (verify via `qodo read tools`) |
|---|---|---|
| **Current code** — where/what/how it works now | `qodo read codebase` | search-repos, grep, find, ls, read-file, blame, list-commits, get-commit, list-prs, get-pr, list-issues, get-issue, search-issues |
| **History / prior art** — how a change was done, a file's PR history, past review feedback | `qodo read pull-request` | stats, similar, by-file, details, patch |
| **Impact / coupling** — what a change affects, which repos depend on this | `qodo read cross-repo` | overview, relations |

Real tasks span groups — see Examples.

## Narrow, then fetch

Cheap discovery before heavy pulls: **orient** (`search-repos`; `pull-request stats` to
confirm a repo has indexed PR history; `cross-repo relations` for coupling) → **locate**
(`grep`/`find`/`blame`/`list-commits`; `pull-request similar`/`by-file`) → **read** (only
then `read-file` with `--start-line`/`--limit-lines`, `get-pr`, `pull-request details`/`patch`).

## Examples

**Q — "Where is `chargeCard()` defined?"**
`codebase grep --pattern "chargeCard"` → pick the hit → `codebase read-file --path src/pay.py
--start-line 120 --limit-lines 40`. → "`chargeCard()` is at `owner/repo` `src/pay.py:142`;
calls Stripe, last changed in PR #1523."

**Plan — "Add retry to failed charges."**
`pull-request similar --query "retry failed charge"` → PR #1401 (webhook retries) →
`pull-request details --pr-number 1401` (backoff + queue pattern) → `cross-repo relations`
(is charging coupled to other repos?) → `codebase grep --pattern "chargeCard\("` (call sites).
→ "Done before in PR #1401 (exp. backoff, max 3, dedicated queue). `chargeCard()` has 2 call
sites (`src/checkout.py:88`, `src/batch.py:210`); `cross-repo` shows no coupling beyond this
repo, so the change stays local to those two flows."

**Debug — "Why did checkout start 500ing last week?"**
`codebase list-commits --path src/checkout.py --since <date>` / `blame` → find the suspect
change → `codebase get-pr --number <n>` → name the cause with evidence.

## Deliver

Lead with one compact value block, then put code, paths, and diffs underneath it:

```
# 🧭 Qodo Codebase Insight

**Answer:** <the bottom line in plain language>
**Scope:** <repos, refs, or date range actually checked>
**Evidence:** <N cited locations, or "not found in the checked scope">
---
```

Render this once, only after the investigation has an evidence-backed answer. The Qodo header
identifies where the cross-repository evidence came from; the fields make the result auditable.
Do not show it for auth/tool failures or use it to decorate an uncertain answer.

- Keep the answer understandable to a non-engineering reader; put technical detail below it.
- **Cite everything** — repo, `path:line`, PR number, commit SHA. When a fact has no locatable
  source (a hit without a line, or a synthesis of several), say so plainly — don't invent a citation.
- **Source precedence** when sources disagree: `read-file` (current code) = how it behaves now;
  `pull-request` = how/why it got there; `cross-repo` = estimated coupling. Present state trumps history.
- **Empty or `truncated: true` → narrow once and retry** (tighter query / path / repo) before
  concluding. Still empty → report "not found in <scope>", don't overclaim.
- Freshness caveats: `pull-request` = merged PRs only (no open/draft); `cross-repo` edges may be
  `pending` (analysis running) or `not_found` (checked, no coupling).

## Configuration

Use `--json` for parsed output and stamp the exact skill/version/distribution provenance on the
first Qodo call. Tool names and schemas come from the installed CLI catalog, never from hardcoded
skill assumptions. The marketplace or skills.sh owns this skill; the CLI owns only runtime access.

## Error Handling

Preserve the returned error code and message. Treat authentication, unavailable-tool, rate-limit,
and loop-protection responses as explicit stop or recovery conditions described above; never
replace them with guessed repository facts or broader authority.

## Guardrails

- Only call managed tools through the fail-closed `qodo read` gateway. The write tools — `approve`,
  `post-comment`, `post-inline-comment(s)`, `set-labels`, `update-description` (non-exhaustive) —
  post to the forge; **don't call them** while investigating. (Editing local code as part of a
  fix is your normal work — that's not these tools.)
- Don't guess slugs, paths, PR numbers, or SHAs — resolve them first.
- Don't reason only from a local checkout when the work spans other repos; these tools reach
  what you don't have on disk.
- An `MT-TOOL-LOOP` error means stop and change approach, not retry.

A short, well-cited result is a confidence signal; padding with uncited detail is noise.

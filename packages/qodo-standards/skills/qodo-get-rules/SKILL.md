---
name: qodo-get-rules
description: Load the coding rules from Qodo most relevant to the current coding task, using the qodo CLI's managed rules search — generate structured semantic queries from the assignment, retrieve the workspace's matching rules ranked by relevance, and apply them while writing the code. Use when the user asks to write, edit, refactor, or review code, when starting implementation planning, or on "get rules", "load qodo rules", "fetch coding rules", "relevant rules", "search rules"; skip if rules are already loaded in this conversation.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.1.2"
  recommended: "false"
  package: "qodo-standards"
  distribution: "marketplace"
  instruction_mode: "embedded"
---

# Get Rules

## Description

Use the `qodo` CLI to fetch the workspace's coding rules most relevant to the task at
hand, then **apply them while producing the code**. Retrieval is semantic — the quality
of what comes back is decided by how you write the query, so follow the query format
below exactly.

## Prerequisites

- The optional Qodo Standards package is installed and loaded explicitly.
- The Qodo CLI is installed, authenticated, and exposes the read-only rules search tool.
- The task is concrete enough to form semantic queries; already-loaded rules are reused.

## Instructions

Follow the detailed workflow below: preserve update notices, verify the current tool contract,
build focused semantic queries, merge ranked results, print the Qodo rules block, then apply it.

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
qodo read whoami --json --skill qodo-get-rules --skill-version 1.1.2 --distribution marketplace --host claude-code
qodo read rules search --query "Name: JWT Authentication Endpoint Validation
Category: Security
Content: Implementing a login endpoint that validates credentials and issues JWT tokens securely" --top-k 20 --scopes "/owner/repo/" --json
qodo read tools rules --json                              # exact safe flags (renders offline)
```

The newlines inside the quoted `--query` value are literal — a multi-line double-quoted
string works as-is in POSIX sh/bash/zsh and in PowerShell. Don't use Bash-only `$'…'`
quoting. (cmd.exe can't express multi-line strings — run the command from PowerShell or
bash there.)

**`qodo: command not found`?** That's PATH, not a missing install: GUI-launched agents run
shells with a minimal PATH. Retry with the absolute path `~/.qodo/bin/qodo` (or
`$QODO_HOME/bin/qodo` if set) and keep using it. Only if that file is missing too is qodo
actually not installed; tell the user to obtain a checksum-pinned installer command from
Qodo or their organization's administrator. Installers are served from https://get.qodo.ai,
but never invent a digest or pipe an installer directly into a shell.

**Sandbox auth diagnostic.** In a sandboxed environment, if `qodo read whoami` fails for any reason
(including `Not logged in`), ask the user to approve one exact read-only retry of `qodo read whoami`
outside the sandbox before recommending login or refreshing tools. Keychain failures can be
reported as generic auth failures, so the sandboxed result alone is not diagnostic. That approval
applies only to this single diagnostic retry: do not reuse it, request persistent approval, or move
later Qodo commands outside the sandbox automatically. If the retry succeeds, continue with normal
per-command permission checks. If it still fails, follow the normal auth troubleshooting below.

## Preflight

1. **Already loaded?** If "Qodo Rules Loaded" appears earlier in this conversation, skip
   straight to applying those rules — don't re-fetch.
2. **Auth.** Run `qodo read whoami`. After the sandbox retry above when applicable, a non-zero exit →
   tell the user to run `qodo login`, then stop.
   `Not logged in` / `No tool catalog cached` → not logged in. An `unknown command` on
   `qodo rules` while `whoami` SUCCEEDS is a different failure: the cached catalog predates
   the rules tool — run `qodo tools --refresh` and retry; only ask for `qodo login` when
   `whoami` itself fails.
3. **Repository scope** (optional, improves precision). From the repo's `origin` remote,
   take the **full path after the host** and strip a `.git` suffix — `git@host:a/b` and
   `https://host/a/b` both parse to `a/b`, and a deeper hosted path survives intact
   (GitLab subgroups `group/subgroup/repo`, Azure DevOps `org/project/repo` — don't
   collapse to two segments). Wrap as `/<path>/`. If the cwd is inside a
   `modules/<name>/` subdirectory of the repo root, narrow to
   `/<path>/modules/<name>/`. No remote / unparseable → **omit `--scopes` entirely**
   (org-wide search still works); never pass an empty scopes value.

## Write the queries

Generate **two** structured queries — retrieval data shows a single topic query
systematically misses the cross-cutting standards rules that dominate real reviews.
Each query is a three-line block mirroring how rules are indexed:

```
Name: <concise 5-10 word title of the rule this task would trigger>
Category: <one of: Security, Correctness, Quality, Reliability, Performance, Testability, Compliance, Accessibility, Observability, Architecture>
Content: <1-2 sentences describing what should be checked or enforced; mention the tech stack when known>
```

- **Topic query** — the assignment's primary concern. Pick the category by the change's
  *purpose*, not a side effect (rate limiting → Reliability, not Security); prefer Security
  when it's genuinely a candidate; don't default everything to Correctness — structural
  work is Architecture, style is Quality, fault tolerance is Reliability, instrumentation
  is Observability.
- **Cross-cutting query** — the standards the org applies to *all* changes. Default:
  `Name: Code Quality and Standards Compliance / Category: Architecture / Content: Module
  directory structure, type annotations or type safety, structured logging, repository or
  service layer patterns, dependency injection, and naming conventions` — adjust Content
  to the repo's stack.
- **Never** pass keyword lists, flat sentences, or filler ("please", "I need to") — they
  retrieve poorly against the structured index.

## Search and merge

Run `qodo read rules search` **once per query** (in parallel when you can), each with
`--top-k 20` and `--json`. Add `--scopes "$SCOPE"` only when detection produced a scope:

```
# With a detected scope:
qodo read rules search --query "$TOPIC_QUERY" --top-k 20 --scopes "$SCOPE" --json
qodo read rules search --query "$CROSS_QUERY" --top-k 20 --scopes "$SCOPE" --json

# Without a detected scope, omit both the flag and its value:
qodo read rules search --query "$TOPIC_QUERY" --top-k 20 --json
qodo read rules search --query "$CROSS_QUERY" --top-k 20 --json
```

Merge: topic results first (in order), then cross-cutting results not already present —
dedup by rule `id`. Topic rules are task-specific guidance; treat cross-cutting rules as
supplementary and deprioritize any that are semantically distant from the task.
**Low-return fallback:** topic query returns < 3 rules → re-run it once with a broadened
Content line (add adjacent concepts for the domain: e.g. auth → token validation,
credential handling, session management) before merging. An **empty merged list is a valid
outcome** — proceed without rule constraints, never treat it as an error.
**Unscoped search caveat:** when you had to omit `--scopes`, the results are org-wide —
before applying each rule, check it plausibly applies to THIS repo/stack (a rule naming a
different service, language, or framework doesn't); skip mismatches and say so rather than
imposing another repo's standards.

## Output, then apply

Print the loaded rules before writing code:

```
# 📋 Qodo Rules Loaded

Rules loaded: **<N>** (ranked by relevance to your task)

- **<name>** [<SEVERITY if present>]: <content>
...
---
```

(Empty result: "No relevant rules found for this task. Proceeding without rule
constraints.") Then apply every returned rule to the code you produce. When a rule
carries a severity:

| Severity | Enforcement |
|---|---|
| **ERROR** | Must comply — non-negotiable; if you must deviate, stop and ask the user |
| **WARNING** | Comply by default; briefly explain any deliberate skip in your response |
| **RECOMMENDATION** | Apply when appropriate; mention only if it shaped a design decision |

After the code is written, report which rules were applied and which WARNING rules were
skipped and why. If none applied, say "No Qodo rules were applicable to this code change."

## Configuration

Use `--json`, the exact scopes relevant to the task, and the current CLI-provided rules schema.
Stamp the skill/version/distribution provenance on the first Qodo call. This optional skill is
never installed or updated implicitly with the default Qodo package.

## Error Handling

An empty result is valid. Preserve authentication, capability, validation, and rate-limit errors;
follow the bounded recovery above and continue without invented rules when retrieval cannot
safely succeed.

## Guardrails

- `rules search` is read-only; it never changes workspace state.
- Don't re-fetch when rules are already loaded; don't crash on an empty list.
- A rate-limit error (the search is capped per organisation) → wait for the indicated
  reset, or proceed without rules and say so — don't hammer retries.
- Don't fabricate rules: apply exactly what came back, cite rules by their returned name.

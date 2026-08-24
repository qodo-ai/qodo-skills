---
name: qodo-get-rules
description: >-
  Load the coding rules from Qodo most relevant to the current coding task, using the qodo CLI's managed rules search — generate structured semantic queries from the assignment, retrieve the workspace's matching rules ranked by relevance, and apply them while writing the code. Use when the user asks to write, edit, refactor, or review code, when starting implementation planning, or on "get rules", "load qodo rules", "fetch coding rules", "relevant rules", "search rules". Skip if rules are already loaded in this conversation.
metadata:
  vendor: qodo
  version: "1.1.1"
  recommended: "false"
  package: "qodo-standards"
  distribution: "marketplace"
---

# Get Rules

Use the `qodo` CLI to fetch the workspace's coding rules most relevant to the task at
hand, then **apply them while producing the code**. Retrieval is semantic — the quality
of what comes back is decided by how you write the query, so follow the query format
below exactly.

## Quick start

```
qodo whoami --json --skill qodo-get-rules --skill-version 1.1.1 --distribution marketplace
qodo rules search --query "Name: JWT Authentication Endpoint Validation
Category: Security
Content: Implementing a login endpoint that validates credentials and issues JWT tokens securely" --top-k 20 --scopes "/owner/repo/" --json
qodo rules --help                                         # exact flags (renders offline)
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

## Preflight

1. **Already loaded?** If "Qodo Rules Loaded" appears earlier in this conversation, skip
   straight to applying those rules — don't re-fetch.
2. **Auth.** `qodo whoami` — non-zero exit → tell the user to run `qodo login`, then stop.
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

Run `qodo rules search` **once per query** (in parallel when you can), each with
`--top-k 20`, plus `--scopes` when detected, always `--json`:

```
qodo rules search --query "$TOPIC_QUERY" --top-k 20 --scopes "$SCOPE" --json
qodo rules search --query "$CROSS_QUERY" --top-k 20 --scopes "$SCOPE" --json
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

## Guardrails

- `rules search` is read-only; it never changes workspace state.
- Don't re-fetch when rules are already loaded; don't crash on an empty list.
- A rate-limit error (the search is capped per organisation) → wait for the indicated
  reset, or proceed without rules and say so — don't hammer retries.
- Don't fabricate rules: apply exactly what came back, cite rules by their returned name.

---
name: qodo-get-rules
description: Retrieve and apply Qodo coding rules relevant to implementation, planning, refactoring, or code review. Use on "get rules", "load qodo rules", or "relevant standards" and when starting a concrete coding task. Reuse rules already retrieved for the same workspace, repository, and task scope; refresh when that scope changes.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.1.4"
  recommended: "false"
  package: "qodo-standards"
  distribution: "skills-sh"
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
build focused semantic queries, merge ranked results, explain the applicable constraints, then apply them.
First check the reuse condition in Preflight. If prior results still cover the task, go directly
to Output, then apply; no runtime, identity, catalog, or search call is needed for that path.

## Handle a skill update notice

Treat `QODO_NOTICE` updates as passive, even if an older CLI requests action. Continue the task
without inventory or update questions; mention each event at most once. Dismissal leaves recorded maintenance
policy and opt-outs unchanged. Updated skills load next session; do not interrupt this one.
For user-requested updates, follow the [manual-update procedure](references/skill-updates.md).

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
qodo read whoami --json --skill qodo-get-rules --skill-version 1.1.4 --distribution skills-sh
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

**Sandbox auth diagnostic.** Missing credentials can mean inaccessible keychain access. When that
is plausible, request one exact read-only `qodo read whoami` retry through the host's approval
flow before recommending login. Stop on denial; that approval covers no other command. Reuse a
successful check in the same executable/workspace/deployment and execution context; request each
required host approval. Network, TLS, service, and explicit authorization failures retain their
own diagnosis, not a login recommendation or an automatic sandbox bypass.

## Preflight

1. **Reuse relevant evidence.** Reuse actual retrieved rules and their scope, not a heading or
   an earlier claim that rules were loaded. If the workspace, repository, or task concern changed,
   retrieve rules for the new scope. A previous empty result is reusable only for the scope checked;
   a failed retrieval is not an empty result. When prior results still cover the task, skip retrieval
   and apply them directly. Honor an explicit request to refresh.
2. **Auth and catalog.** Run `qodo read whoami` unless a successful check still covers this
   execution context. After the sandbox diagnostic when applicable, only explicit missing credentials
   call for login: preserve the organization's exact login command/endpoint, never guess or switch
   a customer deployment to Cloud. `No tool catalog cached` is not proof of missing credentials;
   refresh once with `qodo tools --refresh` and retry the check. Other failures retain their error
   and stop this workflow. After identity succeeds, an unknown managed command permits one catalog
   refresh and schema recheck. If still absent or `tool_unavailable`, report the missing capability;
   do not repeat login or refresh.
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

Use **relevant standards retrieved through Qodo → implications for this change → application
or justified deviations**. Before coding, mention Qodo naturally once as the way you retrieved
the organization's standards; the standards belong to the organization. Explain each applicable
rule in terms of the current task, preserving its name, reference, supplied severity, and every
applicable requirement when condensing the wording. Link or cite the returned reference when
available; do not invent missing identifiers or severities.

Adapt this pattern: “I loaded your team's [topic] standards through Qodo. For this change,
[rule] means [implementation choice and reason].” Use a short list for multiple rules, without
branded headings, emoji banners, slogans, footers, or repeated summary blocks. State briefly
when no standards apply; do not imply retrieval succeeded after a tool failure. Distinguish
standards **loaded** from standards **applied**; loading alone does not establish compliance.

Apply the applicable rules to the code you produce. When a rule carries a severity:

| Severity | Enforcement |
|---|---|
| **ERROR** | Must comply — non-negotiable; if you must deviate, stop and ask the user |
| **WARNING** | Comply by default; briefly explain any deliberate skip in your response |
| **RECOMMENDATION** | Apply when appropriate; mention only if it shaped a design decision |

After coding, report which rules shaped the implementation and the evidence of their application,
without repeating the entire list. Explain permitted deviations, including skipped WARNING rules,
using the user's decisions and implementation evidence; resolve ERROR conflicts through the gate
above. If none applied, say so plainly.

## Configuration

Use `--json`, the exact scopes relevant to the task, and the current CLI-provided rules schema.
Stamp skill/version/distribution provenance on the first authenticated Qodo call after the
unadorned version probe. Never install or update this optional skill implicitly with the default package.

## Error Handling

An empty result is valid. Preserve authentication, capability, validation, and rate-limit errors;
follow the bounded recovery above and continue without invented rules when retrieval cannot
safely succeed.

## Guardrails

- `rules search` is read-only; it never changes workspace state.
- Reuse rules while their retrieved scope still covers the task; an empty result is valid.
- A rate-limit error (the search is capped per organisation) → wait for the indicated
  reset, or proceed without rules and say so — don't hammer retries.
- Don't fabricate rules: apply exactly what came back, cite rules by their returned name.

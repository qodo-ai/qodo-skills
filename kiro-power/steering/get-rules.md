# Qodo Get Rules

Load this steering file when the user wants the Qodo coding rules most relevant to the current coding task — "get rules", "load qodo rules", "fetch coding rules", "what rules apply here" — before writing, editing, refactoring, or reviewing code.

This delegates to the **Qodo CLI** managed rules tool (`qodo rules search`), which runs a **semantic** search over the workspace's rule set and returns the matching rules ranked by relevance. Retrieval quality is decided by how you write the query, so follow the query format below exactly. `qodo rules search` is **read-only** — it never changes the rule set (creating or editing rules is a separate admin capability, not this one).

**Skip this whole workflow** if "Qodo Rules Loaded" already appears in the conversation for the same repository scope and a similar task — don't re-fetch.

## UX and Safety Rules

- Run the `qodo` CLI; don't build your own API calls. After the shared authentication/catalog checks, the fetch is just the `qodo rules search` calls — no extra commands to print git state, config, or request IDs.
- **Read-only.** `qodo rules search` never mutates the workspace. Never try to "fix" or edit rules from this capability.
- This capability only retrieves and presents rules. Applying them through code edits belongs to a separately authorized coding task.
- No raw JSON dumps and **no secrets** — never print `~/.qodo/` contents, tokens, or the raw tool JSON. Present the scannable summary described in Step 5.
- An **empty result is valid** — proceed without rule constraints; never present it as an error or an auth failure.
- Rate-limit (`MT-RATE-LIMITED`, the search is capped per organization) → wait for the reset or proceed without rules and say so; don't hammer retries.

## Locate the CLI + auth

The CLI requires **Node.js ≥ 20**. `qodo` may be "command not found" (GUI shells have a minimal PATH) — use `~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo`); missing there too → install `curl -fsSL https://get.qodo.ai/install.sh | sh`. See `POWER.md` → Onboarding.

Run `qodo whoami --json` first without surfacing its raw output. If it fails, tell the user to run `qodo login` and stop. Then inspect `qodo tools --json` internally and require the catalog entry `name: "rules-search"`, `toolset: "rules"`, `mutating: false` before invoking it.

- If authentication succeeds but the catalog is missing/corrupt or `rules-search` is absent, run `qodo tools --refresh` once and retry discovery once.
- If the entry remains absent or is not explicitly `mutating: false`, stop. Invoke only `qodo rules search`; never call mutating siblings such as `create`, `update`, `bulk`, `set-state`, or `set-scope`.

## Workflow

### Step 1 — Already loaded?

If "Qodo Rules Loaded" appears earlier in this conversation **for the same repository scope and a similar task**, skip fetching and apply those rules. Re-fetch only if the current task targets a materially different area or scope.

### Step 2 — Detect repository scope (optional, improves precision)

From the repo's `origin` remote, take the **full path after the host** and strip a `.git` suffix — `git@host:org/repo` and `https://host/org/repo` both give `org/repo`; keep deeper hosted paths intact (GitLab subgroups `group/subgroup/repo`, Azure DevOps `org/project/repo` — don't collapse to two segments). Wrap it as `/<path>/`. If the cwd is inside a `modules/<name>/` subdirectory of the repo root, narrow to `/<path>/modules/<name>/`.

Scope is optional, and this single `git remote get-url origin` read is the **only** `git` this capability uses — don't run any other `git` commands around it. No `origin` remote, an unparseable URL, any extraction failure, or if you'd simply rather not shell out to git → **omit `--scopes` entirely** (org-wide search still works). Never pass an empty scope value.

### Step 3 — Write two structured queries

Generate **two** queries — retrieval data shows a single topic query systematically misses the cross-cutting standards rules that dominate real reviews. Each query is a three-line block mirroring how rules are indexed:

```
Name: <concise 5-10 word title of the rule this task would trigger>
Category: <one of: Security, Correctness, Quality, Reliability, Performance, Testability, Compliance, Accessibility, Observability, Architecture>
Content: <1-2 sentences describing what should be checked or enforced; mention the tech stack when known>
```

- **Topic query** — the assignment's primary concern. Pick the Category by the change's *purpose*, not a side effect (rate limiting → Reliability, not Security); prefer Security when it's genuinely a candidate; don't default everything to Correctness.
- **Cross-cutting query** — the standards the org applies to *all* changes. Default template: `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module directory structure, type annotations or type safety, structured logging, repository or service layer patterns, dependency injection, and naming conventions` — adjust Content to the repo's stack.
- **Never** pass keyword lists, flat sentences, or filler ("please", "I need to") — they retrieve poorly against the structured index.

See [Query Generation Guidelines](#query-generation-guidelines) below for the full strategy, category selection, and worked examples.

### Step 4 — Search and merge

Run `qodo rules search` **once per query** (in parallel when you can), each with `--top-k 20`, plus `--scopes` when a scope was detected, always `--json`:

```
qodo rules search --query "$TOPIC_QUERY" --top-k 20 --scopes "$SCOPE" --json
qodo rules search --query "$CROSS_QUERY"  --top-k 20 --scopes "$SCOPE" --json
```

The newlines inside the quoted `--query` value are literal — a multi-line double-quoted string works as-is in POSIX sh/bash/zsh and in PowerShell; don't use Bash-only `$'…'` quoting. When no scope was detected, drop the `--scopes` argument entirely (don't pass `--scopes ""`). Confirm exact flags with `qodo rules search --help` (the group-level help only lists leaves); `--json` is global and is documented by `qodo --help`.

- **Merge:** topic results first (in relevance order), then cross-cutting results not already present — **dedup by rule `id`**. Treat cross-cutting rules as supplementary; deprioritize any that are semantically distant from the task.
- **Scoped→unscoped fallback:** if a scoped search returns no rules, re-run the two calls once **without** `--scopes` before reporting empty, and note the fallback in the scope line.
- **Low-return fallback (model judgment, not automatic):** if the topic query returns fewer than 3 rules, re-run it once with a broadened Content line (adjacent concepts from the table in Query Generation Guidelines) before merging. Don't force it — a small, highly relevant set beats a broad, noisy one.
- **Unscoped caveat:** when you omitted `--scopes`, results are org-wide — before applying each rule, check it plausibly applies to THIS repo/stack (a rule naming a different service, language, or framework may not); skip mismatches and say so rather than imposing another repo's standards.

### Step 5 — Present the rules

The tool output is the raw rule list. Present it back as a compact, **scannable summary** — don't echo raw JSON:

- Lead with a `📋 Qodo Rules Loaded` header, then one line with **how many** rules and the **scope** — e.g., "Loaded **16** rules for `org/repo`", and say "org-wide defaults" when the scope fell back to org-wide.
- Group the rules under a few short **bold theme headers** inferred from their content (e.g., *Code Quality*, *Architecture & Patterns*, *Error Handling & Logging*, *Testing*, *Security*, *Safety & Operations*) — use only the themes that apply.
- One concise bullet per rule (a short paraphrase of its intent). **Represent every returned rule**; merge only genuine duplicates and keep the count honest.
- Close with a brief line offering to apply the rules as the user works.

This summary is for readability only. When you actually generate or review code, apply the **full rule text from the fetched list** (still in context), not the shortened bullet.

**Empty result** — when the merged list is empty (including after the unscoped fallback), don't crash. Output:

```
# 📋 Qodo Rules Loaded

No relevant rules found for this task. This is a valid result; your organization may not have configured rules for this task or scope yet. Rules are created and scoped in the Qodo portal: https://docs.qodo.ai/governance/governance-management. Proceeding without rule constraints; continue with your task as usual.

---
```

### Step 6 — Apply by severity

Apply all returned rules to the coding task; they are ranked by relevance. **When a rule includes a `severity`**, apply it by tier:

| Severity | Enforcement | When skipped |
|---|---|---|
| **ERROR** | Must comply in a separately authorized coding task. Do not add a source comment solely to prove compliance; report which rule shaped the change. | Stop and ask the user for guidance. |
| **WARNING** | Comply by default. | Briefly explain the deliberate skip in your response. |
| **RECOMMENDATION** | Apply when appropriate. | No action needed. |

**When `severity` is absent** (common — the tool may return only `id`/`name`/`content`), treat every returned rule as advisory guidance: apply the most relevant ones and note which informed the work. **Never fabricate a severity.**

### Step 7 — Report

After a separately authorized coding task, tell the user: which **rules were applied** (with severity if any); which **WARNING rules were skipped** and why; **RECOMMENDATION** rules only if they shaped a design decision. During retrieval-only use, stop after presenting the rules. If none applied, say "No Qodo rules were applicable to this code change."

---

## Query Generation Guidelines

The query is the most important input to `qodo rules search`. A well-formed query retrieves rules that genuinely apply; a generic query returns noise.

### Strategy

Retrieval is **embedding-based** — every rule is indexed as a vector of:

```
Name: {rule name}
Category: {rule category}
Content: {rule content}
```

To maximize semantic alignment, the query must mirror this exact structure — aligning on **all three dimensions** rather than collapsing the signal into one sentence.

### Field guidelines

- **Name**: think "what rule would apply here?" — a concise 5-10 word title of the rule this assignment would trigger.
- **Category**: choose the single most relevant value:
  - `Security` — authentication, authorization, injection, secrets, encryption, token validation, access control, privilege escalation, CSRF, XSS
  - `Correctness` — logic errors, null handling, off-by-one, type safety, incorrect computation, missing guard, data corruption
  - `Quality` — code style, naming, readability, maintainability, dead code, duplication, magic numbers, overly complex logic
  - `Reliability` — error handling, retries, graceful degradation, timeouts, circuit breakers, fault tolerance, idempotency, recovery
  - `Performance` — latency, caching, memory, query optimization, batching, N+1 queries, connection pooling, scalability
  - `Testability` — test coverage, mocking, test structure, assertions, test isolation, fixtures
  - `Compliance` — licensing, regulatory, data retention, audit trails, GDPR, PII handling, policy enforcement
  - `Accessibility` — WCAG, ARIA, screen readers, keyboard navigation, color contrast, focus management, semantic HTML
  - `Observability` — logging, metrics, tracing, alerting, monitoring, instrumentation, log levels, error reporting
  - `Architecture` — layering, coupling, module boundaries, API design, dependency direction, separation of concerns, domain modeling

  **Tie-breaking:** when an assignment spans categories, prefer `Security` if it's a candidate. Otherwise pick the category describing the primary *purpose* of the change, not a secondary effect (e.g. "add rate limiting" is `Reliability`, not `Security`). The cross-cutting query covers the other dimensions.

  **Avoid over-using Correctness:** before choosing it, consider a more specific category — structural work → `Architecture`; style/naming → `Quality`; fault tolerance → `Reliability`; instrumentation → `Observability`; speed → `Performance`. Use `Correctness` only for genuine logic/type/computation concerns.
- **Content**: 1-2 sentences (aim for 15+ words) describing what specifically should be checked or enforced. Mention the tech stack when the repository context is known — it helps the model align with rules referencing specific technologies.

  **Broadening Content for weak domains:** when a topic query returns fewer than 3 rules, expand Content with semantically adjacent concepts:

  | Domain | Adjacent concepts to include |
  |---|---|
  | Auth / JWT / OAuth | token validation, credential handling, session management, authorization headers, access control |
  | Async / concurrency | event loop, task management, concurrent execution, thread safety, resource cleanup |
  | Rate limiting / throttling | request quotas, backpressure, abuse prevention, middleware, circuit breaking |
  | Data migration | schema changes, rollback safety, backward compatibility, data integrity |
  | Frontend form validation | input sanitization, client-side validation, accessibility requirements, error state handling |
  | Database access patterns | query optimization, connection management, transaction handling, ORM conventions |

### Query format

Write each query as a **structured three-line block** matching the rule embedding format:

```
Name: {concise title of the rule this assignment would trigger}
Category: {most relevant category value}
Content: {what specifically should be checked or enforced for this assignment}
```

- **Do not** write keyword-style queries (`authentication login JWT token Python`).
- **Do not** write flat natural-language sentences — mirror the indexed structure.
- **Do not** include filler ("please", "I need to") that dilutes the semantic signal.

### Multi-query strategy

Generate **two** queries per assignment:

1. **Topic query** — focused on the assignment's primary concern.
2. **Cross-cutting query** — the recurring quality/standards rules that apply to most changes regardless of topic.

**Why two?** Evaluation data shows cross-cutting rules (module structure, structured logging, type annotations, repository pattern) account for 60%+ of rules flagged in real reviews. A single topic-focused query systematically misses these because they're semantically distant from the change's specific subject.

**Cross-cutting Category** (by the org's emphasis, when known): code structure/layering → `Architecture`; security applied everywhere → `Security`; mandatory audit/compliance → `Compliance`; observability standards → `Observability`; unknown → default `Architecture`.

**Cross-cutting default template:**

```
Name: Code Quality and Standards Compliance
Category: Architecture
Content: Module directory structure, type annotations or type safety, structured logging, repository or service layer patterns, dependency injection, and naming conventions
```

### Examples

| Coding assignment | Topic query | Cross-cutting query |
|---|---|---|
| Add a login endpoint that validates credentials and returns a JWT | `Name: JWT Authentication Endpoint Validation` / `Category: Security` / `Content: Implementing a login endpoint that validates user credentials against the database and issues JWT tokens securely` | `Name: Code Quality and Security Standards` / `Category: Security` / `Content: Token validation, credential handling, secure session management, input sanitization, and access control applied broadly across all endpoints` |
| Refactor the user service to use async/await instead of callbacks | `Name: Async Await Migration Pattern` / `Category: Quality` / `Content: Refactoring a service layer from callback-based concurrency to async/await, ensuring correct error propagation and resource cleanup` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module directory structure, type annotations or type safety, structured logging, repository or service layer patterns, dependency injection, and naming conventions` |
| Fix a SQL injection vulnerability in the search query builder | `Name: SQL Injection Prevention` / `Category: Security` / `Content: Sanitizing user input in the database query builder to prevent SQL injection through parameterized queries` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module directory structure, type annotations, structured logging, repository or service layer patterns, dependency injection, and naming conventions` |
| Add unit tests for the payment processing module | `Name: Payment Processing Test Coverage` / `Category: Testability` / `Content: Adding unit tests for the payment processing module with mocked external payment gateway services` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module structure, type annotations, structured logging, repository or service layer patterns, dependency injection, and naming conventions` |
| Implement a rate limiter middleware for the API | `Name: Rate Limiting Enforcement` / `Category: Reliability` / `Content: Implementing rate limiting middleware to throttle HTTP API requests and protect against abuse` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module structure, type annotations, structured logging, repository or service layer patterns, dependency injection, and naming conventions` |
| Add ARIA labels to the navigation menu _(TypeScript React)_ | `Name: Navigation Accessibility Labels` / `Category: Accessibility` / `Content: Adding ARIA attributes and roles to the navigation menu for screen reader compatibility and keyboard navigation` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: React component structure, TypeScript strict type checking, consistent naming, proper prop typing, and component test coverage` |
| Add a GDPR data deletion endpoint _(Java Spring)_ | `Name: GDPR Data Deletion Compliance` / `Category: Compliance` / `Content: Implementing a data deletion endpoint that enforces retention policies, logs audit trails, and handles PII per GDPR` | `Name: Code Quality and Compliance Standards` / `Category: Compliance` / `Content: Data retention enforcement, audit trail logging, PII handling, Spring service layer conventions, and exception handling standards` |
| Optimize the dashboard query that takes 5 seconds to load | `Name: Database Query Performance Optimization` / `Category: Performance` / `Content: Optimizing slow database queries for the dashboard through indexing, query restructuring, or caching` | `Name: Code Quality and Standards Compliance` / `Category: Architecture` / `Content: Module structure, type annotations, structured logging, repository or service layer patterns, dependency injection, and naming conventions` |
| Add structured logging to the payment pipeline _(Go microservice)_ | `Name: Structured Logging Implementation` / `Category: Observability` / `Content: Adding structured logging with contextual fields and appropriate log levels to the payment processing pipeline` | `Name: Code Quality and Architecture Standards` / `Category: Architecture` / `Content: Go package structure, interface-based dependency injection, structured logging with contextual fields, error wrapping, and consistent handler patterns` |

### Short or ambiguous assignments

If the assignment is very short or ambiguous ("fix the bug"), use the assignment text as the **Name**, pick the closest Category (default `Correctness` when truly ambiguous — the cross-cutting query already covers Architecture, so a different topic category maximizes diversity), and write a brief Content line restating the assignment in 15+ words. Still generate the cross-cutting query. A short structured query beats an invented one.

---

## Common Mistakes

- **Re-running when rules are loaded** — check for "Qodo Rules Loaded" in context first.
- **Wrong query format** — use the structured Name/Category/Content format, not keyword lists or flat sentences.
- **Single query only** — always generate both a topic and a cross-cutting query.
- **Vague query** — the query must capture the nature of the task; a generic Name or Content returns irrelevant rules.
- **Crashing on empty results** — an empty rule list is valid; proceed without constraints.
- **Manual scoped retry** — if a scoped search returns zero rules, do the unscoped fallback yourself; don't ask the user to rerun.
- **Treating a stale catalog as a login failure** — `unknown command` on `rules` while `qodo whoami` succeeds means run `qodo tools --refresh`, not `qodo login`.
- **Debugging in public** — never print `~/.qodo/` contents, tokens, or raw tool JSON in normal operation.
- **Fabricating rules or severities** — apply exactly what came back; cite rules by their returned name.

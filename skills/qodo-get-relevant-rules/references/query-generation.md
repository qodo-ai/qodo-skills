# Query Generation Guidelines

The search query is the most important input to the `/rules/search` endpoint. A well-formed query retrieves rules that are genuinely applicable to the task; a generic query returns irrelevant or noisy rules.

## Strategy

The search uses **embedding-based retrieval** where every rule is indexed as a vector of:

```
Name: {rule name}
Category: {rule category}
Content: {rule content}
```

To maximize semantic alignment between the query and the stored rule vectors, the search query must mirror this exact structure. A structured query aligns on **all three dimensions** (name, category, content) rather than collapsing the signal into a single sentence.

### Field guidelines

- **Name**: Think of it as "what rule would apply here?" Write a concise 5-10 word title describing the rule this coding assignment would trigger.
- **Category**: Choose the single most relevant category from the available values:
  - `Security` — authentication, authorization, injection, secrets, encryption, token validation, access control, privilege escalation, CSRF, XSS
  - `Correctness` — logic errors, null handling, off-by-one, type safety, incorrect computation, wrong conditional, missing guard, data corruption
  - `Quality` — code style, naming, readability, maintainability, dead code, code duplication, comment quality, magic numbers, overly complex logic, formatting
  - `Reliability` — error handling, retries, graceful degradation, timeouts, circuit breakers, fault tolerance, service availability, idempotency, recovery
  - `Performance` — latency, caching, memory, query optimization, batching, N+1 queries, connection pooling, unnecessary computation, scalability
  - `Testability` — test coverage, mocking, test structure, assertions, test isolation, test data, parameterized tests, fixture management
  - `Compliance` — licensing, regulatory, data retention, audit trails, GDPR, PII handling, data classification, policy enforcement
  - `Accessibility` — WCAG, ARIA, screen readers, keyboard navigation, color contrast, focus management, semantic HTML
  - `Observability` — logging, metrics, tracing, alerting, monitoring, instrumentation, dashboards, distributed tracing, log levels, error reporting
  - `Architecture` — layering, coupling, module boundaries, API design, dependency direction, separation of concerns, package structure, interface design, service decomposition, domain modeling

  **Tie-breaking:** When an assignment spans multiple categories, prefer `Security` if security is one of the candidates (security rules have the highest impact if missed). Otherwise prefer the category that describes the primary *purpose* of the change, not a secondary effect. For example, "add rate limiting" is primarily `Reliability` (protecting availability), not `Security`, even though it has security benefits. The cross-cutting query will cover the other dimensions.

  **Avoiding over-use of Correctness:** The heuristic classifier defaults to `Correctness` for a disproportionate share of tasks. Before selecting `Correctness`, consider whether a more specific category better describes the primary purpose:
  - Structural changes (new modules, refactors, layer reorganization) → prefer `Architecture`
  - Code style, naming, or readability improvements → prefer `Quality`
  - Availability, fault tolerance, or error recovery work → prefer `Reliability`
  - Instrumentation, logging, or monitoring additions → prefer `Observability`
  - Speed or resource efficiency improvements → prefer `Performance`

  Use `Correctness` when the task is genuinely about fixing a logic error, ensuring type safety, or preventing incorrect computation — not as a generic catch-all. If LLM-based classification is available, prefer it over keyword heuristics for ambiguous cases.
- **Content**: 1-2 sentences (aim for at least 15 words) describing what specifically should be checked or enforced for this coding assignment. When the coding assignment is in a known repository with established patterns (e.g., Python modulith, FastAPI service, SQLAlchemy ORM), mention the relevant tech stack in the Content field -- this helps the embedding model align with rules that reference specific technologies. Even for ambiguous assignments, expand the Content with general concerns (e.g., error handling, input validation) to provide enough semantic signal.

  **Broadening Content for weak domains:** Certain domains have sparser rule coverage. When the assignment involves one of these areas, expand the Content field with the adjacent concepts listed below to improve retrieval:

  | Domain | Include adjacent concepts |
  |---|---|
  | Auth / JWT | authorization headers, token storage, session management, credential handling |
  | Async / await | event loop, coroutine, asyncio, concurrent execution, task management |
  | Rate limiting | throttling, request quotas, API abuse prevention, middleware |

  The goal is to give the embedding model a richer surface to align against — not to make the query generic, but to ensure that closely related rules are surfaced even when the exact terminology differs.

## Query Format

Write the query as a **structured three-line block** matching the rule embedding format:

```
Name: {concise title of the rule this coding assignment would trigger}
Category: {most relevant RuleCategory value}
Content: {what specifically should be checked or enforced for this assignment}
```

**Do not** write keyword-style queries (e.g., `authentication login JWT token Python`).

**Do not** write flat natural language sentences. The embedding model aligns better when the query mirrors the indexed structure.

**Do not** include filler words like "please", "I need to", or other padding that dilutes the semantic signal.

## Multi-Query Strategy

Generate **two queries** per coding assignment for best coverage:

1. **Topic query** -- a structured query focused on the assignment's primary concern (the standard approach described above).
2. **Cross-cutting query** -- a supplementary query targeting common architectural and code quality patterns that apply to most code changes regardless of topic.

**Why two queries?** Evaluation data shows that cross-cutting rules (module structure, structured logging, type annotations, repository pattern) account for 60%+ of rules flagged in real code reviews. A single topic-focused query systematically misses these because they are semantically distant from the PR's specific subject.

**Cross-cutting query template:**

```
Name: Code Quality and Architecture Compliance
Category: Architecture
Content: Module directory structure, type annotations, structured logging, repository pattern, dependency injection, and model standardization
```

Adjust the Content field to reflect the repository's tech stack when known. For example, in a Python FastAPI project:

```
Name: Code Quality and Architecture Compliance
Category: Architecture
Content: Python modulith module directory structure, full type hints on function signatures, structured logging with contextual extra arguments, SQLAlchemy repository pattern, and dependency injection
```

Call the search endpoint **once per query** (each with `top_k=20`) and merge the results, deduplicating by rule ID.

**Low-return fallback:** If the topic query returns fewer than 3 rules, do not silently accept the sparse result. Re-generate the topic query with a broader Content field by including adjacent concepts for the domain (see the "Broadening Content for weak domains" table above). Then call the endpoint again with the broadened query before merging with cross-cutting results.

**Cross-cutting false positives:** The cross-cutting query intentionally casts a wide net. A small number of rules (e.g., broad architecture rules) will surface in almost every cross-cutting query regardless of topic. This is expected behavior. When consuming results, focus on the topic query rules for task-specific guidance; use cross-cutting results as supplementary context rather than the primary signal.

**JS/TypeScript cross-contamination (known platform issue):** Rules authored for JavaScript or TypeScript may appear in query results for Python or other language workloads. This is a known seeding concern in the platform's rule index and is not something the skill can correct at query time. If JS/TS rules surface in a non-JS context, treat them as non-applicable and skip them. The platform team is tracking the fix on the seeding side.

## Examples

| Coding Assignment | Topic Query | Cross-Cutting Query |
|---|---|---|
| Add a login endpoint that accepts username and password, validates credentials, and returns a JWT token | `Name: JWT Authentication Endpoint Validation`<br>`Category: Security`<br>`Content: Implementing a login endpoint that validates user credentials against the database and issues JWT tokens securely` | `Name: Code Quality and Architecture Compliance`<br>`Category: Architecture`<br>`Content: Python modulith module directory structure, full type hints on function signatures, structured logging with contextual extra arguments, SQLAlchemy repository pattern, and dependency injection` |
| Refactor the user service to use async/await instead of callbacks | `Name: Async Await Migration Pattern`<br>`Category: Quality`<br>`Content: Refactoring a service layer from callback-based concurrency to async/await, ensuring correct error propagation and resource cleanup` | _(use default template)_ |
| Fix a SQL injection vulnerability in the search query builder | `Name: SQL Injection Prevention`<br>`Category: Security`<br>`Content: Sanitizing user input in the database query builder to prevent SQL injection attacks through parameterized queries` | _(use default template)_ |
| Add unit tests for the payment processing module | `Name: Payment Processing Test Coverage`<br>`Category: Testability`<br>`Content: Adding unit tests for the payment processing module with mocked external payment gateway services` | _(use default template)_ |
| Implement a rate limiter middleware for the API | `Name: Rate Limiting Enforcement`<br>`Category: Reliability`<br>`Content: Implementing rate limiting middleware to throttle HTTP API requests and protect against abuse` | _(use default template)_ |
| Add error handling to the file upload handler | `Name: File Upload Error Handling`<br>`Category: Reliability`<br>`Content: Adding structured error handling and exception management to the file upload handler for graceful failure recovery` | _(use default template)_ |
| Optimize the dashboard query that takes 5 seconds to load | `Name: Database Query Performance Optimization`<br>`Category: Performance`<br>`Content: Optimizing slow database queries for the dashboard view through indexing, query restructuring, or caching` | _(use default template)_ |
| Add ARIA labels to the navigation menu _(TypeScript React)_ | `Name: Navigation Accessibility Labels`<br>`Category: Accessibility`<br>`Content: Adding ARIA attributes and roles to the navigation menu to ensure screen reader compatibility and keyboard navigation` | `Name: Code Quality and Architecture Compliance`<br>`Category: Architecture`<br>`Content: React component structure, TypeScript strict type checking, consistent naming conventions, proper prop typing, and component test coverage` |
| Add a new user management module with CRUD endpoints | `Name: Module Structure and Layer Boundaries`<br>`Category: Architecture`<br>`Content: Creating a new module with proper directory structure, service layer, repository pattern, and dependency injection in a Python FastAPI modulith` | _(use default template)_ |
| Add logging to the payment processing pipeline _(Go microservice)_ | `Name: Structured Logging Implementation`<br>`Category: Observability`<br>`Content: Adding structured logging with contextual fields and appropriate log levels to the payment processing pipeline` | `Name: Code Quality and Architecture Compliance`<br>`Category: Architecture`<br>`Content: Go package structure, interface-based dependency injection, structured logging with contextual fields, error wrapping conventions, and consistent handler patterns` |

## Approach: Start from the Coding Assignment

1. Read the coding assignment and identify the **core concern** -- what rule would a reviewer look for?
2. Write that as a concise **Name** (5-10 words)
3. Pick the single best **Category** from the list above
4. Write 1-2 sentences for **Content** describing what should be checked or enforced; include tech stack details when the repository context is known
5. Assemble the three-line structured topic query
6. Generate the cross-cutting query using the template (adjust Content for the repository's tech stack)
7. Call the search endpoint with both queries (top_k=20 each), merge and deduplicate results

## Fallback

If the coding assignment is very short or ambiguous (e.g., "fix the bug"), use the assignment text as the **Name** field, pick the closest Category (default to `Correctness` when truly ambiguous -- the cross-cutting query already covers Architecture, so using a different category for the topic query maximizes category diversity), and write a brief Content line restating the assignment with at least 15 words. Still generate the cross-cutting query alongside it. A short structured query is better than an invented one.

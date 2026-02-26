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
  - `Security` — authentication, authorization, injection, secrets, encryption
  - `Correctness` — logic errors, null handling, off-by-one, type safety
  - `Quality` — code style, naming, readability, maintainability, dead code
  - `Reliability` — error handling, retries, graceful degradation, timeouts
  - `Performance` — latency, caching, memory, query optimization, batching
  - `Testability` — test coverage, mocking, test structure, assertions
  - `Compliance` — licensing, regulatory, data retention, audit trails
  - `Accessibility` — WCAG, ARIA, screen readers, keyboard navigation
  - `Observability` — logging, metrics, tracing, alerting, monitoring
  - `Architecture` — layering, coupling, module boundaries, API design
- **Content**: 1-2 sentences describing what specifically should be checked or enforced for this coding assignment.

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

## Examples

| Coding Assignment | Generated Query |
|---|---|
| Add a login endpoint that accepts username and password, validates credentials against the database, and returns a JWT token | `Name: JWT Authentication Endpoint Validation`<br>`Category: Security`<br>`Content: Implementing a login endpoint that validates user credentials against the database and issues JWT tokens securely` |
| Refactor the user service to use async/await instead of callbacks | `Name: Async Await Migration Pattern`<br>`Category: Quality`<br>`Content: Refactoring a service layer from callback-based concurrency to async/await, ensuring correct error propagation and resource cleanup` |
| Fix a SQL injection vulnerability in the search query builder | `Name: SQL Injection Prevention`<br>`Category: Security`<br>`Content: Sanitizing user input in the database query builder to prevent SQL injection attacks through parameterized queries` |
| Add unit tests for the payment processing module | `Name: Payment Processing Test Coverage`<br>`Category: Testability`<br>`Content: Adding unit tests for the payment processing module with mocked external payment gateway services` |
| Implement a rate limiter middleware for the API | `Name: Rate Limiting Enforcement`<br>`Category: Reliability`<br>`Content: Implementing rate limiting middleware to throttle HTTP API requests and protect against abuse` |
| Add error handling to the file upload handler | `Name: File Upload Error Handling`<br>`Category: Reliability`<br>`Content: Adding structured error handling and exception management to the file upload handler for graceful failure recovery` |
| Optimize the dashboard query that takes 5 seconds to load | `Name: Database Query Performance Optimization`<br>`Category: Performance`<br>`Content: Optimizing slow database queries for the dashboard view through indexing, query restructuring, or caching` |
| Add ARIA labels to the navigation menu | `Name: Navigation Accessibility Labels`<br>`Category: Accessibility`<br>`Content: Adding ARIA attributes and roles to the navigation menu to ensure screen reader compatibility and keyboard navigation` |

## Approach: Start from the Coding Assignment

1. Read the coding assignment and identify the **core concern** — what rule would a reviewer look for?
2. Write that as a concise **Name** (5-10 words)
3. Pick the single best **Category** from the list above
4. Write 1-2 sentences for **Content** describing what should be checked or enforced
5. Assemble the three-line structured query

## Fallback

If the coding assignment is very short or ambiguous (e.g., "fix the bug"), use the assignment text as the **Name** field, pick the closest Category (default to `Correctness` when truly ambiguous), and write a brief Content line restating the assignment. A short structured query is better than an invented one.

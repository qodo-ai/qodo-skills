# Query Generation Guidelines

The search query is the most important input to the `/rules/search` endpoint. A well-formed query retrieves rules that are genuinely applicable to the task; a generic query returns irrelevant or noisy rules.

## Strategy

Generate a query that captures:
1. **The action being performed** — what kind of change (e.g., adding, modifying, refactoring, fixing)
2. **The domain or subsystem** — what area of the codebase (e.g., authentication, database layer, REST API, frontend)
3. **Key technologies** — languages, frameworks, libraries involved (e.g., Python, FastAPI, React, SQL)
4. **The core concern** — what the task is fundamentally about (e.g., input validation, error handling, async calls, security)

## Query Format

Write the query as a short, natural-language phrase — typically one sentence or a comma-separated list of key concepts. Aim for 10–25 words.

**Do not** include filler words like "please", "I need to", "implement a feature to", or other padding that dilutes the semantic signal.

## Examples

| Coding Assignment | Generated Query |
|---|---|
| Add a login endpoint that accepts username and password, validates credentials against the database, and returns a JWT token | `authentication login endpoint JWT token credential validation Python` |
| Refactor the user service to use async/await instead of callbacks | `async await refactoring Python service layer concurrency` |
| Fix a SQL injection vulnerability in the search query builder | `SQL injection security input sanitization query builder database` |
| Add unit tests for the payment processing module | `unit testing payment processing mock external services pytest` |
| Implement a rate limiter middleware for the API | `rate limiting middleware API throttling HTTP requests` |
| Add error handling to the file upload handler | `error handling file upload exception management HTTP API` |

## Template

Use this template to construct the query:

```
{action} {domain/subsystem} {technologies} {core concern}
```

Example:
- Assignment: "Add pagination to the products API endpoint using cursor-based pagination"
- Query: `pagination cursor-based REST API endpoint products database query`

## Fallback

If the coding assignment is very short or ambiguous (e.g., "fix the bug"), use the assignment text verbatim as the query rather than generating a paraphrase. A short verbatim query is better than an invented one.

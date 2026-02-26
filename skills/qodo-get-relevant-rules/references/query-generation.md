# Query Generation Guidelines

The search query is the most important input to the `/rules/search` endpoint. A well-formed query retrieves rules that are genuinely applicable to the task; a generic query returns irrelevant or noisy rules.

## Strategy

Generate a query that captures:
1. **The action being performed** — what kind of change (e.g., adding, modifying, refactoring, fixing)
2. **The domain or subsystem** — what area of the codebase (e.g., authentication, database layer, REST API, frontend)
3. **Key technologies** — languages, frameworks, libraries involved (e.g., Python, FastAPI, React, SQL)
4. **The core concern** — what the task is fundamentally about (e.g., input validation, error handling, async calls, security)

## Query Format

Write the query as a **natural language sentence** — not a keyword list. The search endpoint uses embedding-based semantic retrieval, which performs significantly better with natural language than with flat keyword lists.

Aim for **one concise sentence** of 10-25 words that reads like a short description of the task.

**Do not** write keyword-style queries (e.g., `authentication login JWT token Python`). Instead, write a sentence: `Adding a login authentication endpoint with JWT tokens that validates credentials in Python`.

**Do not** include filler words like "please", "I need to", or other padding that dilutes the semantic signal.

## Examples

| Coding Assignment | Generated Query |
|---|---|
| Add a login endpoint that accepts username and password, validates credentials against the database, and returns a JWT token | `Adding a login authentication endpoint with JWT token credential validation against the database` |
| Refactor the user service to use async/await instead of callbacks | `Refactoring a Python service layer from callbacks to async/await concurrency` |
| Fix a SQL injection vulnerability in the search query builder | `Fixing SQL injection vulnerability by sanitizing input in the database query builder` |
| Add unit tests for the payment processing module | `Adding unit tests for the payment processing module with mocked external services` |
| Implement a rate limiter middleware for the API | `Adding rate limiting middleware to throttle HTTP API requests` |
| Add error handling to the file upload handler | `Adding error handling and exception management to the HTTP file upload handler` |

## Approach: Start from the First Sentence

Experimentation shows that the **first sentence or title** of the coding assignment already captures the core task effectively. Use it as the starting point:

1. Take the first sentence or title of the coding assignment
2. Rephrase it as a concise natural language sentence if needed (remove filler, add key technology terms)
3. Keep the sentence self-contained — it should make sense without additional context

If the assignment is already a clear, concise sentence, use it directly or with minimal rephrasing.

## Fallback

If the coding assignment is very short or ambiguous (e.g., "fix the bug"), use the assignment text verbatim as the query rather than generating a paraphrase. A short verbatim query is better than an invented one.

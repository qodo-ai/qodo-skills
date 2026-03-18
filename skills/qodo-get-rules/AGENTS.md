# qodo-get-rules - Agent Guidelines

> Skill-specific guidelines for working on the `qodo-get-rules` skill.

## Skill Architecture

This skill fetches rules relevant to the current coding assignment using semantic search. It:

1. Generates a focused search query from the current coding assignment
2. Calls `POST /rules/search` twice in parallel (topic query + cross-cutting query)
3. Returns ranked rules most relevant to the task, capped at 15–20 rules

Key design properties:
- Uses `POST /rules/search` — a single request per query, no pagination
- Requires a query generation step (see `references/query-generation.md`)
- Returns a ranked subset, not all rules
- No scope filtering — the search endpoint handles relevance via semantic matching

## Reference Files

| File | Purpose |
|---|---|
| `references/query-generation.md` | How to generate the search query from the assignment |
| `references/search-endpoint.md` | Full contract for POST /rules/search, top_k, error handling |
| `references/repository-scope.md` | Git repo detection (verify user is in a git repo) |
| `references/output-format.md` | How to format the rules output |
| `../../references/usage-tracking.md` | Required HTTP headers for all Qodo API calls |

## Key Design Decisions

**Structured query format mirrors rule embeddings**: Queries use a three-field format — `Name:`, `Category:`, `Content:` — that mirrors how rules are embedded in the vector database. This ensures the embedding model aligns on all three semantic dimensions rather than collapsing the signal into a single sentence.

**Dual-query strategy (topic + cross-cutting)**: Each invocation generates two queries: a topic query focused on the assignment's primary concern, and a cross-cutting query targeting architectural/quality patterns. Evaluation showed cross-cutting rules account for 60%+ of rules flagged in real reviews but are missed by topic-only queries.

**`TOP_K` is tunable**: Each query uses `top_k=TOP_K` (default: 20). Results are merged and deduplicated — final count depends on overlap between the two queries. No pagination is needed regardless of `TOP_K` value; the search endpoint always returns results in a single response.

**Severity enforcement preserved**: Rules are returned ranked by relevance. ERROR rules must be complied with (and documented via comment); WARNING rules should be followed; RECOMMENDATION rules are considered when appropriate.

**Graceful failure on empty results**: An empty `rules` list from the endpoint is valid — proceed without rule constraints.

## Development Setup

- API key: `~/.qodo/config.json` (`API_KEY` field) or `QODO_API_KEY` env var
- Environment: `~/.qodo/config.json` (`ENVIRONMENT_NAME` field) or `QODO_ENVIRONMENT_NAME` env var

## Testing

Test scenarios to verify:
1. **Happy path** — assignment with a clear domain generates a good query, rules returned and formatted with severity labels
2. **Empty results** — endpoint returns `{"rules": []}` — skill outputs "No relevant rules found" and does not crash
3. **No API key** — inform user with setup instructions, exit gracefully
4. **Not in git repo** — inform user, exit gracefully
5. **HTTP error (401/403/404/5xx)** — appropriate error message, exit gracefully
6. **Short/ambiguous assignment** — verbatim assignment used as query (fallback behavior)
7. **ERROR rules present** — verify compliance comment is added to generated code

---

See root `AGENTS.md` for universal guidelines.

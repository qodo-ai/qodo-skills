# qodo-get-relevant-rules - Agent Guidelines

> Skill-specific guidelines for working on the `qodo-get-relevant-rules` skill.

## Skill Architecture

This skill is a **semantic-search variant** of `qodo-get-rules`. Instead of fetching all rules with pagination, it:

1. Generates a focused search query from the current coding assignment
2. Calls `POST /rules/search` (a single request, no pagination)
3. Returns ranked rules most relevant to the task

Key difference from `qodo-get-rules`:
- Uses `POST /rules/search` instead of `GET /rules`
- Requires a query generation step
- Returns a ranked subset, not all rules
- No pagination — single request returns top_k results

## Reference Files

| File | Purpose |
|---|---|
| `references/query-generation.md` | How to generate the search query from the assignment |
| `references/search-endpoint.md` | Full contract for POST /rules/search, top_k, error handling |
| `references/repository-scope.md` | Git repo detection (for context, not filtering) |
| `../../qodo-get-rules/references/attribution.md` | Required HTTP headers |

## Key Design Decisions

**Query generation is critical**: The quality of the search query directly determines retrieval quality. Queries must be **natural language sentences**, not keyword lists -- embedding models perform significantly better with natural language. Follow the guidelines in `references/query-generation.md` carefully.

**top_k default is 20**: Validated by Track D experimentation (best F1 across precision/recall trade-off). The value is documented in `references/search-endpoint.md`.

**Graceful failure on empty results**: An empty `rules` list from the endpoint is valid — proceed without rule constraints. Do not crash or error.

**No scope filtering**: Unlike `qodo-get-rules`, the repository scope is not sent as a query parameter. Step 2 only verifies the user is in a git repo; no scope extraction is performed.

## Development Setup

Same as `qodo-get-rules`:
- API key: `~/.qodo/config.json` (`API_KEY` field) or `QODO_API_KEY` env var
- Environment: `~/.qodo/config.json` (`ENVIRONMENT_NAME` field) or `QODO_ENVIRONMENT_NAME` env var

## Testing

Test scenarios to verify:
1. **Happy path** — assignment with a clear domain generates a good query, rules are returned and formatted
2. **Empty results** — endpoint returns `{"rules": []}` — skill outputs "No relevant rules found" and does not crash
3. **No API key** — inform user with setup instructions, exit gracefully
4. **Not in git repo** — inform user, exit gracefully
5. **HTTP error (401/403/404/5xx)** — appropriate error message, exit gracefully
6. **Short/ambiguous assignment** — verbatim assignment used as query (fallback behavior)

---

See root `AGENTS.md` for universal guidelines.

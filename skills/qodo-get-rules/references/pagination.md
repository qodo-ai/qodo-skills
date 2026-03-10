# Fetching Rules with Pagination

The API returns rules in pages of 50. All pages must be fetched to ensure no rules are missed.

## Algorithm

1. Start with `page=1`, `page_size=50`, accumulate results in an empty list
2. Request: `GET {API_URL}/rules?scopes={ENCODED_SCOPE}&state=active&page={PAGE}&page_size=50`
   - Header: `Authorization: Bearer {API_KEY}`
   - Header: `request-id: {REQUEST_ID}` — UUID generated once in Step 3; same value on every page fetch
   - Header: `qodo-client-type: skill-qodo-get-rules` — identifies this skill as the caller
   - Header: `trace_id: {TRACE_ID}` — only include if `TRACE_ID` is set in the shell environment; skip silently otherwise
3. On non-200 response, handle the error and exit gracefully:
   - `401` — invalid/expired API key
   - `403` — access forbidden
   - `404` — endpoint not found (check `QODO_ENVIRONMENT_NAME`)
   - `429` — rate limit exceeded
   - `5xx` — API temporarily unavailable
   - connection error — check internet connection
4. Parse `rules` array from JSON response body
5. Append page rules to accumulated list
6. If rules returned on this page < 50 → last page, stop
7. Otherwise increment page and repeat from step 2
8. Safety limit: stop after 100 pages (5000 rules max)

## API URL

Construct `{API_URL}` using the following priority:

1. **`QODO_API_URL` in config** (highest priority): If `QODO_API_URL` is present in `~/.qodo/config.json`, use `{QODO_API_URL}/rules/v1` as the full API URL. The `/rules/v1` path is always appended internally — do not include it in the config value.

2. **`ENVIRONMENT_NAME`-based construction** (fallback): If `QODO_API_URL` is not set, construct from `ENVIRONMENT_NAME` as before:

| `ENVIRONMENT_NAME` | `{API_URL}` |
|---|---|
| not set / empty | `https://qodo-platform.qodo.ai/rules/v1` |
| `staging` | `https://qodo-platform.staging.qodo.ai/rules/v1` |
| `qodost.st` | `https://qodo-platform.qodost.st.qodo.ai/rules/v1` |

The `ENVIRONMENT_NAME` value is substituted verbatim as a subdomain segment — dots in the value become dots in the hostname.

## After Fetching

If total rules == 0, inform the user no rules are configured for the repository scope and exit gracefully.
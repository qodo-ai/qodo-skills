# POST /rules/search Endpoint

## Request

```
POST {API_URL}/rules/search
Content-Type: application/json
Authorization: Bearer {API_KEY}
request-id: {REQUEST_ID}
qodo-client-type: skill-qodo-get-relevant-rules
```

**Body:**
```json
{
  "query": "<generated search query>",
  "top_k": 20
}
```

**`top_k` default:** Use `20` per query. The skill generates two queries (topic + cross-cutting) and calls this endpoint once per query, each with `top_k=20`. Results are merged and deduplicated by rule ID. This gives the LLM classification step more candidates while maintaining precision per query. Experimentation (Track D) validated that `top_k=20` per query provides a good balance.

**Merge strategy and result cap:** When merging topic and cross-cutting results, use the following approach to prevent rule fatigue:
1. Start with topic query results (in order of relevance).
2. Append cross-cutting results not already present, in order of relevance.
3. **Cap the final merged list at 15-20 unique rules.** If the combined deduplicated set exceeds 20 rules, truncate at 20, keeping topic results ahead of cross-cutting fills.

This prioritization ensures task-specific rules are never pushed out by cross-cutting results.

## Response

```json
{
  "rules": [
    { "id": "...", "name": "...", "content": "..." },
    ...
  ]
}
```

Rules are returned ranked by relevance (most relevant first). The list may be empty if no matching rules exist — this is a valid response; do not treat it as an error.

## API URL Construction

Construct `{API_URL}` from `ENVIRONMENT_NAME` (read from `~/.qodo/config.json`, overridable via `QODO_ENVIRONMENT_NAME` env var):

| `ENVIRONMENT_NAME` | `{API_URL}` |
|---|---|
| not set / empty | `https://qodo-platform.qodo.ai/rules/v1` |
| `staging` | `https://qodo-platform.staging.qodo.ai/rules/v1` |
| `qodost.st` | `https://qodo-platform.qodost.st.qodo.ai/rules/v1` |

The `ENVIRONMENT_NAME` value is substituted verbatim as a subdomain segment.

## Attribution Headers

All requests must include attribution headers per the [attribution guidelines](../../qodo-get-rules/references/attribution.md):

| Header | Value |
|---|---|
| `Authorization` | `Bearer {API_KEY}` |
| `request-id` | UUID generated once per invocation |
| `qodo-client-type` | `skill-qodo-get-relevant-rules` |
| `trace_id` (optional) | Value of `TRACE_ID` env var if set |

## Example (curl)

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-get-relevant-rules" \
  -d "{\"query\": \"${SEARCH_QUERY}\", \"top_k\": 20}" \
  "${API_URL}/rules/search"
```

With optional trace header:
```bash
TRACE_HEADER=""
if [ -n "${TRACE_ID:-}" ]; then
  TRACE_HEADER="-H trace_id:${TRACE_ID}"
fi

curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-get-relevant-rules" \
  ${TRACE_HEADER} \
  -d "{\"query\": \"${SEARCH_QUERY}\", \"top_k\": 20}" \
  "${API_URL}/rules/search"
```

## Example (Python)

```python
import json
import os
from urllib.request import urlopen, Request

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
    "request-id": request_id,
    "qodo-client-type": "skill-qodo-get-relevant-rules",
}
if trace_id := os.environ.get("TRACE_ID"):
    headers["trace_id"] = trace_id

body = json.dumps({"query": search_query, "top_k": 20}).encode()
req = Request(f"{api_url}/rules/search", data=body, headers=headers, method="POST")
with urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read())
rules = data.get("rules", [])
```

## Error Handling

| Status | Meaning | Action |
|---|---|---|
| 200 | Success | Parse `rules` array; empty list is valid |
| 401 | Invalid or expired API key | Inform user, exit gracefully |
| 403 | Access forbidden | Inform user, exit gracefully |
| 404 | Endpoint not found | Inform user to check `QODO_ENVIRONMENT_NAME`, exit gracefully |
| 429 | Rate limit exceeded | Inform user, exit gracefully |
| 5xx | API temporarily unavailable | Inform user, exit gracefully |
| Connection error | Network issue | Inform user to check internet connection, exit gracefully |

**Never crash on an empty `rules` list.** An empty result means no relevant rules exist — proceed with the coding task without constraints.

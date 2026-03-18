# Usage Tracking Headers for Qodo API Endpoints

All HTTP requests to Qodo API endpoints must include usage tracking headers so the platform can identify the caller, correlate requests, and support tracing.

## Required Headers

| Header | Value | Notes |
|--------|-------|-------|
| `Authorization` | `Bearer {API_KEY}` | Required for authentication |
| `request-id` | `{UUID}` | Generated once per invocation; reuse across all requests in the same invocation |
| `qodo-client-type` | `skill-{skill-name}` | Identifies the skill making the request |

## Optional Headers

| Header | Value | Notes |
|--------|-------|-------|
| `trace_id` | `{TRACE_ID}` | Only include if `TRACE_ID` is set in the shell environment; skip silently otherwise |

## Implementation Rules

1. **`request-id`**: Generate a UUID once at the start of each skill invocation (e.g. `uuidgen` or `python3 -c "import uuid; print(uuid.uuid4())"`). Use the **same value on every request** in that invocation — this correlates all requests for a single skill run on the platform side.

2. **`qodo-client-type`**: Use the format `skill-{skill-name}` where `skill-name` matches the skill's identifier. For example:
   - `qodo-get-rules` skill → `qodo-client-type: skill-qodo-get-rules`
   - A new `my-skill` skill → `qodo-client-type: skill-my-skill`

3. **`trace_id`**: Read from the `TRACE_ID` shell environment variable. If not set, omit the header entirely — do not send an empty value.

## Example (bash)

```bash
curl -s \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-{skill-name}" \
  "${API_URL}/..."
```

With optional trace:

```bash
TRACE_HEADER=""
if [ -n "${TRACE_ID:-}" ]; then
  TRACE_HEADER="-H trace_id:${TRACE_ID}"
fi

curl -s \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-{skill-name}" \
  ${TRACE_HEADER} \
  "${API_URL}/..."
```

## Example (Python)

```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "request-id": request_id,
    "qodo-client-type": "skill-{skill-name}",
}
if trace_id := os.environ.get("TRACE_ID"):
    headers["trace_id"] = trace_id
```

## Why This Matters

- **`request-id`** allows the Qodo platform to correlate all requests in a single skill invocation, enabling accurate usage metrics and debugging.
- **`qodo-client-type`** identifies which skill or integration is calling the API, enabling per-client analytics and support.
- **`trace_id`** enables distributed tracing when running in environments that propagate trace context (e.g., CI pipelines, observability platforms).

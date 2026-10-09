# Auth and Environment Resolution

## API Key

Resolution order (first found wins):

1. `QODO_API_KEY` environment variable
2. `~/.qodo/auth.key` file (single line, no newline trimming needed)
3. `API_KEY` field in `~/.qodo/config.json`

If no key is found, exit with:
```
Error: Qodo API key not found.
Set QODO_API_KEY or create ~/.qodo/auth.key with your key.
Get your key at https://app.qodo.ai/account/api-keys
```

## API URL

Resolution order (first found wins):

1. **Skill argument** — if the argument looks like a Qodo app URL (`https://app.<env>.qodo.ai`), extract `<env>` and build:
   `https://qodo-platform.<env>.qodo.ai/rules/v1`

2. **`QODO_API_URL` in config** — `~/.qodo/config.json` field `QODO_API_URL`:
   `{QODO_API_URL}/rules/v1`

3. **`ENVIRONMENT_NAME` in config** — `~/.qodo/config.json` field `ENVIRONMENT_NAME` (also overridable via `QODO_ENVIRONMENT_NAME` env var):
   `https://qodo-platform.{ENVIRONMENT_NAME}.qodo.ai/rules/v1`

4. **Production default:**
   `https://qodo-platform.qodo.ai/rules/v1`

## App URL → API URL Examples

| App URL (user provides) | API Base URL |
|---|---|
| `https://app.qodo.ai` | `https://qodo-platform.qodo.ai/rules/v1` |
| `https://app.staging.qodo.ai` | `https://qodo-platform.staging.qodo.ai/rules/v1` |
| `https://app.qodost.st.qodo.ai` | `https://qodo-platform.qodost.st.qodo.ai/rules/v1` |

The path after the hostname (e.g. `/rules?state=active`) is ignored — only the hostname matters.

## Request Headers

Every API call must include:

```
Authorization: Bearer {API_KEY}
request-id: {REQUEST_ID}      # UUID, generated once per skill invocation
qodo-client-type: skill-qodo-manage-rules
Content-Type: application/json   # only for POST/PUT requests
```

Generate `REQUEST_ID`:
```bash
REQUEST_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
```

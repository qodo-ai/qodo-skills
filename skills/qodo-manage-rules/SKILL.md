---
name: qodo-manage-rules
description: "Manage Qodo rules: list, get, create (with AI-drafted content), update, and delete rules via the Qodo Rules API. Use when the user wants to view, create, edit, activate, deactivate, or delete coding rules in a Qodo environment."
allowed-tools: "Bash"
triggers:
  - "manage.?rules"
  - "create.?rule"
  - "add.?rule"
  - "new.?rule"
  - "delete.?rule"
  - "remove.?rule"
  - "update.?rule"
  - "edit.?rule"
  - "activate.?rule"
  - "deactivate.?rule"
  - "list.?rules"
  - "show.?rules"
  - "get.?rule"
  - "view.?rule"
  - "find.?rule"
  - "qodo.?manage"
  - "rules.?management"
---

# Manage Qodo Rules Skill

## Description

Manages Qodo coding rules via the Rules API. Supports listing, viewing, creating (with AI-drafted content via `prompt-to-rule`), updating, and deleting rules. Admin-only operations (update, delete) detect missing permissions and surface them clearly.

---

## Arguments

The skill accepts an optional argument. Recognized forms:

- **App URL** — e.g. `https://app.qodost.st.qodo.ai` or `https://app.qodost.st.qodo.ai/rules?state=active`
  Overrides the environment derived from config. The hostname is parsed to build the API URL.
- **No argument** — uses `~/.qodo/config.json` (`ENVIRONMENT_NAME` / `QODO_API_URL`) to determine the environment.

---

## Workflow

### Step 1: Resolve Auth and API URL

Read the API key and determine the API base URL.

```bash
# 1. API key — prefer env var, fall back to auth.key file
if [ -n "${QODO_API_KEY:-}" ]; then
  API_KEY="$QODO_API_KEY"
elif [ -f "$HOME/.qodo/auth.key" ]; then
  API_KEY=$(cat "$HOME/.qodo/auth.key")
elif [ -f "$HOME/.qodo/config.json" ]; then
  API_KEY=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/.qodo/config.json'))); print(c.get('API_KEY',''))")
fi

if [ -z "$API_KEY" ]; then
  echo "Error: no API key found. Set QODO_API_KEY or create ~/.qodo/auth.key"
  exit 1
fi

# 2. API URL — from argument, config file, or production default
API_URL=""

# If an app URL was passed as argument, extract env name from hostname
# e.g. https://app.qodost.st.qodo.ai -> qodost.st -> https://qodo-platform.qodost.st.qodo.ai/rules/v1
if [ -n "${SKILL_ARG:-}" ]; then
  ENV_FROM_ARG=$(python3 -c "
from urllib.parse import urlparse
import sys
url = sys.argv[1]
host = urlparse(url if '://' in url else 'https://' + url).hostname or ''
# host: app.<env>.qodo.ai  -> env is everything between 'app.' and '.qodo.ai'
import re
m = re.match(r'^app\.(.+)\.qodo\.ai$', host)
if m:
    print(m.group(1))
" "$SKILL_ARG" 2>/dev/null)
  if [ -n "$ENV_FROM_ARG" ]; then
    API_URL="https://qodo-platform.${ENV_FROM_ARG}.qodo.ai/rules/v1"
  fi
fi

# Fall back to config file
if [ -z "$API_URL" ] && [ -f "$HOME/.qodo/config.json" ]; then
  API_URL=$(python3 -c "
import json, os
c = json.load(open(os.path.expanduser('~/.qodo/config.json')))
qodo_api_url = c.get('QODO_API_URL', '')
env_name = os.environ.get('QODO_ENVIRONMENT_NAME') or c.get('ENVIRONMENT_NAME', '')
if qodo_api_url:
    print(qodo_api_url.rstrip('/') + '/rules/v1')
elif env_name:
    print(f'https://qodo-platform.{env_name}.qodo.ai/rules/v1')
else:
    print('https://qodo-platform.qodo.ai/rules/v1')
" 2>/dev/null)
fi

# Production default
if [ -z "$API_URL" ]; then
  API_URL="https://qodo-platform.qodo.ai/rules/v1"
fi

REQUEST_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
```

See [auth-and-env.md](references/auth-and-env.md) for full details.

---

### Step 2: Detect Intent

Read the user's message and any skill argument to determine which operation to run:

| User says | Operation |
|---|---|
| "list rules", "show me rules", "what rules exist" | **LIST** |
| "get rule 123", "show rule 123", "view rule 123" | **GET** |
| "create a rule about X", "add a rule for Y" | **CREATE** |
| "update rule 123", "edit rule 123", "activate/deactivate rule 123" | **UPDATE** |
| "delete rule 123", "remove rule 123" | **DELETE** |
| "find similar rules to …", "check for duplicates" | **SIMILAR** |

Extract any rule ID mentioned. If an ID is needed but not provided, ask the user.

---

### Step 3: Execute Operation

See the relevant section below.

---

## Operations

### LIST — Browse Rules

**Endpoint:** `GET {API_URL}/rules`

**Common filters** (map from user's natural language):

| User says | Query param |
|---|---|
| "active rules" | `state=active` |
| "pending rules" | `state=pending` |
| "error severity" | `severity=error` |
| "category Quality" | `categories=Quality` |
| "from Code Patterns" | `sourceType=Code Patterns` |
| "containing 'logging'" | `nameContains=logging` |

```bash
# Build query string from detected filters (add params as needed)
PARAMS="pageSize=50"
[ -n "$STATE_FILTER" ]    && PARAMS="${PARAMS}&state=${STATE_FILTER}"
[ -n "$SEVERITY_FILTER" ] && PARAMS="${PARAMS}&severity=${SEVERITY_FILTER}"
[ -n "$CATEGORY_FILTER" ] && PARAMS="${PARAMS}&categories=${CATEGORY_FILTER}"
[ -n "$SOURCE_TYPE" ]     && PARAMS="${PARAMS}&sourceType=${SOURCE_TYPE}"
[ -n "$NAME_FILTER" ]     && PARAMS="${PARAMS}&nameContains=${NAME_FILTER}"

curl -s "${API_URL}/rules?${PARAMS}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules"
```

Present results as a concise table. See [output-format.md](references/output-format.md).

---

### GET — View a Rule

**Endpoint:** `GET {API_URL}/rule/{rule_id}`

```bash
curl -s "${API_URL}/rule/${RULE_ID}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules"
```

Present the rule concisely. Offer to show full content (examples, scopes) if the user asks.

---

### CREATE — Draft, Review, Confirm, Persist

**Three-step flow:** draft → review → confirm → create.

See [create-flow.md](references/create-flow.md) for the full flow.

**Step A — Draft via prompt-to-rule**

```bash
PROMPT_BODY=$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$USER_DESCRIPTION")

curl -s -X POST "${API_URL}/prompt-to-rule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$PROMPT_BODY"
```

**Step B — Present draft to user**

Show the drafted rule in a readable format (name, category, severity, content, examples). Ask: _"Does this look right? Reply 'yes' to create, or tell me what to change."_

**Step C — Create on confirmation**

```bash
CREATE_BODY=$(python3 -c "
import json, sys
rule = json.loads(sys.argv[1])
# Remove fields not accepted by RuleCreateRequest
for f in ['state', 'extractionReasoningContext', 'sourceUris', 'ruleId', 'workspaceId', 'createdAt', 'updatedAt', 'similaritiesCount', 'url', 'insights']:
    rule.pop(f, None)
print(json.dumps(rule))
" "$DRAFT_JSON")

curl -s -X POST "${API_URL}/rule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$CREATE_BODY"
```

Report the created rule ID on success.

---

### UPDATE — Edit an Existing Rule

**Endpoint:** `PUT {API_URL}/rule/{rule_id}` (admin only)

**Flow:**

1. Fetch current rule via `GET /rule/{rule_id}` and display it.
2. Apply the user's requested changes to the current values.
3. Show the proposed updated rule and ask for confirmation.
4. On confirmation, send `PUT` with the full `RuleUpdateRequest` body.

```bash
# RuleUpdateRequest requires ALL fields (same as RuleCreateRequest + state)
UPDATE_BODY=$(python3 -c "
import json, sys
rule = json.loads(sys.argv[1])
# Keep only fields accepted by RuleUpdateRequest
keep = ['name','category','severity','suggestionType','content','goodExamples','badExamples','scopes','source','sourceType','sourceUri','state']
out = {k: rule[k] for k in keep if k in rule}
print(json.dumps(out))
" "$UPDATED_RULE_JSON")

curl -s -X PUT "${API_URL}/rule/${RULE_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$UPDATE_BODY"
```

See [admin-operations.md](references/admin-operations.md) for 403 handling.

---

### DELETE — Remove a Rule

**Endpoint:** `DELETE {API_URL}/rule/{rule_id}` (admin only)

**Flow:**

1. Fetch the rule via `GET /rule/{rule_id}` and show name + severity to the user.
2. Ask for explicit confirmation: _"Are you sure you want to delete rule {id} '{name}'? This cannot be undone."_
3. On confirmation, send `DELETE`.

```bash
curl -s -X DELETE "${API_URL}/rule/${RULE_ID}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -o /dev/null -w "%{http_code}"
```

204 = success. See [admin-operations.md](references/admin-operations.md) for 403 handling.

---

### SIMILAR — Find Similar Rules

**Endpoint:** `POST {API_URL}/rule_similarity`

Use this to check for duplicates before creating, or when the user asks.

```bash
BODY=$(python3 -c "
import json, sys
rule = json.loads(sys.argv[1])
print(json.dumps({'name': rule['name'], 'category': rule['category'], 'severity': rule['severity'], 'content': rule['content'], 'goodExamples': rule.get('goodExamples',''), 'badExamples': rule.get('badExamples',''), 'state': 'active'}))
" "$RULE_JSON")

curl -s -X POST "${API_URL}/rule_similarity" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$BODY"
```

---

## Error Handling

| HTTP status | Meaning | Response |
|---|---|---|
| 401 | Invalid/expired API key | Inform user, show setup instructions |
| 403 | Admin required | "This operation requires admin (org owner or team owner) access." |
| 404 | Rule not found | "Rule {id} not found." |
| 409 | Duplicate rule name | "A rule with this name already exists." |
| 422 | Invalid request body | Show validation error details to user |
| 429 | Rate limit exceeded | "Rate limit hit. Retry in 1 minute." |
| 5xx | Server error | "Service temporarily unavailable. Please try again." |

---

## Common Mistakes

- **Sending wrong fields on create** — `POST /rule` uses `RuleCreateRequest` (no `state`). Strip `state`, `ruleId`, `workspaceId`, `createdAt`, `updatedAt` before posting.
- **Missing required fields** — `name`, `category`, `severity`, `content`, `goodExamples`, `badExamples` are all required on create and update.
- **Not confirming before destructive actions** — always ask for confirmation before delete and update.
- **Not showing the draft** — always present the `prompt-to-rule` output to the user before creating.
- **Skipping admin check** — for 403 responses, explain clearly that admin rights are required rather than showing a raw error.
- **No pagination** — `GET /rules` returns 50 per page. If user asks "how many rules", paginate to get `totalCount`.

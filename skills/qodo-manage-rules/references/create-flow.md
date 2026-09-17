# Create Rule Flow

Creating a rule is a three-step interactive flow: draft → review → confirm → persist.

## Step 1: Draft via prompt-to-rule

Call `POST {API_URL}/prompt-to-rule` with the user's description. This returns a fully structured `RuleBase` object with all required fields filled in.

```bash
PROMPT_BODY=$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$USER_DESCRIPTION")

DRAFT=$(curl -s -X POST "${API_URL}/prompt-to-rule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$PROMPT_BODY")
```

The response is a `RuleBase` object (camelCase JSON):

```json
{
  "name": "...",
  "category": "...",
  "severity": "error|warning|recommendation",
  "content": "...",
  "goodExamples": "...",
  "badExamples": "...",
  "state": "active",
  "scopes": ["/"],
  "source": "",
  "sourceType": null,
  "sourceUri": null
}
```

## Step 2: Present Draft to User

Display the draft clearly and ask for approval. Format:

```
Here's the drafted rule:

**Name:** {name}
**Category:** {category}
**Severity:** {severity}
**Scopes:** {scopes or "universal (/)"}

**Rule content:**
{content}

**Good examples:**
{goodExamples}

**Bad examples:**
{badExamples}

---
Does this look right? Reply **yes** to create it, or tell me what to change.
```

If the user requests changes, update the draft fields accordingly and re-present before proceeding.

## Step 3: Create on Confirmation

When the user confirms, strip response-only fields and POST:

```bash
CREATE_BODY=$(python3 -c "
import json, sys
rule = json.loads(sys.argv[1])
# Strip fields not in RuleCreateRequest
for f in ['state', 'extractionReasoningContext', 'sourceUris', 'ruleId', 'workspaceId', 'createdAt', 'updatedAt', 'similaritiesCount', 'url', 'insights']:
    rule.pop(f, None)
# Ensure required fields have values (prompt-to-rule may return empty strings)
rule.setdefault('goodExamples', '')
rule.setdefault('badExamples', '')
print(json.dumps(rule))
" "$DRAFT_JSON")

RESULT=$(curl -s -X POST "${API_URL}/rule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-manage-rules" \
  -d "$CREATE_BODY")
```

On success (HTTP 201), the response is `{"ruleId": <id>}`. Report: _"Rule created with ID {id}."_

## RuleCreateRequest Required Fields

All of these must be present and non-null:

| Field | Type | Notes |
|---|---|---|
| `name` | string | max 128 chars |
| `category` | string | e.g. Quality, Security, Reliability |
| `severity` | enum | `error`, `warning`, `recommendation` |
| `content` | string | the rule body |
| `goodExamples` | string | can be empty string `""` |
| `badExamples` | string | can be empty string `""` |

Optional:
- `scopes` — list of path strings, defaults to `["/"]` (universal) if omitted
- `source`, `sourceType`, `sourceUri` — auto-set by server from user token if omitted

## Duplicate Check (Optional)

Before creating, optionally call `POST {API_URL}/rule_similarity` with the draft to surface any similar existing rules. If high-similarity rules exist (score > 0.85), show them to the user and ask if they want to proceed.

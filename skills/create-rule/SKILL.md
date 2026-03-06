---
name: create-rule
description: "Use when the user wants to create a coding rule from a bug fix, coding pattern, or natural language description. Also suggest proactively after fixing bugs."
version: 0.2.0
triggers:
  - create.?rule
  - make.?.*rule
  - add.?rule
  - should.?be.?a.?rule
  - prevent.?this
  - catch.?this.?in.?review
allowed-tools: ["Bash", "Read", "AskUserQuestion"]
---

# Create Rule

Turn bug fixes and coding patterns into Qodo rules. Works in two modes:
- **User-initiated**: User asks to create a rule or says "this should be a rule"
- **Proactive**: After fixing a bug, offer to create a rule to prevent the same issue class

## When to Use

- User explicitly asks to create/add a rule
- User says "this should be a rule", "prevent this", "catch this in reviews"
- After fixing a significant bug (security issue, common pattern, architecture violation), offer: "This fix prevents [pattern]. Want to create a rule so it's caught in future reviews?"
  - If user declines, move on. Do not offer rule creation for this type of issue again in the current conversation.

---

## Workflow

### Step 1: Verify configuration

Read Qodo configuration from `~/.qodo/config.json`:
- **API_KEY** (required): The Qodo API key
- **ENVIRONMENT_NAME** (required): Environment name for API URL construction

Environment variables `QODO_API_KEY` and `QODO_ENVIRONMENT_NAME` take precedence over the config file.

Construct the API base URL: `https://qodo-platform.{ENVIRONMENT_NAME}.qodo.ai/rules/v1`

If API key or environment name is missing, inform the user and exit gracefully.

### Step 2: Gather context

Build a natural language prompt describing the rule. Sources:
- **User-initiated**: Use the user's description directly. If they point at code or a recent fix, include that context.
- **Proactive**: Describe the bug that was fixed and the pattern to prevent.

### Step 3: Generate draft rule

Call the prompt-to-rule API:

```
POST {API_URL}/prompt-to-rule
Authorization: Bearer {API_KEY}
Content-Type: application/json

{"prompt": "<natural language description>"}
```

The API returns a JSON draft with: name, category, severity, content, goodExamples, badExamples.

### Step 4: Check for duplicates

Call the similarity API with the full draft rule JSON (must include name, category, severity, content, goodExamples, badExamples, state):

```
POST {API_URL}/rule_similarity
Authorization: Bearer {API_KEY}
Content-Type: application/json

<full-draft-rule-json>
```

The API returns `relatedRules` -- an array of matches. Each match has:
- `rule`: the existing rule object (name, content, severity, ruleId, scopes, etc.)
- `relationship.score`: 0-1 similarity score
- `relationship.relationshipType`: e.g. `"Identical"`, `"Similar"`, `"Related"`

**If near-duplicate found** (relationshipType is `"Identical"` or score >= 0.85):
- Show the existing rule: name, content, severity, and score
- Recommend skipping: "A very similar rule already exists. I recommend using the existing rule."
- Ask: "Create a new rule anyway?"
- If no: exit

**If related rules found** (score 0.6-0.84):
- Show up to 3 top matches with scores
- Ask: "Related rules exist. Proceed with creating the new rule?"

**If no matches** (empty `relatedRules` array or all scores < 0.6): proceed

### Step 5: Present for approval

Determine the repo scope by parsing git remote: `git remote get-url origin`, strip `.git` suffix and protocol, format as `/org/repo/`.

Show the draft rule to the user:

```
Proposed Rule:

Name:         <name>
Category:     <category>
Severity:     <severity>
Scope:        <repo-scope>

Content:      <content>

Good Example: <goodExamples>
Bad Example:  <badExamples>
```

Use AskUserQuestion:
- "Create rule" -- Create the rule as shown
- "Change severity" -- Let user pick ERROR / WARNING / RECOMMENDATION
- "Change scope" -- Let user specify a different scope path
- "Cancel" -- Exit without creating

If user changes severity: update the value in the draft JSON before creating.
If user changes scope: use the new scope value when creating.

### Step 6: Create the rule

Call the create API with the approved rule JSON, injecting the scope:

```
POST {API_URL}/rule
Authorization: Bearer {API_KEY}
Content-Type: application/json

<rule-json with "scopes": ["/org/repo/"]>
```

The API returns `{"ruleId": <id>}`. The rule is created as a **suggestion** that needs admin approval to become active.

If the API returns HTTP 409, a rule with that name already exists -- inform the user.

### Step 7: Confirm

Report to user:
- Rule name and ruleId from the response
- That the rule was submitted as a suggestion and needs admin approval to become active
- Scope applied

---

## Common Mistakes

- **Nagging about rule creation** -- If user declines the proactive suggestion, do not offer rule creation for similar issues in this conversation. The decline is session-scoped.
- **Creating duplicate rules** -- Always run the similarity check before creating. If a near-duplicate exists, recommend skipping but let user override.
- **Ignoring user overrides** -- If user changes severity or scope at approval, update the draft JSON accordingly.

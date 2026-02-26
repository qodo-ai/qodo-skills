---
name: qodo-get-relevant-rules
description: "Fetches the most relevant coding rules from Qodo for the current coding task by generating a semantic search query from the assignment and calling the platform's search endpoint. Use this in place of qodo-get-rules when you have a specific coding task and want targeted rules rather than all rules."
allowed-tools: ["Bash"]
triggers:
  - "get.?relevant.?rules"
  - "relevant.?rules"
  - "search.?rules"
  - "find.?relevant.?rules"
  - "qodo.?relevant"
  - "qodo.?search.?rules"
---

# Get Qodo Relevant Rules Skill

## Description

Searches for the most relevant Qodo coding rules for the current coding task. Instead of loading all rules, this skill generates a focused search query from the coding assignment and calls `POST /rules/search` to retrieve only the rules most relevant to the task at hand.

**Use** when you have a specific coding task and want targeted, ranked rules. This is the semantic-search alternative to `qodo-get-rules`.

**Skip** if "Qodo Rules Loaded" already appears in conversation context.

---

## Workflow

### Step 1: Check if Rules Already Loaded

If rules are already loaded (look for "Qodo Rules Loaded" in recent messages), skip to Step 6.

### Step 2: Verify Working in a Git Repository

- Check that the current directory is inside a git repository. If not, inform the user that a git repository is required and exit gracefully.
- Extract the repository scope from the git `origin` remote URL. If no remote is found, exit silently. If the URL cannot be parsed, inform the user and exit gracefully.

See [repository scope detection](references/repository-scope.md) for details.

### Step 3: Verify Qodo Configuration

Check that the required Qodo configuration is present. The default location is `~/.qodo/config.json`.

- **API key**: Read from `~/.qodo/config.json` (`API_KEY` field). Environment variable `QODO_API_KEY` takes precedence. If not found, inform the user that an API key is required and provide setup instructions, then exit gracefully.
- **Environment name**: Read from `~/.qodo/config.json` (`ENVIRONMENT_NAME` field), with `QODO_ENVIRONMENT_NAME` environment variable taking precedence. If not found or empty, use production.
- **Request ID**: Generate a UUID (e.g. `python3 -c "import uuid; print(uuid.uuid4())"`) to use as `request-id` for the API call.

### Step 4: Generate Search Query from Coding Assignment

Generate a concise, focused search query from the coding assignment. The query quality directly determines retrieval quality.

See [query generation guidelines](references/query-generation.md) for the query generation strategy and examples.

### Step 5: Call POST /rules/search

Call the search endpoint with the generated query.

See [search endpoint](references/search-endpoint.md) for the full request/response contract, `top_k` defaults, error handling, and API URL construction.

### Step 6: Format and Output Rules

- Print the "📋 Qodo Rules Loaded" header with the search query used and total rule count.
- List rules in the order returned (they are already ranked by relevance):
  - Each rule: `- **{name}**: {content}`
- End output with `---`.

**Header format:**
```
# 📋 Qodo Rules Loaded

Search query: `{SEARCH_QUERY}`
Rules loaded: **{TOTAL_RULES}** (ranked by relevance to your task)

These rules must be applied during code generation based on severity:
```

If no rules were returned, output:
```
# 📋 Qodo Rules Loaded

No relevant rules found for this task. Proceeding without rule constraints.

---
```

Do **not** crash or error — an empty result is valid.

### Step 7: Apply Rules

Apply the returned rules to the coding task. Rules are returned ranked by relevance — apply all returned rules.

Inform the user about rule application after code generation:
- **Rules applied**: List which rules were followed
- **No applicable rules**: Inform: "No Qodo rules were applicable to this code change"

---

## Configuration

See [README.md](../../README.md#configuration) for full configuration instructions, including API key setup and environment variable options.

---

## Common Mistakes

- **Re-running when rules are loaded** - Check for "Qodo Rules Loaded" in context first
- **Vague query** - The search query must capture the nature of the task; a generic query returns irrelevant rules
- **Crashing on empty results** - An empty rules list is valid; proceed without rule constraints
- **Not in git repo** - Inform the user that a git repository is required and exit gracefully
- **No API key** - Inform the user with setup instructions; set `QODO_API_KEY` or create `~/.qodo/config.json`

---
name: get-rules
description: "Use when starting a conversation in a git repository with Qodo API key configured - loads repo-specific coding rules by severity for the current repo and path"
allowed-tools: ["Bash", "Read"]
---

# Get Rules

Fetches coding rules from the Qodo platform API for the current repository and path. Rules cover security requirements, coding standards, quality guidelines, and team conventions.

## When to Use

- Auto-invoke at conversation start in git repositories with API key configured
- **Skip** if "Qodo Rules Loaded" already appears in conversation context

## Workflow

### 1. Check Context

If rules are already loaded (look for "Qodo Rules Loaded" in recent messages), skip to step 3.

### 2. Fetch Rules

Run the fetch script from the repository root:
```bash
.claude/skills/get-rules/scripts/fetch-qodo-rules.sh
```

The script handles everything automatically (git detection, API auth, scope detection, pagination, error handling). Its stdout becomes conversation context - no additional processing needed.

### 3. Apply Rules by Severity

| Severity | Enforcement | When Skipped |
|---|---|---|
| **ERROR** | Must comply, non-negotiable. Add comment documenting compliance (e.g., `# Following Qodo rule: No Hardcoded Credentials`) | Explain to user and ask for guidance |
| **WARNING** | Should comply by default | Briefly explain why in response |
| **RECOMMENDATION** | Consider when appropriate | No action needed |

### 4. Report

After code generation, inform the user about rule application:
- **ERROR rules applied**: List which rules were followed
- **WARNING rules skipped**: Explain why
- **No rules applicable**: Inform: "No Qodo rules were applicable to this code change"
- **RECOMMENDATION rules**: Mention only if they influenced a design decision

## Scope Hierarchy

The script automatically determines scope from git remote and working directory:

- **Universal** (`/`) - applies everywhere
- **Org** (`/org/`) - applies to organization
- **Repo** (`/org/repo/`) - applies to repository
- **Path** (`/org/repo/path/`) - applies to specific paths (e.g., `modules/rules/`)

The API returns all matching parent scopes via prefix matching.

## Configuration

See the [repository README](../README.md#configuration) for API key setup (`~/.qodo/config.json` or `QODO_CLI_API_KEY` env var).

## Common Mistakes

- **Re-running when rules are loaded** - Check for "Qodo Rules Loaded" in context first
- **Missing compliance comments on ERROR rules** - ERROR rules require a comment documenting compliance
- **Forgetting to report when no rules apply** - Always inform the user when no rules were applicable, so they know the rules system is active

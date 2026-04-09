---
name: check-rules
description: "Use when planning implementation or before committing code -- fetches Qodo rules and checks code against them to catch violations before PR review"
version: 0.2.0
triggers:
  - check.?rules
  - verify.?rules
  - rules.?check
  - pre.?commit.?check
allowed-tools: ["Bash", "Read", "AskUserQuestion"]
---

# Check Rules

Shift Qodo rule enforcement left -- from PR review to planning and pre-commit. Fetches rules and checks code against `badExamples` to catch violations before they reach a PR.

## When to Use

- **Planning:** Before implementing a task, fetch rules and factor ERROR rules into the approach
- **Pre-commit:** Before committing, check staged changes against rules and flag violations
- **On demand:** User says "check rules", "verify rules", or "/check-rules"

## Prerequisites

- Git repository with remote
- Qodo configuration: `~/.qodo/config.json` with `API_KEY` and `ENVIRONMENT_NAME` (see [get-qodo-rules](../get-qodo-rules/SKILL.md) for setup)

---

## Workflow: Planning

When about to implement a task (entering plan mode, starting a multi-step change):

### Step 1: Fetch rules

Invoke the `get-qodo-rules` skill. This fetches rules from the Qodo API for the current repository scope and outputs them grouped by severity.

If rules are already loaded in the conversation (look for "Qodo Rules Loaded"), use the loaded rules instead of fetching again.

### Step 2: Identify relevant rules

Scan the loaded rules for ones relevant to the planned work. Match by:
- **Category:** e.g., "Security" rules are relevant when touching auth or DB code
- **Keywords:** match rule names/descriptions against the files and patterns in the plan
- **Severity:** prioritize ERROR rules -- these are non-negotiable

Do NOT list all rules. Only mention rules that directly affect the implementation approach.

### Step 3: Factor into the plan

For each relevant ERROR rule, state how the implementation will comply:
- "Rule 'No hardcoded secrets' (ERROR) -- will use environment variables for all credentials"
- "Rule 'Use parameterized SQL' (ERROR) -- DB layer will use prepared statements"

For relevant WARNING rules, note them as considerations without changing the approach unless warranted.

---

## Workflow: Pre-commit

When the user asks to commit or the agent is about to commit after finishing work:

### Step 1: Fetch rules

Invoke the `get-qodo-rules` skill to get a fresh set of rules. Do not rely on previously loaded rules -- they may be stale.

### Step 2: Get the staged diff

```bash
git diff --cached
```

If nothing is staged, check unstaged changes with `git diff`. If the user is about to stage and commit, check the files they intend to commit.

### Step 3: Check code against rules

For each rule (prioritizing ERROR, then WARNING):

1. Read the rule's `badExamples` -- these are concrete code patterns that violate the rule
2. Scan the diff for code that resembles a `badExample` pattern
3. If a match is found, that's a violation

Use the rule's `content` field to understand the intent behind the rule. The `badExamples` are the primary signal, but the content helps judge edge cases.

**Do NOT flag:**
- Code that existed before the change (only check new/modified lines)
- RECOMMENDATION rules as violations (mention if relevant, don't flag)
- Patterns that superficially resemble a `badExample` but serve a different purpose

### Step 4: Report violations

If violations found, present them grouped by severity:

```
Rules Check: <N> issues found

ERROR  "<rule-name>" (<category>)
  <file>:<line> -- <what the violation is>
  Fix: <reference the goodExample from the rule>

WARNING  "<rule-name>" (<category>)
  <file>:<line> -- <what the violation is>
  Fix: <reference the goodExample from the rule>
```

Then use AskUserQuestion:
- "Fix all" -- Fix all violations before committing
- "Fix ERROR only" -- Fix ERROR violations, commit with WARNINGs
- "Commit anyway" -- Proceed without fixing
- "Cancel" -- Don't commit

### Step 5: Fix or proceed

- If user chooses to fix: apply fixes referencing `goodExamples`, then re-check
- If user chooses to commit anyway: proceed with the commit
- If no violations were found: proceed with the commit silently (no "0 violations" report)

---

## Severity Handling

- **ERROR:** Must fix before committing. Recommend blocking the commit. These are non-negotiable rules (security, compliance, critical standards).
- **WARNING:** Should fix. Flag the violation but let the user decide. Don't nag if they choose to proceed.
- **RECOMMENDATION:** Do not flag as violations. Mention only if directly relevant to the change being made.

## Common Mistakes

- **Checking the entire codebase** -- Only check staged changes or planned work. Do not audit the whole repo.
- **Flagging old code** -- Only check new or modified lines in the diff. Pre-existing violations are not your concern.
- **Reporting zero violations** -- If no violations found, proceed silently. Don't report "0 issues found."
- **Blocking on WARNINGs** -- Only ERROR rules warrant recommending a commit block. WARNINGs are advisory.
- **Listing all rules at planning time** -- Only mention rules that directly affect the implementation. Don't dump the full rule list.
- **Using stale rules** -- Always invoke get-qodo-rules fresh at pre-commit time. Rules may have changed.

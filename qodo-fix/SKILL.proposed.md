---
name: qodo-fix
description: "Use when the user asks to see, fix, or address Qodo code review issues on the current branch's PR/MR - supports GitHub, GitLab, Bitbucket, Azure DevOps"
version: 0.3.0
triggers:
  - qodo.?fix
  - fix.?qodo
  - qodo.?review
  - review.?qodo
  - qodo.?issues?
  - show.?qodo
  - get.?qodo
---

# Qodo Fix

Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision. Supports GitHub, GitLab, Bitbucket, and Azure DevOps.

## When to Use

- User asks for a code review, to see Qodo issues, or to fix Qodo comments
- Current branch has an open PR/MR that Qodo has reviewed

**Do NOT use when:**
- No open PR/MR exists for the current branch (offer to create one instead)
- Qodo hasn't reviewed the PR/MR yet (advise user to wait)
- User wants a manual code review (this skill only works with Qodo reviews)

## Prerequisites

- Git repository with remote on a supported provider (GitHub, GitLab, Bitbucket, Azure DevOps)
- Provider CLI installed and authenticated -- see [providers.md](./providers.md) for commands and installation
- Open PR/MR on current branch, reviewed by Qodo bot (`pr-agent-pro`, `qodo-merge[bot]`, `qodo-ai[bot]`, etc.)

Quick check:
```bash
git remote get-url origin                        # Identify provider
gh --version && gh auth status                   # GitHub
glab --version && glab auth status               # GitLab
bb --version                                     # Bitbucket
az --version && az devops                        # Azure DevOps
```

## Qodo Review Types

| Type | Marker | Content |
|---|---|---|
| PR Compliance Guide | 🔍 | Security/ticket/custom compliance with 🟢/🟡/🔴/⚪ indicators |
| PR Code Suggestions | ✨ | Categorized improvements with importance ratings |
| Code Review by Qodo | (most detailed) | Structured issues with 🐞/📘/📎 sections and agent prompts |

## Severity Mapping

**Severity mapping** — derive from Qodo's action level and ordering:
- **"Action required"** issues → 🔴 CRITICAL / 🟠 HIGH
- **"Review recommended"** issues → 🟡 MEDIUM / ⚪ LOW
- Qodo's ordering within each action level implies relative severity — earlier items are more severe. Use position to distinguish: first items in "Action required" are 🔴 CRITICAL, later ones 🟠 HIGH. First items in "Review recommended" are 🟡 MEDIUM, later ones ⚪ LOW.

Action guidelines:
- 🔴 CRITICAL / 🟠 HIGH: Always "Fix"
- 🟡 MEDIUM: Usually "Fix", can "Defer" if low impact
- ⚪ LOW: Can be "Defer" unless quick to fix

## Workflow

### Step 0: Check push status

Check for uncommitted changes, unpushed commits, and get the current branch.

**Scenario A: Uncommitted changes exist**
- Inform: "You have uncommitted changes. These won't be included in the Qodo review."
- Ask: "Would you like to commit and push them first?"
- If yes: Wait for user action, then proceed to Step 1
- If no: Warn "Proceeding with review of pushed code only" and continue to Step 1

**Scenario B: Unpushed commits exist** (no uncommitted changes)
- Inform: "You have N unpushed commits. Qodo hasn't reviewed them yet."
- Ask: "Would you like to push them now?"
- If yes: Execute `git push`, inform "Pushed! Qodo will review shortly. Please wait ~5 minutes then run this skill again."
  - Exit skill (don't proceed -- Qodo needs time to review)
- If no: Warn "Proceeding with existing PR review" and continue to Step 1

**Scenario C: Everything pushed** -- Proceed to Step 1

### Step 1: Detect provider and find PR/MR

1. Detect git provider from remote URL -- see [providers.md](./providers.md) for detection table
2. Find the open PR/MR for this branch -- see [providers.md](./providers.md) for CLI commands

### Step 2: Get Qodo review comments

Fetch both PR-level summary comments and inline review comments -- see [providers.md](./providers.md) for CLI commands. Look for comments from Qodo bot identifiers.

**Check if review is still in progress:**
- If any comment contains "Come back again in a few minutes" or "An AI review agent is analysing this pull request", the review is still running
- Inform the user: "Qodo review is still in progress. Please wait a few minutes and try again."
- Exit early -- don't try to parse incomplete reviews

**Deduplicate issues across summary and inline comments:**
- Qodo posts each issue in two places: once in the **summary comment** (PR-level) and once as an **inline review comment** (attached to the specific code line). These share the same issue title.
- Qodo may also post multiple summary comments (Compliance Guide, Code Suggestions, Code Review) where issues can overlap with slightly different wording.
- Deduplicate by matching on **issue title** (primary key):
  - If an issue appears in both summary and inline, merge into a single issue
  - Prefer the **inline comment** for file location (exact line context)
  - Prefer the **summary comment** for severity, type, and agent prompt (more detailed)
  - **IMPORTANT:** Preserve each issue's **inline review comment ID** -- you will need it later (step 5) to reply directly to that comment with the decision
- Also deduplicate across multiple summary comments by location (file path + line numbers) as a secondary key
- If the same issue appears in multiple places, combine the agent prompts

### Step 3: Parse and display issues

- Extract the review body/comments from Qodo's review
- Parse out individual issues/suggestions
- **IMPORTANT: Preserve Qodo's exact issue titles verbatim** — do not rename, paraphrase, or summarize them. Use the title exactly as Qodo wrote it.
- **IMPORTANT: Preserve Qodo's original ordering** — display issues in the same order Qodo listed them. Qodo already orders by severity.
- Extract location, issue description, and suggested fix
- Extract the agent prompt from Qodo's suggestion (the description of what needs to be fixed)

Output format - Display as a markdown table ordered by severity (CRITICAL → HIGH → MEDIUM → LOW), preserving Qodo's relative ordering within each severity level:

Qodo Issues for PR #123: [PR Title]

| # | Severity | Issue Title | Issue Details | Type | Action |
|---|----------|-------------|---------------|------|--------|
| 1 | 🟠 HIGH | `get_active_installations_by_app_id` leaks orm | • **Location:** modules/git_integration/src/repositories/repo.py:114-131<br><br>• **Issue:** Returns ORM entities directly, no logging | 📘 Rule violation ⛯ Reliability | Fix |
| 2 | 🔴 CRITICAL | Inverted ownership check | • **Location:** modules/auth/src/api/v1/api_keys/services/api_keys_service.py:191<br><br>• **Issue:** == instead of !=, authorization bypass | 🐞 Bug ⛨ Security | Fix |

### Step 4: Ask user for fix preference

Use AskUserQuestion with options:
- "Review each issue" -- Review and approve/defer each issue individually (recommended)
- "Auto-fix all" -- Automatically apply all fixes marked as "Fix" without individual approval
- "Cancel" -- Exit without making changes

### Step 5: Fix issues

For each issue marked as "Fix" (starting with CRITICAL):

1. **Read** the relevant file(s) to understand the current code
2. **Implement the fix** by executing the Qodo agent prompt as a direct instruction. The agent prompt is the fix specification -- follow it literally, do not reinterpret or improvise a different solution. Only deviate if the prompt is clearly outdated relative to the current code (e.g., references lines that no longer exist).
3. **Calculate** the proposed fix in memory (DO NOT use Edit or Write tool yet)

**If interactive mode ("Review each issue"):**

**CRITICAL:** Present the fix and ask for approval in a SINGLE step. Do NOT show the diff separately and then ask. Combine into ONE message:
1. Brief header with issue title and location
2. Show Qodo's agent prompt in full so the user can verify the fix matches it
3. Display current code snippet
4. Display proposed change as markdown diff
5. Immediately use AskUserQuestion:
   - "Apply fix" -- Apply the proposed change
   - "Defer" -- Skip this issue (will prompt for reason)
   - "Modify" -- User wants to adjust the fix first

**IMPORTANT:** WAIT for user's choice via AskUserQuestion before proceeding.

- **If "Apply fix":** Apply change using Edit tool, reply to inline comment, git commit (see below)
- **If "Defer":** Ask for deferral reason, reply to inline comment with deferral, move to next issue
- **If "Modify":** Inform user they can make changes manually, move to next issue

**If auto-fix mode ("Auto-fix all"):**

Apply the fix directly using Edit tool, reply to inline comment, git commit (see below). Report each fix:
> **Fixed: [Issue Title]** at `[Location]`
> **Agent prompt:** [the Qodo agent prompt used]

**After each fix (both modes):**
- Reply to the Qodo inline comment -- see [providers.md](./providers.md) for inline reply commands
- Git commit: `git add <modified-files> && git commit -m "fix: <issue title>"`

**After all auto-fixes:** Display summary of fixed and skipped issues.

### Step 6: Post summary and push

**REQUIRED:** After all issues have been reviewed (fixed or deferred), ALWAYS post a summary comment using the provider CLI -- see [providers.md](./providers.md) for post comment commands:

```markdown
## Qodo Fix Summary

Reviewed and addressed Qodo review issues:

### Fixed Issues
- **Issue Title** (Severity) - Brief description of what was fixed

### Deferred Issues
- **Issue Title** (Severity) - Reason for deferring

---
*Generated by Qodo Fix skill*
```

After posting the summary, resolve the Qodo review comment -- see [providers.md](./providers.md) for resolve commands.

**Push:** If any fixes were applied (commits exist), ask the user if they want to push. If all issues were deferred, there are no commits to push -- skip this step.

## Special Cases

- **Unsupported git provider:** Inform the user and exit
- **No PR/MR exists:** Inform user, ask if they want to create one. If yes, use CLI to create, then inform "PR created! Qodo will review shortly. Run this skill again in ~5 minutes." **IMPORTANT:** Do NOT proceed without a PR/MR.
- **No Qodo review yet:** Inform "Qodo hasn't reviewed this PR/MR yet. Please wait a few minutes." Exit skill. **IMPORTANT:** This skill only works with Qodo reviews, not manual reviews.
- **Review in progress:** Inform user to wait and try again, then exit
- **Missing CLI tool:** Provide installation instructions from [providers.md](./providers.md) and exit

## Common Mistakes

- **Paraphrasing issue titles** -- Use Qodo's exact titles verbatim. Do not rename or summarize.
- **Reinterpreting agent prompts** -- The agent prompt IS the fix specification. Follow it literally, don't improvise a different solution.
- **Showing diff then asking separately** -- The diff and AskUserQuestion must be in a SINGLE message. Never split into two steps.
- **Proceeding without a PR/MR** -- Always verify an open PR/MR exists before fetching reviews.
- **Running when review is in progress** -- Check for "Come back again in a few minutes" before parsing.

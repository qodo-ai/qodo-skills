---
name: qodo-fix
description: Review code with Qodo - get AI-powered code review issues and fix them interactively (GitHub, GitLab, Bitbucket)
version: 2.2.0
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

A skill to show Qodo review issues for your current branch's PR/MR across multiple git providers.

## Prerequisites

### Required Tools:
- **Git** - For branch operations
- **Git Provider CLI** (one of):
  - **GitHub**: `gh` CLI
    - Install: `brew install gh` or [cli.github.com](https://cli.github.com/)
    - Authenticate: `gh auth login`
  - **GitLab**: `glab` CLI
    - Install: `brew install glab` or [glab.readthedocs.io](https://glab.readthedocs.io/)
    - Authenticate: `glab auth login`
  - **Bitbucket**: `bb` CLI or API access
    - See [bitbucket.org/product/cli](https://bitbucket.org/product/cli)

### Required Context:
- Must be in a git repository
- Repository must be hosted on a supported git provider (GitHub, GitLab, or Bitbucket)
- Current branch must have an open PR/MR
- PR/MR must have been reviewed by Qodo (pr-agent-pro bot, qodo-merge[bot], etc.)

### Quick Check:
```bash
git --version                                    # Check git installed
git remote get-url origin                        # Identify git provider
# Then check appropriate CLI:
gh --version && gh auth status                   # For GitHub
glab --version && glab auth status               # For GitLab
bb --version                                     # For Bitbucket
```

## Understanding Qodo Reviews

Qodo (formerly Codium AI) is an AI-powered code review tool that analyzes PRs/MRs with compliance checks, bug detection, and code quality suggestions.

### Bot Identifiers
Look for comments from: **`pr-agent-pro`**, **`pr-agent-pro-staging`**, **`qodo-merge[bot]`**, **`Codium-ai[bot]`**

### Review Comment Types
1. **PR Compliance Guide** 🔍 - Security/ticket/custom compliance with 🟢/🟡/🔴/⚪ indicators
2. **PR Code Suggestions** ✨ - Categorized improvements with importance ratings
3. **Code Review by Qodo** - Structured issues with 🐞/📘/📎 sections and agent prompts (most detailed)

### Identifying Qodo Comments
Headers: `## PR Compliance Guide`, `## PR Code Suggestions`, `## Code Review by Qodo`
Footer: Link to `https://www.qodo.ai` with Qodo logo
Format: Collapsible `<details>` sections, file locations as `[file.py[L123-L456]](...)`, severity indicators

### In-Progress Reviews
Messages like "Come back again in a few minutes" or "An AI review agent is analysing" mean the review is still running - wait before parsing.

## Instructions

When the user asks for a code review, to see Qodo issues, or fix Qodo comments:

**Step 0: Check code push status**

First, check if code is pushed and if PR exists:

```bash
# Check for uncommitted changes
UNCOMMITTED=$(git status --porcelain)

# Check for unpushed commits
UNPUSHED=$(git log @{u}.. --oneline 2>/dev/null)

# Get current branch
BRANCH=$(git branch --show-current)
```

**Handle three scenarios:**

**Scenario A: Uncommitted changes exist** (`$UNCOMMITTED` not empty)
- Inform: "⚠️ You have uncommitted changes. These won't be included in the Qodo review."
- Ask: "Would you like to commit and push them first?"
- If yes: Wait for user action, then proceed to Step 1
- If no: Warn "Proceeding with review of pushed code only" and continue to Step 1

**Scenario B: Unpushed commits exist** (`$UNPUSHED` not empty, `$UNCOMMITTED` empty)
- Inform: "⚠️ You have N unpushed commits. Qodo hasn't reviewed them yet."
- Ask: "Would you like to push them now?"
- If yes: Execute `git push`, inform "Pushed! Qodo will review shortly. Please wait ~5 minutes then run this skill again."
- Exit skill (don't proceed - Qodo needs time to review)
- If no: Warn "Proceeding with existing PR review" and continue to Step 1

**Scenario C: Everything pushed** (both empty)
- Proceed to Step 1

1. Detect git provider and get current branch:
   ```bash
   BRANCH=$(git branch --show-current)
   REMOTE_URL=$(git remote get-url origin)

   # Detect provider
   if [[ "$REMOTE_URL" =~ github\.com ]]; then
     PROVIDER="github"
   elif [[ "$REMOTE_URL" =~ gitlab\.com ]]; then
     PROVIDER="gitlab"
   elif [[ "$REMOTE_URL" =~ bitbucket\.org ]]; then
     PROVIDER="bitbucket"
   fi
   ```

2. Find the open PR/MR for this branch:

   **GitHub:**
   ```bash
   gh pr list --head <branch-name> --state open --json number,title
   ```

   **GitLab:**
   ```bash
   glab mr list --source-branch <branch-name> --state opened
   ```

   **Bitbucket:**
   ```bash
   # Use API or bb CLI
   bb pr list --source-branch <branch-name> --state OPEN
   ```

3. Get the Qodo review comments:

   **GitHub:**
   ```bash
   gh pr view <pr-number> --json comments
   ```

   **GitLab:**
   ```bash
   glab mr view <mr-iid> --comments
   ```

   **Bitbucket:**
   ```bash
   bb pr view <pr-id> --comments
   ```

   Look for comments where the author is "qodo-merge[bot]", "pr-agent-pro", "pr-agent-pro-staging" or similar Qodo bot name.

3a. Check if review is still in progress:
   - If any comment contains "Come back again in a few minutes" or "An AI review agent is analysing this pull request", the review is still running
   - In this case, inform the user: "⏳ Qodo review is still in progress. Please wait a few minutes and try again."
   - Exit early - don't try to parse incomplete reviews

3b. Deduplicate issues across multiple comments:
   - Qodo may post multiple comments (Compliance Guide, Code Suggestions, Code Review, etc.)
   - Issues may appear in multiple comments with slightly different wording
   - Deduplicate by:
     - Location (file path + line numbers)
     - Issue title/summary
   - Keep the most detailed version (prefer "Code Review" comment over "Code Suggestions")
   - If the same issue appears in multiple places, combine the agent prompts

4. Parse and display the issues:
   - Extract the review body/comments from Qodo's review
   - Parse out individual issues/suggestions
   - Identify severity (CRITICAL, HIGH, MEDIUM, LOW) and add corresponding emojis
   - Identify type (Compliance, Bug, Rule Violation, Security, Performance, etc.)
   - Extract location, issue description, and suggested fix
   - Extract the agent prompt from Qodo's suggestion (the description of what needs to be fixed)
   - Determine if each issue should be fixed or deferred based on severity and context

Severity levels:
- 🔴 CRITICAL - Must be fixed before merge
- 🟠 HIGH - Should be fixed, can be deferred if justified
- 🟡 MEDIUM - Should address, can be deferred to follow-up
- ⚪ LOW - Nice to have, can be deferred

Output format - Display as a markdown table:

Qodo Issues for PR #123: [PR Title]

| Severity | Issue Title | Issue Details | Type | Action |
|----------|-------------|---------------|------|--------|
| 🔴 CRITICAL | Test expects wrong behavior | • **Location:** tests/unittest/test_pr_questions.py:154<br><br>• **Issue:** Test assertion expects plain markdown when GFM is supported | Bug | Fix |
| 🟠 HIGH | Missing error handling | • **Location:** src/api/handler.py:42<br><br>• **Issue:** No exception handling for API calls | Rule Violation | Fix |
| 🟡 MEDIUM | Improve code readability | • **Location:** src/utils/parser.py:28<br><br>• **Issue:** Complex nested conditions hard to follow | Maintainability | Defer |
| ⚪ LOW | Add docstring | • **Location:** src/utils/helper.py:15<br><br>• **Issue:** Function missing docstring | Documentation | Defer |

Sort the table by severity (CRITICAL → HIGH → MEDIUM → LOW).

5. **Ask user for fix preference:**
   After displaying the table, ask the user how they want to proceed using AskUserQuestion:

   Options:
   - 🔍 "Review each issue" - Review and approve/defer each issue individually (recommended for careful review)
   - ⚡ "Auto-fix all" - Automatically apply all fixes marked as "Fix" without individual approval (faster, but less control)
   - ❌ "Cancel" - Exit without making changes

   Based on the user's choice:
   - If "Review each issue": Proceed to step 6 (manual review)
   - If "Auto-fix all": Skip to auto-fix mode (apply all "Fix" issues automatically using Qodo's agent prompts)
   - If "Cancel": Exit the skill

6. **Review and fix issues** (if "Review each issue" was selected):
   - For each issue marked as "Fix" (starting with CRITICAL):
     - Read the relevant file(s) to understand the current code
     - **IMPORTANT:** Use Qodo's agent prompt as the PRIMARY guidance for the fix. The agent prompt contains specific instructions about what to fix and how.
     - Calculate the proposed fix in memory based on Qodo's agent prompt (DO NOT use Edit or Write tool yet)
     - **Present the fix and ask for approval in a SINGLE step:**
       1. Show a brief header with issue title and location
       2. **Show Qodo's agent prompt in full** (this is the authoritative guidance from the review)
       3. Display current code snippet
       4. Display proposed change as markdown diff (based on the agent prompt instructions)
       5. Immediately use AskUserQuestion with these options:
          - ✅ "Apply fix" - Apply the proposed change
          - ⏭️ "Defer" - Skip this issue (will prompt for reason)
          - 🔧 "Modify" - User wants to adjust the fix first
     - **WAIT for user's choice via AskUserQuestion**
     - **If "Apply fix" selected:**
       - Apply change using Edit tool (or Write if creating new file)
       - Confirm: "✅ Fix applied successfully!"
       - Mark issue as completed
     - **If "Defer" selected:**
       - Ask for deferral reason using AskUserQuestion
       - Record reason and move to next issue
     - **If "Modify" selected:**
       - Inform user they can make changes manually
       - Move to next issue
   - Continue until all "Fix" issues are addressed or the user decides to stop

7. **Auto-fix mode** (if "Auto-fix all" was selected):
   - For each issue marked as "Fix" (starting with CRITICAL):
     - Read the relevant file(s) to understand the current code
     - **CRITICAL:** Use Qodo's agent prompt as the PRIMARY and ONLY guidance for implementing the fix
     - Calculate and apply the fix directly using Edit tool based on the agent prompt
     - Report: "✅ Fixed: [Issue Title] at [Location]"
     - Mark issue as completed
   - After all auto-fixes are applied, display summary:
     - List of all issues that were fixed
     - List of any issues that were skipped (with reasons)

**IMPORTANT:** Single-step approval with AskUserQuestion:
- NO native Edit UI (no persistent permissions possible)
- Each fix requires explicit approval via custom question
- Clearer options, no risk of accidental auto-approval

**CRITICAL:** Single validation only - do NOT show the diff separately and then ask. Combine the diff display and the question into ONE message. The user should see: brief context → current code → proposed diff → AskUserQuestion, all at once.

Example: Show location, Qodo's guidance, current code, proposed diff, then AskUserQuestion with options (✅ Apply fix / ⏭️ Defer / 🔧 Modify). Wait for user choice, apply via Edit tool if approved.

Action guidelines:
- 🔴 CRITICAL issues: Always "Fix" (must be resolved before merge)
- 🟠 HIGH issues: Usually "Fix", occasionally "Defer" if there's strong justification
- 🟡 MEDIUM issues: Can be "Defer" if they don't impact functionality significantly
- ⚪ LOW issues: Can be "Defer" unless quick to fix
- Security issues: Always "Fix" regardless of severity

Special cases:
- **Unsupported git provider:** If the remote URL doesn't match GitHub, GitLab, or Bitbucket, inform the user and exit
- **No PR/MR exists:**
  - Inform: "No PR/MR found for branch `<branch-name>`"
  - Ask: "Would you like me to create a PR/MR?"
  - If yes: Use appropriate CLI to create PR/MR (`gh pr create` / `glab mr create` / `bb pr create`), then inform "PR created! Qodo will review it shortly. Run this skill again in ~5 minutes."
  - If no: Exit skill
  - **IMPORTANT:** Do NOT proceed without a PR/MR
- **No Qodo review yet:**
  - Check if PR/MR has comments from Qodo bots (pr-agent-pro, qodo-merge[bot], etc.)
  - If no Qodo comments found: Inform "Qodo hasn't reviewed this PR/MR yet. Please wait a few minutes for Qodo to analyze it."
  - Exit skill (do NOT attempt manual review)
  - **IMPORTANT:** This skill only works with Qodo reviews, not manual reviews
- **Review in progress:** If "Come back again in a few minutes" message is found, inform user to wait and try again, then exit
- **Multiple comments:** Deduplicate issues by location and title, keeping the most detailed version
- **Missing CLI tool:** If the detected provider's CLI is not installed, provide installation instructions and exit

8. Post summary to PR/MR (ALWAYS):
   **REQUIRED:** After all issues have been reviewed (fixed or deferred), ALWAYS post a comment summarizing the actions taken, even if all issues were deferred:

   **GitHub:**
   ```bash
   gh pr comment <pr-number> --body "$(cat <<'EOF'
   ## Qodo Fix Summary

   Reviewed and addressed Qodo review issues:

   ### ✅ Fixed Issues
   - **Issue Title** (Severity) - Brief description of what was fixed

   ### ⏭️ Deferred Issues
   - **Issue Title** (Severity) - Reason for deferring

   ---
   *Generated by Qodo Fix skill*
   EOF
   )"
   ```

   **GitLab:**
   ```bash
   glab mr comment <mr-iid> --message "$(cat <<'EOF'
   ## Qodo Fix Summary
   [same format as above]
   EOF
   )"
   ```

   **Bitbucket:**
   ```bash
   bb pr comment <pr-id> --message "$(cat <<'EOF'
   ## Qodo Fix Summary
   [same format as above]
   EOF
   )"
   ```

   The summary should include:
   - Count of issues fixed vs deferred
   - List of fixed issues with their titles and severity
   - List of deferred issues with their titles, severity, and deferral reasons
   - Clear, concise formatting using markdown

   **After posting the summary, resolve the Qodo review comment:**

   Find the Qodo "Code Review by Qodo" comment ID and mark it as resolved to indicate the issues have been addressed.

   **GitHub:**
   ```bash
   # Get the Qodo comment ID
   COMMENT_ID=$(gh pr view <pr-number> --json comments --jq '.comments[] | select(.author.login | test("pr-agent-pro|qodo-merge|Codium-ai"; "i")) | select(.body | contains("Code Review by Qodo")) | .id' | head -1)

   # Resolve the comment (mark as resolved)
   # Note: GitHub doesn't have a direct "resolve comment" API for PR comments
   # The comment resolution happens at the review thread level
   # Add a thumbs-up reaction to indicate acknowledgment
   gh api "repos/{owner}/{repo}/issues/comments/$COMMENT_ID/reactions" -X POST -f content='+1'
   ```

   **GitLab:**
   ```bash
   # Get the Qodo comment/discussion ID
   DISCUSSION_ID=$(glab api "/projects/:id/merge_requests/<mr-iid>/discussions" --jq '.[] | select(.notes[].body | contains("Code Review by Qodo")) | .id' | head -1)

   # Resolve the discussion thread
   glab api "/projects/:id/merge_requests/<mr-iid>/discussions/$DISCUSSION_ID" -X PUT -f resolved=true
   ```

   **Bitbucket:**
   ```bash
   # Bitbucket Cloud API to resolve comment thread
   # Get comment ID, then mark as resolved
   bb api "/2.0/repositories/{workspace}/{repo}/pullrequests/<pr-id>/comments" --jq '.values[] | select(.content.raw | contains("Code Review by Qodo")) | .id'
   # Then update to resolved status
   ```

   If the resolve operation succeeds, inform: "✅ Marked Qodo review as resolved"
   If it fails (comment not found, API error), continue anyway - the summary comment is the important part

9. Commit changes to git:
   If any fixes were applied, commit the changes:

   ```bash
   git add <files-that-were-modified>
   git commit -m "fix: address Qodo review issues

   - Fixed: [list of fixed issues]
   - Deferred: [list of deferred issues with reasons]

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

   Then ask the user if they want to push to remote:
   - If yes: `git push`
   - If no: Inform them they can push later with `git push`

   **Important:** Only commit if at least one fix was applied. If all issues were deferred, skip the commit step.
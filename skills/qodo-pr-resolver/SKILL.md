---
name: qodo-pr-resolver
description: "Use when the user wants to review Qodo PR feedback or fix code review comments. Capabilities: view issues by severity, apply fixes interactively or in batch, reply to inline comments, post fix summaries (GitHub, GitLab, Bitbucket, Azure DevOps, Gerrit)"
triggers:
  - qodo.?pr.?resolver
  - pr.?resolver
  - resolve.?pr
  - qodo.?fix
  - fix.?qodo
  - qodo.?review
  - review.?qodo
  - qodo.?issues?
  - show.?qodo
  - get.?qodo
  - qodo.?resolve
---

# Qodo PR Resolver

Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision. Supports GitHub, GitLab, Bitbucket, Azure DevOps, and Gerrit.

## Prerequisites

### Required Tools:
- **Git** - For branch operations
- **Git Provider CLI** - One of: `gh` (GitHub), `glab` (GitLab), `curl` (Bitbucket/Gerrit), or `az` (Azure DevOps)

**Installation and authentication details:** See [providers.md](./resources/providers.md) for provider-specific setup instructions.

### Required Context:
- Must be in a git repository
- Repository must be hosted on a supported git provider (GitHub, GitLab, Bitbucket, Azure DevOps, or Gerrit)
- Current branch must have an open PR/MR (or Gerrit change)
- PR/MR must have been reviewed by Qodo (pr-agent-pro bot, qodo-merge[bot], etc.)

### Quick Check:
```bash
git --version                                    # Check git installed
git remote get-url origin                        # Identify git provider
```

See [providers.md](./resources/providers.md) for provider-specific verification commands.

## Understanding Qodo Reviews

Qodo (formerly Codium AI) is an AI-powered code review tool that analyzes PRs/MRs with compliance checks, bug detection, and code quality suggestions.

### Bot Identifiers
Look for comments from: **`pr-agent-pro`**, **`pr-agent-pro-staging`**, **`qodo-merge[bot]`**, **`qodo-ai[bot]`**

### Review Comment Types
1. **PR Compliance Guide** 🔍 - Security/ticket/custom compliance with 🟢/🟡/🔴/⚪ indicators
2. **PR Code Suggestions** ✨ - Categorized improvements with importance ratings
3. **Code Review by Qodo** - Structured issues with 🐞/📘/📎 sections and agent prompts (most detailed)

## Looping (opt-in)

By default this skill runs once. Pass `watch` or a trailing `every Nm`/`every Nh` to arm a recurring cron so new Qodo reviews after each push are picked up without re-typing the command.

- `/qodo-pr-resolver` → one-shot (default)
- `/qodo-pr-resolver watch` → arm 30-minute cron
- `/qodo-pr-resolver every 10m` → arm 10-minute cron
- `/qodo-pr-resolver once` → explicit one-shot (same as default)

**Mechanics:**

1. Run one pass per the steps below.
2. If looping was requested, at end of pass call `CronList` first; if a recurring `/qodo-pr-resolver` job already exists, skip and remind the user of its ID + cadence. Otherwise `CronCreate` with prompt `/qodo-pr-resolver`, `recurring: true`, and the chosen schedule. Surface the job ID so the user can `CronDelete <id>` later. 7-day session expiry is the backstop.
3. **Stop conditions:** PR not `OPEN` (closed/merged) — detect via Step 2's PR lookup, exit without arming the next cron. User says "stop"/"cancel" → `CronDelete` and confirm.
4. **Cron-fire re-entry:** when a fire re-enters the skill with the same prompt, run the pass as normal — step 2 above detects the existing job and skips re-arming.

Convert intervals to cron with off-minute offsets (e.g. `5m` → `3-59/5 * * * *`, not `*/5 * * * *`) to avoid fleet-alignment on the `:00`/`:30` marks. For intervals that don't cleanly divide their unit, pick the nearest clean one and tell the user what you rounded to.

## Instructions

When the user asks for a code review, to see Qodo issues, or fix Qodo comments:

### Step 0: Check code push status

Check for uncommitted changes, unpushed commits, and get the current branch.

**Note:** Only consider **tracked** files when checking for uncommitted changes. Untracked files (scripts, local configs, etc.) that are not part of the repository should be ignored. Use `git diff --name-only` and `git diff --cached --name-only` rather than `git status --porcelain` which includes untracked files.

#### Scenario A: Uncommitted changes exist

- Inform: "⚠️ You have uncommitted changes. These won't be included in the Qodo review."
- Ask: "Would you like to commit and push them first?"
- If yes: Wait for user action, then proceed to Step 1
- If no: Warn "Proceeding with review of pushed code only" and continue to Step 1

#### Scenario B: Unpushed commits exist

(no uncommitted changes)

- Inform: "⚠️ You have N unpushed commits. Qodo hasn't reviewed them yet."
- Ask: "Would you like to push them now?"
- If yes: Execute `git push`, inform "Pushed! Qodo will review shortly." Record internally `JUST_PUSHED = true`. Continue to Step 1 (the Wait for Qodo review flow in Step 3a will handle the waiting).
- If no: Warn "Proceeding with existing PR review" and continue to Step 1

#### Scenario C: Everything pushed

(both uncommitted changes and unpushed commits are empty)

- Proceed to Step 1

### Step 1: Detect git provider

Detect git provider from the remote URL (`git remote get-url origin`).

See [providers.md](./resources/providers.md) for provider detection patterns. For Gerrit, also check for `.gitreview` file, port 29418 in remote URL, or `googlesource.com` — see [gerrit.md](./resources/gerrit.md#provider-detection).

### Step 2: Find the open PR/MR

Find the open PR/MR for this branch using the provider's CLI.

See [providers.md § Find Open PR/MR](./resources/providers.md#find-open-prmr) for provider-specific commands. For Gerrit, look up the change using the `Change-Id` from the HEAD commit message — see [gerrit.md § Find Open Change](./resources/gerrit.md#find-open-change).

### Step 3: Get Qodo review comments

Get the Qodo review comments using the provider's CLI.

Qodo typically posts in three places: a **summary comment** (PR-level), **inline review comments** (one per issue), and on GitHub also as a **review submission body** — the optional message attached when a review is submitted. Qodo's main "Code Review by Qodo" sometimes lands here as a `CHANGES_REQUESTED` review rather than a free-standing comment, so missing this endpoint = missing findings. Fetch all three surfaces.

See [providers.md § Fetch Review Comments](./resources/providers.md#fetch-review-comments) for provider-specific commands.

**Fetch in parallel.** Once Step 2 returns the PR number, fire the three comment endpoints (plus the provider's current-user lookup for own-comment filtering and `git log -5 --oneline` for commit-style matching in Step 6/7) as parallel tool calls in a single assistant message — not as a serial chain. Latency gains matter most on self-hosted providers. If any single call returns rate-limited (403), retry just that one serially after a brief wait; the bucket is shared but parallel batches of 5–6 are usually fine.

Look for comments where the author is "qodo-merge[bot]", "pr-agent-pro", "pr-agent-pro-staging" or similar Qodo bot name. For review submissions, skip entries with empty `body` unless `state` is `CHANGES_REQUESTED`.

**Gerrit note:** Qodo posts as **tagged human comments** via `/comments` with `tag: "autogenerated:qodo"`. Also check change messages (`/messages`) for the summary comment. Filter by `tag` field or bot username. See [gerrit.md § Fetch Review Comments](./resources/gerrit.md#fetch-review-comments).

#### Step 3a: Check if review is ready / Wait for Qodo review

Check if the Qodo review is complete:
- If any comment contains "Come back again in a few minutes" or "An AI review agent is analysing this pull request", the review is still running
- If no Qodo bot comments are found at all, the review hasn't started yet

If the review is **not ready** (in progress, not started, or we just pushed/created a PR):

1. Ask using AskUserQuestion: "⏳ Qodo review is not ready yet. Would you like to wait for it to complete?"
   - Options: **"Wait for review" (Recommended)** / "Exit and come back later"
2. If **"Exit and come back later"**: Inform "Run this skill again in a few minutes once Qodo has reviewed the PR." Exit skill.
3. If **"Wait for review"**:
   - Inform: "Monitoring for Qodo review completion (checking every 30 seconds)..."
   - Use the **Monitor** tool to poll for review completion:
     - `description`: "Waiting for Qodo review on PR #<number>"
     - `timeout_ms`: `600000` (10 minutes)
     - `persistent`: `false`
     - `command`: A polling script that runs in a `while true; do ... sleep 30; done` loop. The script should use the **same provider-specific comment-fetch commands from Step 3** (Fetch Review Comments) to check for Qodo bot comments. If Qodo comments are found AND they do not contain "Come back again in a few minutes" or "An AI review agent is analysing this pull request", output `REVIEW_COMPLETE` and exit. Use `|| true` on API calls for transient failure resilience.
   - When the Monitor emits `REVIEW_COMPLETE`: Inform "Qodo review is ready!" and **return to Step 3** to fetch and parse the review comments normally.
   - If the Monitor times out (10 minutes): Inform "Qodo review hasn't appeared yet. You can run this skill again later." Exit skill.

If the review **is ready** (Qodo comments found, no "in progress" markers): Proceed directly to Step 3b.

#### Step 3b: Deduplicate issues

Deduplicate issues across summary and inline comments:

- Qodo posts each issue in two places: once in the **summary comment** (PR-level) and once as an **inline review comment** (attached to the specific code line). These will share the same issue title.
- Qodo may also post multiple summary comments (Compliance Guide, Code Suggestions, Code Review, etc.) where issues can overlap with slightly different wording.
- Deduplicate by matching on **issue title** (primary key - the same title means the same issue):
  - If an issue appears in both the summary comment and as an inline comment, merge them into a single issue
  - Prefer the **inline comment** for file location (it has the exact line context)
  - Prefer the **summary comment** for severity, type, and agent prompt (it is more detailed)
  - **IMPORTANT:** Preserve each issue's **inline review comment ID** — you will need it later (Step 8) to reply directly to that comment with the decision
- Also deduplicate across multiple summary comments by location (file path + line numbers) as a secondary key
- If the same issue appears in multiple places, combine the agent prompts
- **Review submission bodies (GitHub)** — treat as a summary-comment equivalent during dedup. If the body lists issues whose titles match inline comments, merge by title. Use the review's `html_url` (ending in `#pullrequestreview-<id>`) as the canonical reference; review bodies have no REST reactions endpoint (use GraphQL `addReaction` fallback if needed)

**Gerrit deduplication:** Qodo inline comments contain an **Agent Prompt** section (rendered as plain text — Gerrit doesn't support expandable blocks) with detailed fix instructions. When deduplicating, preserve the Agent Prompt from each unique finding.

#### Step 3c: Detect clusters (root-cause consolidation)

Dedup-by-title catches the obvious duplicates. It misses **clusters** — multiple findings with different titles but one root cause (e.g. three "missing null check" issues that share an unvalidated input path; four "unused import" findings from one module reshuffle; five suggestions that all point at a missing helper).

After Step 3b returns the deduplicated set, run a single synthesis pass:

- Group by **file proximity** — issues in the same file within ±50 lines of each other.
- Group by **shared theme keywords** — title or agent-prompt overlap on terms like "null check", "await", "validation", "logging", "error handling".

If at least one cluster is found, surface it to the user **ONCE at the start of Step 6** via AskUserQuestion:

> "Issues 2, 4, 7 all touch the retry logic — handle as one architectural change or one-by-one?"
>
> Options: "Handle together" / "One-by-one (default)" / "Skip cluster, address others"

Don't auto-merge — the "ask, don't decide" framing avoids false clustering (sometimes co-location is coincidence). If the user picks "Handle together", route the cluster through Step 6 once with combined agent prompts and post N inline replies pointing at the consolidating commit.

Why this matters: Qodo's per-line granularity often surfaces 3–4 inline comments for one underlying smell. Stepping through each separately wastes time and produces messy commit history.

### Step 4: Parse and display the issues

- Extract the review body/comments from Qodo's review
- Parse out individual issues/suggestions
- **IMPORTANT: Preserve Qodo's exact issue titles verbatim** — do not rename, paraphrase, or summarize them. Use the title exactly as Qodo wrote it.
- **IMPORTANT: Preserve Qodo's original ordering** — display issues in the same order Qodo listed them. Qodo already orders by severity.
- Extract location, issue description, and suggested fix
- Extract the agent prompt from Qodo's suggestion (the description of what needs to be fixed)

#### Severity mapping

Derive severity from Qodo's action level and position:

1. **Action level determines severity range:**
   - **"Action required"** issues → Can only be 🔴 CRITICAL or 🟠 HIGH
   - **"Review recommended"** / **"Remediation recommended"** issues → Can only be 🟡 MEDIUM or ⚪ LOW
   - **"Other"** / **"Advisory comments"** issues → Always ⚪ LOW (lowest priority)

2. **Qodo's position within each action level determines the specific severity:**
   - Group issues by action level ("Action required" vs "Review recommended" vs "Other")
   - Within "Action required" and "Review recommended" groups: earlier positions → higher severity, later positions → lower severity
   - Split point: roughly first half of each group gets the higher severity, second half gets the lower
   - All "Other" issues are treated as ⚪ LOW regardless of position

**Example:** 7 "Action required" issues would be split as:
- Issues 1-3: 🔴 CRITICAL
- Issues 4-7: 🟠 HIGH
- Result: No MEDIUM or LOW issues (because there are no "Review recommended" or "Other" issues)

**Example:** 5 "Action required" + 3 "Review recommended" + 2 "Other" issues would be split as:
- Issues 1-2 or 1-3: 🔴 CRITICAL (first ~half of "Action required")
- Issues 3-5 or 4-5: 🟠 HIGH (second ~half of "Action required")
- Issues 6-7: 🟡 MEDIUM (first ~half of "Review recommended")
- Issue 8: ⚪ LOW (second ~half of "Review recommended")
- Issues 9-10: ⚪ LOW (all "Other" issues)

**Action guidelines:**
- 🔴 CRITICAL / 🟠 HIGH ("Action required"): Always "Fix"
- 🟡 MEDIUM ("Review recommended"): Usually "Fix", can "Defer" if low impact
- ⚪ LOW ("Review recommended" or "Other"): Can be "Defer" unless quick to fix; "Other" issues are lowest priority

#### Output format

**IMPORTANT: Use actual Unicode emoji characters** (e.g. `🔴`, `🟠`, `📘`, `⛨`, `⚙`), NOT GitHub-style shortcodes (`:red_circle:`, `:books:`, `:shield:`). Shortcodes do not render in terminal environments.

Display as a markdown table in Qodo's exact original ordering (do NOT reorder by severity - Qodo's order IS the severity ranking):

```
Qodo Issues for PR #123: [PR Title]

| # | Severity | Issue Title | Issue Details | Type | Action |
|---|----------|-------------|---------------|------|--------|
| 1 | 🔴 CRITICAL | Insecure authentication check | • **Location:** src/auth/service.py:42<br><br>• **Issue:** Authorization logic is inverted | 🐞 Bug ⛨ Security | Fix |
| 2 | 🔴 CRITICAL | Missing input validation | • **Location:** src/api/handlers.py:156<br><br>• **Issue:** User input not sanitized before database query | 📘 Rule violation ⛯ Reliability | Fix |
| 3 | 🟠 HIGH | Database query not awaited | • **Location:** src/db/repository.py:89<br><br>• **Issue:** Async call missing await keyword | 🐞 Bug ✓ Correctness | Fix |
```

### Step 5: Ask user for fix preference

After displaying the table, ask the user **two questions in one AskUserQuestion call** (the tool supports up to 4 questions per invocation):

**Question 1 — How to proceed?**
- 🔍 "Review each issue" - Review and approve/defer each issue individually (recommended for careful review)
- ⚡ "Auto-fix all" - Automatically apply all fixes marked as "Fix" without individual approval (faster, but less control)
- ❌ "Cancel" - Exit without making changes

**Question 2 — Auto-resolve threads after fix/defer?**
- ✅ "Yes" - Set `unresolved: false` on inline replies; mark the main Qodo review comment resolved. Faster cleanup; Qodo re-evaluates on next pass.
- 🟡 "No" - Leave threads unresolved so human teammates can still see the discussion; only react 👍 on acknowledgments.

Record Question 2's answer as `AUTO_RESOLVE = true|false`. Step 8's resolution rules and Step 9's chain depend on it.

**Based on Question 1's choice:**
- If "Review each issue": Proceed to Step 6 (manual review)
- If "Auto-fix all": Skip to Step 7 (auto-fix mode - apply all "Fix" issues automatically using Qodo's agent prompts)
- If "Cancel": Exit the skill

### Step 6: Review and fix issues (manual mode)

If "Review each issue" was selected:

- For each issue marked as "Fix" (starting with CRITICAL):
  - Read the relevant file(s) to understand the current code
  - **Premise check:** before applying, ask once — does this finding still apply given current code + repo context? Qodo can be wrong (false positives on test fixtures, wrong-language idiom suggestions, refactor proposals that don't fit the codebase). If the premise is wrong → skip the fix and defer with reason `"Qodo premise incorrect: <one-liner>"`. Step 8's reply will explain to Qodo; the next review pass will see and adjust.
  - Implement the fix by **executing the Qodo agent prompt as a direct instruction**. The agent prompt is the fix specification — follow it literally, do not reinterpret or improvise a different solution. Only deviate if the prompt is clearly outdated relative to the current code (e.g. references lines that no longer exist).
  - Calculate the proposed fix in memory (DO NOT use Edit or Write tool yet)
  - **Present the fix and ask for approval in a SINGLE step:**
    1. Show a brief header with issue title and location
    2. **Show Qodo's agent prompt in full** so the user can verify the fix matches it
    3. Display current code snippet
    4. Display proposed change as markdown diff
    5. Immediately use AskUserQuestion with these options:
       - ✅ "Apply fix" - Apply the proposed change
       - ⏭️ "Defer" - Skip this issue (will prompt for reason)
       - 🔧 "Modify" - User wants to adjust the fix first
  - **WAIT for user's choice via AskUserQuestion**
  - **If "Apply fix" selected:**
    - Apply change using Edit tool (or Write if creating new file)
    - **GitHub / GitLab / Bitbucket / Azure DevOps:** Git commit the fix: `git add <modified-files> && git commit -m "fix: <issue title>"`
    - **Gerrit:** Do NOT commit yet — stage the change (`git add <modified-files>`) but wait until all fixes are applied, then amend into a single commit (see Gerrit note below)
    - Confirm: "✅ Fix applied!"
    - Mark issue as completed
  - **If "Defer" selected:**
    - Ask for deferral reason using AskUserQuestion
    - Record reason and move to next issue
  - **If "Modify" selected:**
    - Inform user they can make changes manually
    - Move to next issue
- Continue until all "Fix" issues are addressed or the user decides to stop
- **After all fixes are applied**, reply to all Qodo inline comments in one batch (see Step 8)

**Gerrit commit strategy:** In Gerrit, each commit becomes a separate change. To keep all fixes as a single new patchset on the existing change:
1. Apply all fixes (Edit tool) and stage them (`git add`)
2. After ALL fixes are done, amend the original commit: `git commit --amend --no-edit`
3. Push once in Step 9

Do NOT create individual commits per fix for Gerrit.

#### Important notes

**Single-step approval with AskUserQuestion:**
- NO native Edit UI (no persistent permissions possible)
- Each fix requires explicit approval via custom question
- Clearer options, no risk of accidental auto-approval

**CRITICAL:** Single validation only - do NOT show the diff separately and then ask. Combine the diff display and the question into ONE message. The user should see: brief context → current code → proposed diff → AskUserQuestion, all at once.

**Example:** Show location, Qodo's guidance, current code, proposed diff, then AskUserQuestion with options (✅ Apply fix / ⏭️ Defer / 🔧 Modify). Wait for user choice, apply via Edit tool if approved.

### Step 7: Auto-fix mode

If "Auto-fix all" was selected:

- For each issue marked as "Fix" (starting with CRITICAL):
  - Read the relevant file(s) to understand the current code
  - **Premise check:** quick sanity pass — if Qodo's finding is clearly wrong relative to the current code (premise no longer holds), mark the issue deferred with reason `"Qodo premise incorrect: <one-liner>"` and continue. Do not pause for user input in auto-fix mode; record the decision for Step 8's summary.
  - Implement the fix by **executing the Qodo agent prompt as a direct instruction**. The agent prompt is the fix specification — follow it literally, do not reinterpret or improvise a different solution. Only deviate if the prompt is clearly outdated relative to the current code (e.g. references lines that no longer exist).
  - Apply the fix using Edit tool
  - **GitHub / GitLab / Bitbucket / Azure DevOps:** Git commit the fix: `git add <modified-files> && git commit -m "fix: <issue title>"`
  - **Gerrit:** Stage only (`git add <modified-files>`) — do NOT commit yet
  - Report each fix with the agent prompt that was followed:
    > ✅ **Fixed: [Issue Title]** at `[Location]`
    > **Agent prompt:** [the Qodo agent prompt used]
  - Mark issue as completed
- **Gerrit:** After ALL fixes are applied, amend into one commit: `git commit --amend --no-edit`
- Reply to all Qodo inline comments in one batch (see Step 8)
- After all auto-fixes are applied, display summary:
  - List of all issues that were fixed
  - List of any issues that were skipped (with reasons)

### Step 8: Prepare summary and replies (DO NOT post yet)

After all issues have been reviewed (fixed or deferred), **draft** the summary comment AND the per-issue inline replies into temp files. **Do not post them yet** — they fire in Step 9's atomic chain so Qodo's webhook re-scan sees the push, summary, and replies as one event. Posting the summary before the push lets the bot re-flag just-fixed issues during the re-scan window.

See [providers.md § Post Summary Comment](./resources/providers.md#post-summary-comment) and [§ Reply to Inline Comments](./resources/providers.md#reply-to-inline-comments) for provider-specific commands and the reply format. **REQUIRED:** always draft a summary, even if all issues were deferred.

**Gerrit exception:** Gerrit's unified `/review` endpoint already batches summary + replies into a single atomic API call — see [gerrit.md § Post Summary Comment](./resources/gerrit.md#post-summary-comment). The chaining concern (next step) is GitHub/GitLab/Bitbucket/Azure DevOps only.

**Important resolution rules for inline replies** (depend on `AUTO_RESOLVE` from Step 5):
- If `AUTO_RESOLVE = true`: set `"unresolved": false` on both Fixed and Deferred replies (resolves the thread; Qodo re-evaluates next pass).
- If `AUTO_RESOLVE = false`: omit the `unresolved` field (leave threads unresolved so human teammates can still see the discussion). Replies still post normally; only the resolution state is skipped.

**Also prepare the Qodo review-comment acknowledgment.** Find the Qodo "Code Review by Qodo" comment ID. If `AUTO_RESOLVE = true`, prepare the resolve command; otherwise prepare only the 👍 reaction. Either fires as part of Step 9's chain. See [providers.md § Resolve Qodo Review Comment](./resources/providers.md#resolve-qodo-review-comment).

### Step 9: Atomic publish — push + summary + replies

Chain the push, summary post, inline replies, and Qodo-comment resolution into a **single approval gate**. **Why:** webhook-driven bots (including Qodo itself) re-scan the PR on push events. If the summary and replies don't land in the same webhook window as the push, the bot may re-flag the just-fixed issues because the post-push state doesn't yet include the acknowledgments.

**Order matters:** push must precede the summary (the summary may reference SHAs); summary must precede inline replies (replies may cite the summary URL). Use `&&` short-circuit semantics — the chain stops at the first failure, by design: a failed push doesn't leave a summary citing unpushed commits, and a failed summary doesn't leave replies citing a non-existent summary URL. If you want "best-effort replies" after a summary failure, don't use a pure `&&` chain — handle the missing summary URL explicitly.

Ask for approval on the bundle as one unit ("approve push + summary + N replies + resolve?"). The "ask before push" rule still applies, but it's one gate, not many. Clean up the temp files after the command succeeds. If resolve/reaction fails, continue — the summary is the important part.

See [providers.md § Atomic Publish](./resources/providers.md#atomic-publish-push--summary--replies) for the chained command per provider.

**If all issues were deferred**, there are no commits to push — skip `git push`, post the summary + replies as a chained command without the push prefix.

**Gerrit:** Step 9 is just the push (`git push origin HEAD:refs/for/<target-branch>`) — Step 8's unified `/review` POST already published summary + replies. See [gerrit.md § Push Changes](./resources/gerrit.md#push-changes).

### Step 9b: Handle draft PR status

**Only run this step if `DRAFT_PR_CREATED = true`** (a draft PR was created earlier in this session). Skip entirely if the PR already existed or was created as a regular PR.

- Ask using AskUserQuestion: "We opened this PR as a draft. Would you like to mark it as ready for review, or keep it as a draft?"
  - Options: **"Mark as ready for review"** / "Keep as draft"
- If **"Mark as ready for review"**: Use provider CLI to mark PR as ready (see [providers.md § Mark PR Ready for Review](./resources/providers.md#mark-pr-ready-for-review)). Inform: "PR marked as ready for review!"
- If **"Keep as draft"**: Inform: "PR will remain as a draft. You can mark it ready later."

### Step 10: Show PR URL

After completing all steps, always echo the PR/MR URL to the user so they can easily navigate to it. Use the PR URL detected in Step 2.

Example output: `🔗 PR: https://github.com/owner/repo/pull/123`
For Gerrit: `🔗 Change: https://<gerrit-host>/c/<project>/+/<change-number>`

### Special cases

#### Unsupported git provider

If the remote URL doesn't match GitHub, GitLab, Bitbucket, Azure DevOps, or Gerrit, inform the user and exit.

See [providers.md § Error Handling](./resources/providers.md#error-handling) for details.

#### No PR/MR exists

- Inform: "No PR/MR found for branch `<branch-name>`. A PR is needed to trigger a Qodo review."
- **For non-Gerrit providers**, ask using AskUserQuestion: "How would you like to proceed?"
  - **"Open draft PR" (Recommended)** — Create a draft PR since the code isn't finalized yet. Use provider CLI with draft flag (see [providers.md § Create PR/MR](./resources/providers.md#create-prmr)). **Record internally:** `DRAFT_PR_CREATED = true` and save the PR number/ID. Inform "Draft PR created!" then proceed to the **Wait for Qodo review** flow (Step 3a).
  - **"Open PR"** — Create a regular (non-draft) PR. Use provider CLI without draft flag (see [providers.md § Create PR/MR](./resources/providers.md#create-prmr)). Set `DRAFT_PR_CREATED = false`. Inform "PR created!" then proceed to the **Wait for Qodo review** flow (Step 3a).
  - **"I'll open it manually"** — Inform: "No problem! Open the PR yourself, then run this skill again once the PR exists and Qodo has reviewed it." Exit skill.
- **For Gerrit**, ask: "Would you like me to create a change?" If yes, push with `git push origin HEAD:refs/for/<branch>` (see [gerrit.md § Create Change](./resources/gerrit.md#create-change)). Then proceed to the **Wait for Qodo review** flow (Step 3a). If no, exit skill.

**IMPORTANT:** Do NOT proceed to Step 3b without a PR/MR. This skill only works with Qodo reviews, not manual reviews.

#### No Qodo review yet / Review in progress

Handled by Step 3a — proceeds to the **Wait for Qodo review** flow.

#### Missing CLI tool

If the detected provider's CLI is not installed, provide installation instructions and exit.

See [providers.md § Error Handling](./resources/providers.md#error-handling) for provider-specific installation commands.

#### Inline reply commands

Used per-issue in Steps 6 and 7 to reply to Qodo's inline comments:

Use the inline comment ID preserved during deduplication (Step 3b) to reply directly to Qodo's comment.

See [providers.md § Reply to Inline Comments](./resources/providers.md#reply-to-inline-comments) for provider-specific commands and reply format. For Gerrit, all replies go through a single unified endpoint and can be batched — see [gerrit.md § Reply to Comments](./resources/gerrit.md#reply-to-comments).

Keep replies short (one line). If a reply fails, log it and continue.

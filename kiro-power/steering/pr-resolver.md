# Qodo PR Resolver

Load this steering file when the user wants to read a **Qodo PR/MR review** — check its status or freshness, see what's open, prepare local fixes when explicitly requested, or watch a PR until its review comes back clean.

This delegates to the **Qodo CLI** (`qodo pr-review-session findings`), which reads the review from Qodo's DB — **structured and git-provider-agnostic**. Do **not** scrape rendered Qodo review comments with provider CLIs or APIs; that view is lossy and can be stale. Plain forge metadata reads such as the PR URL or head SHA are allowed for locating the PR and checking freshness. The Qodo call and default workflow are report-only; local fixes require an explicit request.

## UX and Safety Rules

- Run the `qodo` CLI for the review itself, not per-provider review-comment reads. One managed read gives you every finding with its status.
- **Never post to the git forge.** The review tool is read-only. Never call comment, approval, label, description, dismissal, or other forge-write tools to "resolve" a finding.
- **Report first.** If the user asked only for status/findings, fetch, assess, report, and stop. Prepare local fixes only when explicitly requested and confirm the edit scope first. This capability never commits or pushes; hand local changes back uncommitted.
- **Stay in scope** — apply the fix a finding describes; don't run test suites, debug, or change unrelated code. If a clean fix needs broader work, skip it with that reason.
- Don't dump raw JSON at the user and never print secrets/config. Lead with a short status (how many findings, how many open).
- On `MT-RATE-LIMITED` / `MT-TOOL-LOOP` / `MT-UPSTREAM-DOWN`: stop or back off — don't spin.

## Locate the CLI + auth (shared)

The CLI requires **Node.js ≥ 20**. `qodo` may be "command not found" (GUI shells have a minimal PATH) — use `~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo`). Missing there too → install with `curl -fsSL https://get.qodo.ai/install.sh | sh`.

Run `qodo whoami --json` first without surfacing its raw output. On failure, tell the user to run `qodo login` and stop. Confirm flags with `qodo pr-review-session findings --help`, then inspect `qodo tools --json` internally and require `name: "get-pr-review-findings"`, `toolset: "pr_review_session"`, `mutating: false`. If authenticated discovery fails, refresh the catalog once and retry once; otherwise stop. Never pass `--idempotency-key` in this read capability.

## Workflow

1. **Get the PR URL and head SHA.** If the user gave a URL, use it and read the head as plain forge metadata (for GitHub: `gh pr view <URL> --json headRefOid`). Otherwise fetch the current branch's open PR in a **single** provider-CLI command — `gh pr view --json url,title,state,headRefOid` (GitHub), `glab mr view` (GitLab), etc. — don't run separate `git branch` / `git remote` / list commands. Confirm an inferred PR with the user before fetching findings; never guess a URL.
2. **Fetch the review:**
   `qodo pr-review-session findings --pr-url <URL> [--git-provider github|gitlab|bitbucket|ado] --json`
   (confirm exact flags with `qodo pr-review-session findings --help`). Returns `review_session` (`status`, `commit_sha`, `started_at`) and `findings[]` (`title`, `description`, `category`, `action_level`, `attribution_status`, comment IDs). `review_session: null` → no review yet; tell the user and stop.
3. **Trust only a completed review of the current commit.** If `status` isn't a completed/terminal state, the review is mid-flight and findings are provisional. Reviews may remain in `started` for several minutes — and the **first** review on a newly-connected repo can take noticeably longer while Qodo indexes it — so give the user a short status update and use the bounded watch behavior below; never stay in "Working" indefinitely. If `commit_sha` is behind the PR head, findings are stale — wait for the review to catch up. Don't fix on a running or lagging review.
4. **Triage and report.** `attribution_status`: `pending` = open, `implemented` = already addressed, `dismissed` = closed. Order by `action_level` (`action_required` → `remediation_recommended` → `informational`). Honor any user filter and report every out-of-scope or closed finding rather than silently dropping it. For report-only requests, stop here.
5. **Prepare local fixes only when requested.** Findings are a strong second opinion, **not gospel**. After confirming the edit scope, fix sound in-scope findings locally, matching surrounding style (use only codebase-wisdom's non-mutating Qodo read tools to locate code). Skip wrong/already-satisfied findings with a one-line reason. Never degrade correct code to silence a finding.
6. **Hand off without committing or pushing.** Tell the user what changed and what remains. If the user or their workflow later pushes a fix, a subsequent read-only fetch can observe Qodo's re-attribution; this capability never marks findings resolved itself.

## Two modes

- **Once (default):** fetch → assess → report → stop. If the user explicitly requested fixes, confirm scope, prepare them locally, and hand them back uncommitted.
- **Watch until clean** (only when explicitly asked): poll the same read-only command until the review is `completed` and its `commit_sha` equals the externally updated head. If local fixes are prepared, pause while the user or their workflow pushes; resume only when asked. **Bound it** — stop after a few no-progress rounds and hand back.

Lead with the bottom line: how many findings, how many remain open, and—when fixes were requested—how many were prepared locally. A short, accurate status beats a wall of finding text.

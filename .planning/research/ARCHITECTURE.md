# Architecture Research

**Domain:** GitHub Actions CI/CD — Slack notification automation on PR merge
**Researched:** 2026-03-02
**Confidence:** HIGH (backed by official GitHub Docs, official Slack Docs, and official action repositories)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Event Layer                       │
│   PR merged to main → push event fires on target branch     │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│              GitHub Actions Workflow (.github/workflows/)    │
│                                                             │
│  ┌──────────────────┐   ┌─────────────────────────────────┐ │
│  │  actions/checkout │   │  tj-actions/changed-files       │ │
│  │  (fetch-depth: 0) │──▶│  (files: skills/**)            │ │
│  └──────────────────┘   │  (dir_names: true)              │ │
│                          │  → output: all_changed_files    │ │
│                          └───────────────┬─────────────────┘ │
│                                          │                   │
│                          ┌───────────────▼─────────────────┐ │
│                          │  Build message step (bash)       │ │
│                          │  - PR title, author, link        │ │
│                          │  - Changed skills list           │ │
│                          └───────────────┬─────────────────┘ │
│                                          │                   │
│                          ┌───────────────▼─────────────────┐ │
│                          │  slackapi/slack-github-action    │ │
│                          │  (incoming webhook method)       │ │
│                          └───────────────┬─────────────────┘ │
└──────────────────────────────────────────┼──────────────────┘
                                           │
┌──────────────────────────────────────────▼──────────────────┐
│                     Slack Platform Layer                     │
│   Incoming Webhook → #qodo-skills-releases channel           │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Workflow trigger | Fires on PR merge to main | `on: push: branches: [main]` or `pull_request` closed + merged |
| `actions/checkout` | Fetches repo with commit history for diff | `fetch-depth: 0` (full history) or `fetch-depth: 2` (last 2 commits) |
| `tj-actions/changed-files` | Lists which `skills/` subdirectories changed | `files: skills/**`, `dir_names: true`, `dir_names_max_depth: 2` |
| Message builder | Assembles Slack payload from GitHub context | Bash step using `${{ github.event }}` context variables |
| `slackapi/slack-github-action` | Posts formatted message to Slack | Incoming webhook with JSON Block Kit payload |
| GitHub Secrets | Stores webhook URL out of source code | Repository secret `SLACK_WEBHOOK_URL` |
| Slack App + Webhook | Accepts POST and delivers to channel | Slack app configured with incoming webhook for `#qodo-skills-releases` |

## Recommended Project Structure

```
.github/
└── workflows/
    └── notify-skill-changes.yml   # Single workflow file — the entire implementation
```

### Structure Rationale

- **Single workflow file:** The entire pipeline is one file. No library code, no scripts directory. The workflow itself contains the bash for message assembly. Keeps the diff reviewable and the intent obvious.
- **No shared scripts:** Avoid a separate `scripts/` or `bin/` directory — the bash embedded in the workflow steps is simple enough (a few variable assignments and string construction) that extraction adds complexity without benefit.

## Architectural Patterns

### Pattern 1: Push Trigger (Recommended over `pull_request` closed)

**What:** Trigger on `push` to the main branch rather than `pull_request: types: [closed]`.

**When to use:** Always for this project. GitHub merging a PR produces a push event on the target branch. The push event is reliable and runs the workflow from the target branch context (no cross-fork security concerns).

**Trade-offs:** The push event does not natively carry PR metadata (title, author, PR number). These must be retrieved via the `${{ github.event }}` context or the GitHub API step. However, for a PR-only workflow this is a known and common pattern.

**Example:**
```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'skills/**'
```

Adding `paths: skills/**` ensures the workflow only runs when skill files actually changed — no notification for README-only merges unless explicitly desired.

### Pattern 2: Changed Files Detection with `dir_names`

**What:** Use `tj-actions/changed-files` with `dir_names: true` to get the list of top-level subdirectory names under `skills/` that were touched, not individual file paths.

**When to use:** Any time you need "which skills changed" rather than "which files changed". This produces a clean list like `skills/qodo-get-rules skills/qodo-pr-resolver` rather than `skills/qodo-get-rules/SKILL.md skills/qodo-get-rules/AGENTS.md`.

**Trade-offs:** `dir_names_max_depth` must be set to `2` to get `skills/qodo-get-rules` rather than `skills` (depth 1) or `skills/qodo-get-rules/references` (depth 3). Slightly surprising default behavior.

**Example:**
```yaml
- uses: tj-actions/changed-files@v47
  id: changed-skills
  with:
    files: skills/**
    dir_names: true
    dir_names_max_depth: '2'

- name: Show changed skills
  run: echo "${{ steps.changed-skills.outputs.all_changed_files }}"
```

### Pattern 3: Incoming Webhook for Slack (Recommended over Bot Token)

**What:** Create a Slack app with an incoming webhook scoped to `#qodo-skills-releases`. Store the webhook URL as a GitHub secret. Use `slackapi/slack-github-action` (official, Slack-maintained) to POST the message.

**When to use:** Single-channel notifications with no need to update messages, post threads, or look up users. Incoming webhooks are simpler to set up (no OAuth flow, no scopes to configure) and are appropriate for this use case.

**Trade-offs:** Webhooks are channel-scoped at creation time. If the channel needs to change, a new webhook must be created. Bot tokens are more flexible but require managing OAuth scopes, which is overhead not needed here.

**Example:**
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v2
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
    webhook-type: incoming-webhook
    payload: |
      {
        "text": "Skill update merged: ${{ github.event.head_commit.message }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Skills updated:* ${{ steps.changed-skills.outputs.all_changed_files }}\n*PR:* <${{ github.event.pull_request.html_url }}|${{ github.event.pull_request.title }}>\n*By:* ${{ github.event.pull_request.user.login }}"
            }
          }
        ]
      }
```

## Data Flow

### Request Flow: PR merge to Slack message

```
Developer merges PR to main
    │
    ▼
GitHub fires `push` event on main branch
    │
    ▼
Workflow trigger evaluates paths filter
  - If skills/** changed → workflow runs
  - Otherwise → workflow skipped
    │
    ▼
actions/checkout (fetch-depth: 0)
  - Full git history available for diff
    │
    ▼
tj-actions/changed-files
  - Diffs HEAD vs HEAD~1
  - Filters to skills/** paths
  - dir_names: true → extracts subdirectory names
  - Output: all_changed_files = "skills/qodo-get-rules skills/qodo-pr-resolver"
    │
    ▼
Bash step: extract PR metadata from github.event context
  - PR title: github.event.pull_request.title (N/A on push — use head_commit.message or API)
  - PR author: github.event.pusher.name or github.actor
  - PR link: constructed from github.event.repository.html_url + /pull/NUMBER
  - Changed skills: strip "skills/" prefix from dir list
    │
    ▼
slackapi/slack-github-action@v2
  - HTTP POST to SLACK_WEBHOOK_URL
  - Payload: JSON with text + blocks (mrkdwn formatting)
    │
    ▼
Slack delivers message to #qodo-skills-releases
```

### Key Data Flows

1. **PR metadata on push event:** When using `on: push`, the `github.event.pull_request` context is NOT available (it's null). PR title/number must come from either (a) the commit message convention, (b) the GitHub API step using `gh pr list --search ${{ github.sha }}`, or (c) switching to `pull_request_target: types: [closed]` which does have full PR context. This is the main architectural decision to resolve.

2. **Changed skill names:** `tj-actions/changed-files` with `dir_names: true` and `dir_names_max_depth: 2` outputs space-separated paths like `skills/foo skills/bar`. A bash step strips the `skills/` prefix to produce a clean list: `foo, bar`.

3. **Webhook URL secret flow:** URL stored in GitHub repository secrets → injected as env var at runtime → never logged (GitHub masks secret values in logs automatically).

## Suggested Build Order

These components have dependencies that dictate implementation order:

```
1. Slack app + webhook URL      ← no code dependency; external setup
       │
       ▼
2. GitHub secret SLACK_WEBHOOK_URL  ← requires webhook URL from step 1
       │
       ▼
3. #qodo-skills-releases channel  ← Slack setup; can be done in parallel with 1-2
       │
       ▼
4. Workflow YAML skeleton         ← requires secret name decided in step 2
   (trigger + checkout only)
       │
       ▼
5. Changed-files detection step   ← requires checkout step from step 4
       │
       ▼
6. Message assembly step          ← requires changed-files output from step 5
       │
       ▼
7. Slack notify step              ← requires message + secret from steps 2 and 6
       │
       ▼
8. End-to-end test (real merge)   ← requires all steps 1-7 complete
```

**Why this order:** Slack setup (webhook URL) must precede GitHub secrets, which must precede the workflow. The workflow steps build on each other sequentially within the YAML. Testing requires a real merge to main, so it comes last.

## Anti-Patterns

### Anti-Pattern 1: Storing Webhook URL in Workflow YAML

**What people do:** Hard-code `https://hooks.slack.com/services/T.../B.../...` directly in the YAML file.

**Why it's wrong:** The webhook URL is a secret — anyone with it can post to the channel. Committing it to the repository exposes it in version history forever.

**Do this instead:** Store as a GitHub repository secret (`SLACK_WEBHOOK_URL`) and reference via `${{ secrets.SLACK_WEBHOOK_URL }}`.

### Anti-Pattern 2: Using `pull_request: types: [closed]` Without Merge Check

**What people do:** Trigger on `pull_request closed` and forget to add `if: github.event.pull_request.merged == true`.

**Why it's wrong:** The workflow fires for both merged and abandoned (closed-without-merge) PRs. You get Slack spam for every closed PR regardless of whether it landed.

**Do this instead:** Either (a) use `on: push` with `paths: skills/**` (only fires when code actually lands on main), or (b) use `pull_request: types: [closed]` with explicit `if: github.event.pull_request.merged == true` condition on the job.

### Anti-Pattern 3: Using `fetch-depth: 1` (Shallow Clone)

**What people do:** Use the default `actions/checkout` without setting `fetch-depth`.

**Why it's wrong:** `tj-actions/changed-files` needs at least 2 commits to diff against. With a shallow clone of depth 1, there is no previous commit to compare to, and the action either errors or reports all files as changed.

**Do this instead:** Set `fetch-depth: 0` (full history, always safe) or `fetch-depth: 2` (last 2 commits, faster).

### Anti-Pattern 4: Listing Changed Files Instead of Changed Directories

**What people do:** Use `tj-actions/changed-files` without `dir_names: true`, then try to parse individual file paths to derive skill names.

**Why it's wrong:** A single skill update touches multiple files (SKILL.md, AGENTS.md, references/*.md). Listing files produces a verbose, hard-to-read message and requires fragile string parsing.

**Do this instead:** Enable `dir_names: true` and `dir_names_max_depth: 2`. The output is already the skill directory names.

### Anti-Pattern 5: Omitting the `paths` Trigger Filter

**What people do:** Trigger on every push to main, check for changed skills inside the workflow, then skip posting if nothing changed.

**Why it's wrong:** The workflow runs and bills GitHub Actions minutes even for pushes that touch only documentation, configuration, or workflow files.

**Do this instead:** Add `paths: ['skills/**']` to the trigger so the workflow only runs when skill directories are modified. Non-skill changes never start the workflow.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Slack Incoming Webhook | HTTP POST with JSON payload | URL is per-channel, store as GitHub secret |
| GitHub Events | Native workflow trigger | `on: push` or `on: pull_request` |
| GitHub Secrets | `${{ secrets.NAME }}` in YAML | Automatically masked in logs |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Checkout step → Changed-files step | Git history on disk | `fetch-depth: 0` required |
| Changed-files step → Message step | Step outputs via `steps.<id>.outputs` | `all_changed_files` output |
| Message step → Slack step | Workflow environment variable or inline `with.payload` | Avoid multi-line YAML pitfalls — use `|` block scalar |
| GitHub Secrets → Slack step | Runtime injection via `${{ secrets.SLACK_WEBHOOK_URL }}` | Never echo this value |

## Sources

- [slackapi/slack-github-action (official)](https://github.com/slackapi/slack-github-action) — HIGH confidence (Slack-maintained)
- [Slack: Sending messages using incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/) — HIGH confidence (official Slack docs)
- [tj-actions/changed-files](https://github.com/tj-actions/changed-files) — HIGH confidence (most-used changed-files action, actively maintained)
- [GitHub Docs: Events that trigger workflows](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows) — HIGH confidence (official GitHub docs)
- [GitHub Docs: Security hardening for GitHub Actions](https://docs.github.com/actions/security-guides/security-hardening-for-github-actions) — HIGH confidence (official GitHub docs)
- [GitHub community: Trigger workflow only on pull request MERGE](https://github.com/orgs/community/discussions/26724) — MEDIUM confidence (official GitHub community forum)
- [rtCamp/action-slack-notify — Slack Notify on Marketplace](https://github.com/marketplace/actions/slack-notify) — MEDIUM confidence (widely used community action, not official Slack)

---
*Architecture research for: GitHub Actions + Slack notification automation*
*Researched: 2026-03-02*

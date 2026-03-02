# Stack Research

**Domain:** GitHub Actions CI/CD + Slack notification automation (PR merge events, monorepo)
**Researched:** 2026-03-02
**Confidence:** HIGH — all primary recommendations verified against official docs and action release pages

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `slackapi/slack-github-action` | v2.1.1 | Post Slack message from workflow | Official Slack-maintained action. v2 is current major version with breaking changes from v1. Supports both incoming webhooks and bot tokens. Use `webhook-type: incoming-webhook` for this use case. |
| `tj-actions/changed-files` | v47.0.4 | Detect which `skills/` subdirectories changed in the merged PR | Most widely-used changed-files action. Native support for `dir_names: "true"` output mode — returns unique directory names, not individual file paths. Essential for identifying which skill was modified. |
| `actions/checkout` | v6.0.2 | Check out repo so git diff is available to changed-files | Required by `tj-actions/changed-files` to compute diffs. Current stable release (Jan 2025). |

### Workflow Trigger

| Trigger | Configuration | Why |
|---------|--------------|-----|
| `pull_request` → `types: [closed]` | With job condition `if: github.event.pull_request.merged == true` | The only way to get full PR context (title, author, URL, labels) in the workflow. The `closed` event fires for both merged and non-merged closes; the `merged == true` condition filters to actual merges only. The `push` to main trigger fires on the same event but loses `github.event.pull_request.*` context entirely. |

### Slack Integration Method

**Recommendation: Incoming Webhook**

Use `slackapi/slack-github-action@v2.1.1` with `webhook-type: incoming-webhook`.

Rationale:
- This workflow posts to one fixed channel (`#qodo-skills-releases`). Incoming webhooks are scoped to a single channel at creation time — exactly what is needed here.
- Setup requires creating a Slack app, enabling Incoming Webhooks, and installing to workspace. The webhook URL is stored as `SLACK_WEBHOOK_URL` in GitHub repository secrets.
- No token scopes to manage, no bot user to invite to the channel.
- Bot token (`SLACK_BOT_TOKEN` + `chat.postMessage` method) is the right choice when you need to post to multiple dynamic channels or need response data between steps. Neither applies here.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GitHub Slack App (`integrations/slack`) | n/a | Native Slack app that mirrors GitHub events | Do NOT use for this project — it sends its own notification format, not a custom one. Mention for completeness: it exists but doesn't let you control message content. |
| `rtCamp/action-slack-notify` | v2 | Simpler, opinionated Slack notify wrapper | Use only if you want zero configuration and accept the fixed message format. Not recommended here — message content must include changed skills list, which requires the official action's flexible payload. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Slack Block Kit Builder (`app.slack.com/block-kit-builder`) | Visually design the Slack message layout before writing YAML | Use to prototype the notification message. Block Kit is the modern Slack message format (header, sections, context blocks). Slack uses `mrkdwn` (not standard Markdown): `*bold*`, `_italic_`, `<url|link text>`. |
| GitHub Actions workflow debugger (`act`) | Local workflow testing | Optional. `act` can run workflows locally against mock events. Useful for iterating on message format without triggering real Slacks. |

## Installation

```bash
# No npm packages needed — this is a pure GitHub Actions YAML workflow.
# All components are GitHub Actions referenced by uses: in workflow YAML.

# Required GitHub repository secrets:
# SLACK_WEBHOOK_URL  — Incoming webhook URL from Slack app configuration
```

## Workflow Skeleton

```yaml
name: Notify Slack on Skill Change

on:
  pull_request:
    branches: [main]
    types: [closed]

jobs:
  notify:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6.0.2
        with:
          fetch-depth: 0  # Required by tj-actions/changed-files for git diff

      - name: Detect changed skills
        id: changed-skills
        uses: tj-actions/changed-files@v47.0.4
        with:
          files: skills/**
          dir_names: "true"
          dir_names_max_depth: "2"  # skills/<skill-name> — stop at depth 2

      - name: Post Slack notification
        if: steps.changed-skills.outputs.any_changed == 'true'
        uses: slackapi/slack-github-action@v2.1.1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            text: "Skill update merged: ${{ github.event.pull_request.title }}"
            blocks:
              - type: "header"
                text:
                  type: "plain_text"
                  text: "Skill Update Merged"
              - type: "section"
                fields:
                  - type: "mrkdwn"
                    text: "*PR:*\n<${{ github.event.pull_request.html_url }}|${{ github.event.pull_request.title }}>"
                  - type: "mrkdwn"
                    text: "*Author:*\n${{ github.event.pull_request.user.login }}"
              - type: "section"
                text:
                  type: "mrkdwn"
                  text: "*Changed skills:*\n${{ steps.changed-skills.outputs.all_changed_files }}"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `slackapi/slack-github-action@v2.1.1` | `rtCamp/action-slack-notify@v2` | When message format is acceptable as-is and zero config is priority. Does not support custom Block Kit payloads. |
| Incoming webhook auth | Bot token + `chat.postMessage` | When you need to post to multiple channels dynamically, or need the message `ts` for threading replies. This use case has neither requirement. |
| `pull_request` + `types: [closed]` + `merged == true` condition | `push` to main | When you do NOT need PR metadata (title, author, PR URL). If you only need commit info, push is simpler. Here PR title and author are required, so `pull_request` is necessary. |
| `tj-actions/changed-files@v47.0.4` | `dorny/paths-filter` | When you need conditional job execution based on changed paths (paths-filter specializes in that). For this use case, you need the changed file list as output data, not just a conditional — use `tj-actions/changed-files`. |
| `actions/checkout@v6.0.2` | `actions/checkout@v4` | v4 is still functional but v6 is current stable. No reason to use v4 for new workflows. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pull_request_target` event | Has elevated privilege risks — runs in base repo context with access to secrets. Security advisories in 2025 explicitly warn against it for notification workflows that don't need it. The standard `pull_request` event is sufficient and safer. | `pull_request` with `types: [closed]` |
| Native GitHub-Slack App integration (`integrations/slack`) | Posts its own fixed-format notifications. Cannot inject changed skills list or customize message. Requires OAuth app install. | `slackapi/slack-github-action` with custom payload |
| `v1.x` of `slackapi/slack-github-action` | Breaking changes between v1 and v2. v1 has different payload handling, no explicit `webhook-type` required. Using v1 means missing current documentation and future security fixes. | `slackapi/slack-github-action@v2.1.1` |
| Hardcoding the Slack webhook URL in workflow YAML | Webhook URL is a secret credential. Exposed in public repos and logs. | Store as `SLACK_WEBHOOK_URL` in GitHub repository secrets, reference as `${{ secrets.SLACK_WEBHOOK_URL }}` |
| `git diff` in a bash step to detect changed files | Brittle on first commits, merge commit edge cases, and shallow clones. | `tj-actions/changed-files` which handles these edge cases |

## Stack Patterns by Variant

**If you need to notify on ALL commits to main (not just PR merges):**
- Use `push` trigger instead of `pull_request`
- Use `dorny/paths-filter` for conditional execution
- Accept loss of PR-specific context (title, author via PR object)

**If you need to notify per-skill in separate Slack threads:**
- Use bot token approach (`SLACK_BOT_TOKEN` + `chat.postMessage`)
- Loop over `steps.changed-skills.outputs.all_changed_files` to send per-skill messages
- Requires `channels:read` and `chat:write` scopes on bot token

**If message format needs to evolve (add PR labels, reviewers, etc.):**
- Bot token is more flexible — `chat.postMessage` payload can include any Slack API fields
- Incoming webhook payload is limited to standard message fields

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `slackapi/slack-github-action@v2.1.1` | GitHub Actions runner (ubuntu-latest) | `webhook-type` field is v2 only — required for incoming-webhook technique. Not backward compatible with v1 syntax. |
| `tj-actions/changed-files@v47.0.4` | `actions/checkout@v4+`, `ubuntu-latest` runner | Requires `fetch-depth: 0` on checkout step to access git history for diff computation. |
| `actions/checkout@v6.0.2` | All current GitHub-hosted runners | Minimum Actions Runner v2.327.1 required. |

## Sources

- [slackapi/slack-github-action GitHub](https://github.com/slackapi/slack-github-action) — verified v2.1.1 as latest stable release (Jul 2024)
- [Slack Developer Docs — slack-github-action](https://docs.slack.dev/tools/slack-github-action/) — official docs, three sending techniques
- [Slack Developer Docs — Incoming Webhook technique](https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-slack-incoming-webhook/) — YAML example and required inputs (HIGH confidence)
- [Slack Developer Docs — Slack API method technique](https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-slack-api-method/) — bot token alternative (HIGH confidence)
- [tj-actions/changed-files GitHub](https://github.com/tj-actions/changed-files) — verified v47.0.4 as latest stable release (Feb 2025), `dir_names` usage
- [actions/checkout releases](https://github.com/actions/checkout/releases) — verified v6.0.2 as latest stable release (Jan 2025)
- [GitHub Docs — Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) — `pull_request` closed event behavior and `merged` property (HIGH confidence)
- [shipit.dev — Trigger GitHub Actions on PR close](https://shipit.dev/posts/trigger-github-actions-on-pr-close.html) — `closed` + `merged == true` pattern (MEDIUM confidence, verified against GitHub Docs)
- [GitHub Security Lab — Preventing pwn requests](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/) — `pull_request_target` security risks (HIGH confidence)
- [GitHub Changelog — pull_request_target changes Nov 2025](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/) — 2025 security changes to `pull_request_target` (HIGH confidence)

---
*Stack research for: GitHub Actions + Slack notification automation on PR merge*
*Researched: 2026-03-02*

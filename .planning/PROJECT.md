# EB-28: Automate Skill Change Notifications

## What This Is

A GitHub Actions CI/CD pipeline that automatically posts Slack notifications to `#qodo-skills-releases` whenever a PR is merged into the main branch of the qodo-skills repository. The goal is to eliminate manual pings — anyone interested in skill changes can subscribe to the channel and stay informed automatically.

## Core Value

When a skill change lands, the right people know immediately — without anyone having to manually announce it.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] GitHub Actions workflow triggers on PR merge to main
- [ ] Workflow detects which skills were changed in the merged PR
- [ ] Slack notification is posted to `#qodo-skills-releases` containing: PR title, PR author, link to PR, and list of changed skills
- [ ] Slack integration method is chosen and configured (incoming webhook or bot token)
- [ ] `#qodo-skills-releases` channel exists in the Slack workspace

### Out of Scope

- Email or DM notifications — channel subscription is sufficient
- Notifications for direct commits (bypassing PRs) — not a current workflow
- Historical backfill notifications — only future merges
- Release-specific events (git tags, npm publish) — merge to main IS the release event

## Context

- **Repo**: qodo-skills GitHub repository
- **No existing CI**: GitHub Actions must be set up from scratch
- **Skills location**: `skills/` directory — each subdirectory is a distinct skill
- **Trigger**: PR merged to main branch (merge = release, they are the same event)
- **Audience**: Team members who want to track skill changes passively

## Constraints

- **Platform**: GitHub Actions — chosen for native GitHub integration, no extra infra
- **Slack channel**: `#qodo-skills-releases` — needs to be created as part of setup
- **Slack auth**: Method TBD (incoming webhook recommended for simplicity — decide during implementation)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GitHub Actions for CI | Zero infra overhead, native GitHub events | — Pending |
| Merge to main as trigger | Merge = release in this repo's workflow | — Pending |
| Dedicated Slack channel | Opt-in model — subscribers choose to follow | — Pending |

---
*Last updated: 2026-03-02 after initialization*

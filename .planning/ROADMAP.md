# Roadmap: EB-28 — Automate Skill Change Notifications

## Overview

A three-phase delivery: first establish the external prerequisites (Slack channel, webhook, GitHub secret), then build and verify the workflow trigger and skill-detection logic, then wire in the Slack notification message. Each phase delivers a verified, independently testable capability before the next begins. The entire output is a single GitHub Actions YAML file.

## Phases

- [x] **Phase 1: External Setup** - Create the Slack channel, configure the incoming webhook app, and store the secret in GitHub
- [x] **Phase 2: Workflow Core** - Implement the GitHub Actions workflow with correct trigger, checkout, skill-change detection, and non-skill suppression
- [ ] **Phase 3: Slack Notification** - Assemble and deliver the Block Kit message with PR title, author, link, and changed skill names

## Phase Details

### Phase 1: External Setup
**Goal**: All external prerequisites exist and are verifiable before any workflow YAML is written
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, SETUP-03
**Success Criteria** (what must be TRUE):
  1. `#qodo-skills-releases` channel exists in the Slack workspace and accepts messages
  2. A Slack app with an incoming webhook scoped to `#qodo-skills-releases` exists and its URL produces a 200 response when called
  3. `SLACK_WEBHOOK_SKILLS_RELEASES_URL` appears as a repository secret in GitHub Actions settings (value is masked)
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Create Slack channel, app webhook, and GitHub secret (SETUP-01, SETUP-02, SETUP-03)

### Phase 2: Workflow Core
**Goal**: A GitHub Actions workflow fires only on PR merge to main, detects which skills changed, and produces no output for non-skill PRs
**Depends on**: Phase 1
**Requirements**: TRIG-01, TRIG-02, DETECT-01, DETECT-02, DETECT-03
**Success Criteria** (what must be TRUE):
  1. Merging a PR that touches `skills/` causes the workflow to run and log the list of changed skill directories
  2. Closing a PR without merging does not trigger the workflow
  3. Merging a PR that touches only non-`skills/` files (e.g., README) causes the workflow to run but exit without posting any notification
  4. The changed-files action reference in the workflow YAML uses a full commit SHA, not a version tag
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Create notify-skill-changes workflow YAML and verify trigger/detection behavior (TRIG-01, TRIG-02, DETECT-01, DETECT-02, DETECT-03)

### Phase 3: Slack Notification
**Goal**: A Slack message appears in `#qodo-skills-releases` every time a skill-touching PR merges to main, containing all required information in Block Kit format
**Depends on**: Phase 2
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06
**Success Criteria** (what must be TRUE):
  1. Merging a skill-touching PR causes a message to appear in `#qodo-skills-releases` within seconds
  2. The message shows the PR title, the GitHub username of the PR author, and a clickable link to the PR
  3. The message lists the names of changed skills in a readable format (not full `skills/` paths)
  4. The message uses Slack Block Kit formatting (visible structure — header, sections — not plain text)
  5. Merging a non-skill PR produces no message in `#qodo-skills-releases`
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. External Setup | 1/1 | Complete   | 2026-03-02 |
| 2. Workflow Core | 1/1 | Complete | 2026-03-02 |
| 3. Slack Notification | 0/? | Not started | - |

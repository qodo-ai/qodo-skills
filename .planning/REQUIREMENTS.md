# Requirements: EB-28 — Automate Skill Change Notifications

**Defined:** 2026-03-02
**Core Value:** When a skill change lands, the right people know immediately — without anyone having to manually announce it.

## v1 Requirements

### Setup (External Prerequisites)

- [x] **SETUP-01**: `#qodo-skills-releases` Slack channel is created in the workspace
- [x] **SETUP-02**: A Slack app with incoming webhook scoped to `#qodo-skills-releases` is created
- [x] **SETUP-03**: Webhook URL is stored as `SLACK_WEBHOOK_SKILLS_RELEASES_URL` in GitHub Actions repository secrets

### Workflow Trigger

- [ ] **TRIG-01**: GitHub Actions workflow triggers only when a PR is merged to main (not merely closed)
- [ ] **TRIG-02**: Workflow uses `pull_request: types: [closed]` event with `if: github.event.pull_request.merged == true` job condition

### Skill Change Detection

- [ ] **DETECT-01**: Workflow detects which `skills/` subdirectories were modified in the merged PR
- [ ] **DETECT-02**: Notification is suppressed when no files under `skills/` changed (non-skill PRs produce no notification)
- [ ] **DETECT-03**: Third-party changed-files action is pinned to a commit SHA (not a version tag) to prevent supply chain compromise

### Slack Notification

- [ ] **NOTIF-01**: Slack message is posted to `#qodo-skills-releases` when a skill-touching PR merges
- [ ] **NOTIF-02**: Message includes PR title
- [ ] **NOTIF-03**: Message includes PR author (GitHub username)
- [ ] **NOTIF-04**: Message includes clickable link to the PR on GitHub
- [ ] **NOTIF-05**: Message includes list of changed skill names (readable names, not full paths)
- [ ] **NOTIF-06**: Message uses Slack Block Kit formatting (not plain text)

## v2 Requirements

### Notification Enhancements

- **NOTIF-07**: PR body excerpt (first 280 chars) included in message — for consumers wanting change context without opening GitHub
- **NOTIF-08**: Message updates in-place (thread reply) on re-run — reduces channel noise when workflow retries

### Channel Routing

- **CHAN-01**: Per-skill channel routing — notify different channels based on which skill changed
- **CHAN-02**: Webhook rotation tooling — update webhook URL without touching workflow YAML

## Out of Scope

| Feature | Reason |
|---------|--------|
| Email / DM notifications | Channel subscription model is sufficient; opt-in via Slack |
| Direct-commit notifications (bypassing PRs) | Not a current team workflow |
| Historical backfill notifications | Only future merges needed |
| Multi-platform delivery (Teams, email) | Not requested; generalize only when needed |
| Acknowledgment tracking | Premature complexity |
| Per-user opt-out preferences | Channel opt-in is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Complete |
| SETUP-02 | Phase 1 | Complete |
| SETUP-03 | Phase 1 | Complete |
| TRIG-01 | Phase 2 | Pending |
| TRIG-02 | Phase 2 | Pending |
| DETECT-01 | Phase 2 | Pending |
| DETECT-02 | Phase 2 | Pending |
| DETECT-03 | Phase 2 | Pending |
| NOTIF-01 | Phase 3 | Pending |
| NOTIF-02 | Phase 3 | Pending |
| NOTIF-03 | Phase 3 | Pending |
| NOTIF-04 | Phase 3 | Pending |
| NOTIF-05 | Phase 3 | Pending |
| NOTIF-06 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after Phase 1 completion (secret name corrected to SLACK_WEBHOOK_SKILLS_RELEASES_URL)*

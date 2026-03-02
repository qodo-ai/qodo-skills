---
phase: 02-workflow-core
plan: 01
subsystem: infra
tags: [github-actions, workflow, changed-files, sha-pinning, pull-request, slack-prep]

# Dependency graph
requires:
  - phase: 01-external-setup
    provides: SLACK_WEBHOOK_SKILLS_RELEASES_URL secret in GitHub Actions settings

provides:
  - GitHub Actions workflow at .github/workflows/notify-skill-changes.yml — merge-only trigger, SHA-pinned changed-files detection, conditional skill logging
  - Verified trigger behavior (job skips on PR close, runs on merge)
  - Verified skill detection (logs skill names without skills/ prefix)
  - Verified non-skill suppression (exits cleanly for non-skills/ PRs)

affects: [03-slack-notification]

# Tech tracking
tech-stack:
  added:
    - tj-actions/changed-files@7dee1b0c1557f278e5c7dc244927139d78c0e22a (v47.0.4, SHA-pinned)
    - actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 (v4.2.2, SHA-pinned)
  patterns:
    - PR merge-only trigger via pull_request types:[closed] + if:github.event.pull_request.merged==true
    - SHA pinning for all third-party actions (CVE-2025-30066 mitigation)
    - dir_names_max_depth:2 for skills/ subdirectory detection at correct depth
    - Bash prefix stripping ${dir#skills/} to log skill names without path prefix

key-files:
  created:
    - .github/workflows/notify-skill-changes.yml
  modified: []

key-decisions:
  - "Trigger uses pull_request types:[closed] + job-level if:merged==true — not push event — so PR metadata (title, author, URL) is available for Phase 3"
  - "tj-actions/changed-files pinned to full 40-char SHA 7dee1b0c1557f278e5c7dc244927139d78c0e22a, not version tag — CVE-2025-30066 makes tag-based references unsafe"
  - "dir_names_max_depth:2 chosen to produce skills/<name> paths (depth 1 gives only skills/, depth 2 gives skills/qodo-get-rules)"
  - "fetch-depth:0 NOT added to checkout — pull_request events auto-resolve base SHA; only needed for push events"

patterns-established:
  - "PR merge-only guard: pull_request types:[closed] + if:github.event.pull_request.merged==true at job level"
  - "SHA pinning pattern: all third-party actions use full 40-char commit SHA with version comment"
  - "Skill name extraction: bash ${dir#skills/} strips prefix from dir_names output"

requirements-completed: [TRIG-01, TRIG-02, DETECT-01, DETECT-02, DETECT-03]

# Metrics
duration: ~2h (includes 3 live GitHub Actions verification runs)
completed: 2026-03-02
---

# Phase 2 Plan 01: Workflow Core Summary

**GitHub Actions workflow with merge-only PR trigger, SHA-pinned tj-actions/changed-files detection, and verified skill-name logging across 3 live test scenarios**

## Performance

- **Duration:** ~2h (includes live GitHub Actions test runs)
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments

- Created `.github/workflows/notify-skill-changes.yml` with correct merge-only trigger, SHA-pinned action references, and conditional skill logging
- Verified all 3 behavioral scenarios via live GitHub Actions runs: job skips on PR close (TRIG-01/TRIG-02), exits cleanly for non-skill PRs (DETECT-02), logs skill names on skill-touching PRs (DETECT-01)
- Confirmed SHA pin DETECT-03: tj-actions/changed-files at `7dee1b0c1557f278e5c7dc244927139d78c0e22a`
- Left `# TODO(Phase 3): Add slackapi/slack-github-action step here` placeholder for Slack integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GitHub Actions workflow YAML** - `f24304e` (feat)
2. **Task 2: Verify workflow behavior with test PRs** - APPROVED via GitHub Actions runs (no additional commit — checkpoint verification only)

## Verification Evidence

All 3 tests passed via automated `gh` CLI verification:

| Test | Scenario | Workflow Run | Result |
|------|----------|-------------|--------|
| TRIG-01/TRIG-02 | PR closed without merging | `22581806717` | Job conclusion: `skipped` |
| DETECT-02 | Non-skills/ PR merged | `22581833527` | "No skill changes — skipping" step: `success`, "Log changed skills": `skipped` |
| DETECT-01 | skills/ PR merged | `22581878177` | "Log changed skills" step: `success`, output: `  - qodo-get-rules` |

## Files Created/Modified

- `.github/workflows/notify-skill-changes.yml` — GitHub Actions workflow implementing merge-only trigger, SHA-pinned changed-files detection, conditional logging for skill vs non-skill PRs, and TODO placeholder for Phase 3 Slack step

## Decisions Made

- Pull_request types:[closed] trigger chosen over push so PR metadata (title, author, URL) will be available in Phase 3 Slack notification
- tj-actions/changed-files pinned to SHA `7dee1b0c1557f278e5c7dc244927139d78c0e22a` (v47.0.4) — CVE-2025-30066 (March 2025 supply chain compromise) makes version-tag references unsafe
- `dir_names_max_depth: '2'` produces `skills/<name>` paths; bash prefix stripping `${dir#skills/}` extracts just the skill name for readable logging
- No `fetch-depth: 0` in checkout — pull_request events automatically resolve the base SHA; this flag is only needed for push events

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all 3 behavioral tests passed on first attempt.

## User Setup Required

None - no external service configuration required for this plan. (Phase 1 already configured the Slack webhook secret.)

## Next Phase Readiness

- Phase 3 (Slack Notification) can begin immediately
- The workflow file has a `# TODO(Phase 3): Add slackapi/slack-github-action step here` placeholder after the "No skill changes — skipping" step
- Phase 3 needs: PR title via `github.event.pull_request.title`, PR author via `github.event.pull_request.user.login`, PR URL via `github.event.pull_request.html_url`, changed skill names from `steps.changed-skills.outputs.all_changed_files`
- Secret `SLACK_WEBHOOK_SKILLS_RELEASES_URL` is already configured in GitHub Actions (Phase 1 deliverable)

---
*Phase: 02-workflow-core*
*Completed: 2026-03-02*

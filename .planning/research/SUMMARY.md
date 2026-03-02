# Project Research Summary

**Project:** EB-28 — Automate Slack notifications on skill PR merge
**Domain:** GitHub Actions CI/CD + Slack notification automation (monorepo)
**Researched:** 2026-03-02
**Confidence:** HIGH

## Executive Summary

This project is a GitHub Actions workflow that posts a Slack notification to `#qodo-skills-releases` whenever a PR merges to main and touches one or more skills under `skills/`. The implementation is a single YAML file — no application code, no npm packages, no infrastructure. Research across all four domains is highly confident and draws from official Slack, GitHub, and CVE documentation. The right pattern is well-established: trigger on PR merge, detect which skill directories changed, filter out non-skill PRs, post a structured message via an incoming webhook.

The recommended approach is to use `pull_request: types: [closed]` with `if: github.event.pull_request.merged == true` as the trigger (not `push` to main), because this is the only event type that exposes full PR metadata — title, author URL — as direct context variables. Changed-file detection should use either `tj-actions/changed-files` (pinned to a commit SHA, not a version tag) or native `git diff` with a two-component path filter. The Slack delivery mechanism should be an incoming webhook via `slackapi/slack-github-action@v2`, with the webhook URL stored as a GitHub Actions repository secret.

The primary risks are security-related: the supply chain attack on `tj-actions/changed-files` (CVE-2025-30066, March 2025) is directly relevant to this project because that action is the recommended changed-files detection tool. Mitigation is mandatory: pin to commit SHA or replace with native `git diff`. The second risk is webhook credential exposure via workflow logs — mitigated by never echoing secrets and always using `${{ secrets.SLACK_WEBHOOK_URL }}`. All other pitfalls are correctness issues (wrong trigger, shallow clone, missing merge guard) that standard YAML patterns prevent.

## Key Findings

### Recommended Stack

The stack is pure GitHub Actions YAML with three referenced actions: `actions/checkout@v6.0.2` (repo clone), `tj-actions/changed-files@v47.0.4` (skill directory detection), and `slackapi/slack-github-action@v2.1.1` (Slack delivery). No npm packages, no scripts directory, no external dependencies beyond these actions and one GitHub repository secret.

**Core technologies:**
- `actions/checkout@v6.0.2` — fetches repo with full git history — required for `tj-actions/changed-files` diff computation; must set `fetch-depth: 0`
- `tj-actions/changed-files@v47.0.4` — detects which `skills/` subdirectories changed — use `dir_names: true` and `dir_names_max_depth: 2`; MUST be pinned to commit SHA (not version tag) due to CVE-2025-30066
- `slackapi/slack-github-action@v2.1.1` — posts Block Kit message via incoming webhook — official Slack-maintained action; v2 required for `webhook-type: incoming-webhook` field

**Critical version note:** `slackapi/slack-github-action` v2 has breaking changes from v1. `webhook-type` is a v2-only field. Do not use v1 syntax.

### Expected Features

**Must have (table stakes):**
- Trigger on PR merge to main — core purpose; nothing works without the correct trigger
- Changed-files detection scoped to `skills/**` — monorepo context; without this, notifications lack meaning
- Suppress notification when no skills changed — every PR (CI, docs, config) fires otherwise, destroying channel trust
- Post message to `#qodo-skills-releases` via incoming webhook — primary delivery
- Message contains PR title, author, link, and changed skill names — the four fields explicitly required
- `SLACK_WEBHOOK_URL` stored as GitHub Actions secret — mandatory for auth; hardcoding is a disqualifying failure

**Should have (polish after v1 validation):**
- Rich Block Kit formatting — plain-text messages are functional but visually poor
- Human-readable skills list — strip `skills/` prefix and comma-separate (one bash step)
- PR body excerpt (first 280 chars) — for consumers who want change context without opening GitHub

**Defer (v2+):**
- Per-channel routing by skill — only needed when multiple channels exist
- Message threading/update-in-place — only needed when notification volume creates channel noise
- Multi-platform delivery (Teams, email) — not requested; generalize only when a second platform is needed

### Architecture Approach

The entire implementation is a single file at `.github/workflows/notify-skill-changes.yml`. Steps execute sequentially within one job: checkout → detect changed skills → (conditional) post Slack message. No shared scripts, no separate action repository, no infrastructure. External dependencies are the Slack app webhook and the GitHub secret.

**Major components:**
1. Workflow trigger (`pull_request` closed + merged condition) — fires only on actual merges to main
2. `actions/checkout` with `fetch-depth: 0` — enables git diff for changed-files detection
3. `tj-actions/changed-files` with `dir_names: true` + `dir_names_max_depth: 2` — outputs space-separated skill directory names
4. Conditional notify step (`if: steps.changed-skills.outputs.any_changed == 'true'`) — suppresses non-skill PRs
5. `slackapi/slack-github-action` with incoming webhook — delivers Block Kit payload to `#qodo-skills-releases`
6. GitHub Secrets (`SLACK_WEBHOOK_URL`) — credentials injected at runtime, automatically redacted from logs

**Key architectural decision:** STACK.md and ARCHITECTURE.md disagree on trigger strategy. STACK.md recommends `pull_request: types: [closed]` (full PR context). ARCHITECTURE.md recommends `push` to main (simpler, no cross-fork concerns). The correct choice for this project is `pull_request: types: [closed]` with `if: github.event.pull_request.merged == true` because the requirements explicitly include PR title, author, and PR URL — all of which are unavailable on the `push` event without an extra GitHub API call.

### Critical Pitfalls

1. **Third-party action supply chain attack** — `tj-actions/changed-files` was compromised in CVE-2025-30066 (March 2025); pin all third-party actions to commit SHA (`uses: tj-actions/changed-files@<SHA>`) or replace with native `git diff`

2. **Webhook secret leakage** — never `echo $SLACK_WEBHOOK_URL` in workflow steps; pass via `${{ secrets.SLACK_WEBHOOK_URL }}` only, which GitHub auto-redacts; never use `set -x` in steps with secret access

3. **Trigger fires on closed-not-merged PRs** — add `if: github.event.pull_request.merged == true` at the job level; verify by closing a PR without merging and confirming no notification fires

4. **Empty changed-files list from shallow clone** — set `fetch-depth: 2` (minimum) or `fetch-depth: 0` on `actions/checkout`; default `fetch-depth: 1` means no parent commit exists for diffing

5. **Slack channel does not exist at webhook creation time** — create `#qodo-skills-releases` in Slack before configuring the incoming webhook; channel must exist before the webhook URL is generated

## Implications for Roadmap

The architecture's suggested build order maps cleanly to two phases: pre-implementation Slack/secret setup (external, no code), then workflow YAML implementation and verification.

### Phase 1: External Setup (Slack + GitHub Secrets)

**Rationale:** The Slack incoming webhook URL must exist before any workflow YAML can be written or tested. GitHub secrets must be configured before the workflow references them. No code dependencies exist yet — this is pure infrastructure setup. All research sources agree this must precede Phase 2.

**Delivers:** A working Slack app with an incoming webhook scoped to `#qodo-skills-releases`, the webhook URL stored as `SLACK_WEBHOOK_URL` in GitHub Actions repository secrets, and a verified channel that accepts test posts.

**Addresses:** Table stakes features "Slack auth secret stored as GitHub secret" and "Post to specific Slack channel"

**Avoids:**
- Pitfall 6 (Slack channel does not exist) — create channel before webhook
- Pitfall 2 (webhook secret leakage) — configure secrets correctly from the start
- Pitfall 8 (webhook owned by departing member) — use shared/service account

**Research flag:** No deeper research needed. Creating a Slack app with incoming webhooks is official-documentation-level territory.

### Phase 2: Core Workflow — Trigger, Detection, Filter

**Rationale:** Once the webhook secret exists, implement the workflow skeleton: correct trigger, checkout with proper fetch depth, changed-files detection, and the conditional filter that suppresses non-skill PRs. These are all hard dependencies for the Slack notification step. Building and testing them in isolation before adding Slack avoids debugging two systems simultaneously.

**Delivers:** A workflow that correctly fires on PR merge (not close), detects which `skills/` directories changed, and suppresses execution when no skills changed. Verified with test merges.

**Uses:**
- `actions/checkout@v6.0.2` with `fetch-depth: 0`
- `tj-actions/changed-files@v47.0.4` pinned to commit SHA
- `pull_request: types: [closed]` trigger + `if: merged == true` condition

**Implements:** Workflow trigger component, checkout component, changed-files detection component, conditional filter

**Avoids:**
- Pitfall 1 (supply chain) — pin `tj-actions/changed-files` to SHA at creation time
- Pitfall 3 (fires on closed-not-merged) — merge guard condition
- Pitfall 4 (shallow clone) — explicit `fetch-depth`
- Pitfall 5 (pull_request_target) — use `pull_request`, not `pull_request_target`
- Pitfall 7 (notification spam) — `any_changed` conditional on notify step
- Pitfall 11 (skill detection regex) — use `dir_names: true` + `dir_names_max_depth: 2`

**Research flag:** No deeper research needed. All three action versions and their required parameters are confirmed against official documentation.

### Phase 3: Slack Notification — Message Assembly and Delivery

**Rationale:** With trigger, detection, and filtering verified in Phase 2, wiring up Slack is the final step. Start with plain-text payload for initial validation, then add Block Kit formatting. Separating this from Phase 2 makes debugging straightforward: if the message doesn't arrive, the workflow execution path is already confirmed correct.

**Delivers:** A Slack notification in `#qodo-skills-releases` containing PR title, PR author, PR link, and a human-readable list of changed skill names. Triggered by a real PR merge to main.

**Uses:**
- `slackapi/slack-github-action@v2.1.1` with `webhook-type: incoming-webhook`
- `${{ github.event.pull_request.title }}`, `.user.login`, `.html_url` context variables
- `${{ steps.changed-skills.outputs.all_changed_files }}` with `skills/` prefix stripped
- Block Kit payload with `header`, `section`, and `context` blocks

**Implements:** Message builder step, Slack notify step, Block Kit payload

**Avoids:**
- Pitfall 2 (secret leakage) — use `${{ secrets.SLACK_WEBHOOK_URL }}`, never echo
- Pitfall 6 (silent webhook failure) — validate HTTP response code from Slack call
- Pitfall 9 (duplicate notifications) — add `concurrency` group keyed on `github.sha`
- Pitfall 10 (rate limits) — acceptable risk at this project's merge volume

**Research flag:** No deeper research needed. Block Kit payload format and `slackapi/slack-github-action` v2 inputs are fully documented.

### Phase Ordering Rationale

- Phase 1 must precede Phase 2 because the workflow YAML references `secrets.SLACK_WEBHOOK_URL` — the secret must exist before the workflow can be executed without errors.
- Phase 2 must precede Phase 3 because the Slack step depends on `steps.changed-skills.outputs.any_changed` and `steps.changed-skills.outputs.all_changed_files` — these outputs must be confirmed working before building the message that consumes them.
- The three-phase split maps directly to the architecture's suggested build order (items 1–3, items 4–5, items 6–8).
- This order also enables fail-fast debugging: each phase has a clear success criterion that can be verified before proceeding.

### Research Flags

Phases with standard patterns (no additional research needed):
- **Phase 1:** Slack incoming webhook setup is official-documentation-level. Steps are deterministic.
- **Phase 2:** All action versions, parameters, and trigger semantics are verified against official sources.
- **Phase 3:** `slackapi/slack-github-action` v2 payload format is fully documented; Block Kit Builder enables visual prototyping.

No phases require `/gsd:research-phase` during planning. The entire implementation domain is well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All three actions verified against official repositories and release pages; version numbers confirmed current as of Feb/Jan 2025 |
| Features | HIGH | P1 features are unambiguous; corroborated by official GitHub Docs and slackapi/slack-github-action repo |
| Architecture | HIGH | Official GitHub Actions docs, official Slack docs, official action repos; single unresolved trigger decision resolved in this synthesis |
| Pitfalls | HIGH | CVE-2025-30066 is documented by CISA; all other pitfalls backed by official GitHub and Slack documentation |

**Overall confidence:** HIGH

### Gaps to Address

- **Trigger decision:** STACK.md and ARCHITECTURE.md recommend different triggers. This synthesis resolves the ambiguity in favor of `pull_request: types: [closed]` with merge guard, because PR metadata (title, author, URL) cannot be obtained from `push` events without an extra GitHub API call. The roadmap should call this out as a decision with rationale.

- **SHA pinning for `tj-actions/changed-files`:** STACK.md references version `v47.0.4` by tag. PITFALLS.md explicitly warns that this exact action was supply-chain-compromised in 2025. The implementation must resolve the specific commit SHA for v47.0.4 during Phase 2 and pin to it. An alternative is replacing this action entirely with a native `git diff` bash step, which eliminates the supply chain dependency at the cost of slightly more YAML.

- **Block Kit payload validation:** The Slack Block Kit payload is JSON embedded in YAML. Multi-line YAML block scalars with embedded JSON and GitHub Actions expression interpolation (`${{ }}`) are a known source of subtle formatting errors. Use Block Kit Builder to validate the payload structure before committing.

## Sources

### Primary (HIGH confidence)
- [slackapi/slack-github-action GitHub](https://github.com/slackapi/slack-github-action) — v2.1.1 release, incoming webhook technique, payload format
- [Slack Developer Docs — slack-github-action](https://docs.slack.dev/tools/slack-github-action/) — official three sending techniques documentation
- [Slack Developer Docs — Incoming Webhook technique](https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-slack-incoming-webhook/) — YAML examples, required inputs
- [tj-actions/changed-files GitHub](https://github.com/tj-actions/changed-files) — v47.0.4 release, `dir_names` output mode
- [actions/checkout releases](https://github.com/actions/checkout/releases) — v6.0.2 as current stable
- [GitHub Docs — Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) — `pull_request closed` + `merged` property behavior
- [GitHub Docs — Using secrets in GitHub Actions](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions) — secrets configuration
- [CVE-2025-30066 — CISA advisory](https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction) — supply chain attack on `tj-actions/changed-files`
- [GitHub Security Lab — Preventing pwn requests](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/) — `pull_request_target` security risks
- [GitHub Changelog — pull_request_target Nov 2025](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/) — 2025 security changes
- [GitHub Docs — Security hardening for GitHub Actions](https://docs.github.com/actions/security-guides/security-hardening-for-github-actions) — GITHUB_TOKEN permissions
- [Slack incoming webhooks rate limits](https://docs.slack.dev/apis/web-api/rate-limits/) — 1 message/second limit

### Secondary (MEDIUM confidence)
- [shipit.dev — Trigger on PR close](https://shipit.dev/posts/trigger-github-actions-on-pr-close.html) — `closed` + `merged == true` pattern (verified against GitHub Docs)
- [Axolo — GitHub Actions Slack integration guide 2026](https://axolo.co/blog/p/top-4-github-action-slack-integration) — ecosystem survey
- [OneUptime — Monorepo path filters in GitHub Actions (Dec 2025)](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view) — `paths` filter behavior in monorepos
- [GitHub community: Trigger workflow only on PR MERGE](https://github.com/orgs/community/discussions/26724) — community patterns
- [Wiz blog: tj-actions supply chain attack analysis](https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066) — attack mechanics

---
*Research completed: 2026-03-02*
*Ready for roadmap: yes*

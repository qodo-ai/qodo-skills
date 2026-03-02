# Feature Research

**Domain:** GitHub Actions CI/CD — Slack notification automation for PR merges in a monorepo
**Researched:** 2026-03-02
**Confidence:** HIGH (verified against official GitHub Actions docs, slackapi/slack-github-action repo, and multiple corroborating sources)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist or the automation is functionally useless.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Trigger on PR merge to main | Core purpose — if the trigger is wrong, nothing works | LOW | Use `pull_request` event with `types: [closed]` + `if: github.event.pull_request.merged == true` conditional. Native GitHub Actions. |
| Post message to a specific Slack channel | The whole point is channel delivery; posting nowhere or to the wrong place = useless | LOW | Incoming webhook encodes the target channel at creation time. Bot token requires `channel` param. |
| PR title in notification | Receivers need to know what landed | LOW | `${{ github.event.pull_request.title }}` — direct context variable, no extra step. |
| PR author in notification | Accountability and attribution — team wants to know who shipped | LOW | `${{ github.event.pull_request.user.login }}` — direct context variable. |
| Link to the PR | Without it, the notification is a dead end; no way to get context | LOW | `${{ github.event.pull_request.html_url }}` — direct context variable. |
| List which skills changed | This is a monorepo of skills — notifications without the "what changed" answer the wrong question | MEDIUM | Requires a changed-files detection step. `tj-actions/changed-files` with `dir_names: true` + `dir_names_max_depth: 2` against `skills/**` is the standard approach. Outputs a string list. |
| Slack auth secret stored as GitHub secret | Required for any Slack delivery; hardcoding credentials is a disqualifying failure mode | LOW | Store `SLACK_WEBHOOK_URL` as a repository-level GitHub Actions secret. Reference via `${{ secrets.SLACK_WEBHOOK_URL }}`. |
| Only fire on actual merges, not PR closes/rejections | Notifications on rejected PRs = noise that destroys trust in the channel | LOW | The `if: github.event.pull_request.merged == true` conditional at the job level is the standard pattern. |

### Differentiators (Competitive Advantage)

Features not required for basic function, but that meaningfully improve signal quality or operator experience.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Skip notification when no skills changed | A PR that only changes docs, config, or CI files should not flood `#qodo-skills-releases` | LOW-MEDIUM | Add `paths: ['skills/**']` to the workflow trigger OR check `any_changed` output from `tj-actions/changed-files`. The trigger-level `paths` filter is simpler but fires the workflow and then does nothing if path filter was missed; step-level conditional is more reliable for message suppression. |
| Rich Slack Block Kit formatting | Plain-text webhook messages are functional but look poor in Slack. Block Kit messages have headers, bold labels, clickable buttons, and structured fields | MEDIUM | Requires composing a JSON payload with `blocks` array. Use `slackapi/slack-github-action` v2's `payload` input. Slack's Block Kit Builder at app.slack.com/block-kit-builder lets you prototype visually. Always include a fallback `text` field alongside `blocks`. |
| Human-readable skills list (not raw paths) | Raw output like `skills/qodo-get-rules skills/qodo-pr-resolver` is harder to scan than `qodo-get-rules, qodo-pr-resolver` | LOW | One bash step: strip `skills/` prefix, replace spaces with `, `. Two `sed` calls or a simple shell substitution. |
| Notify only if skills changed (suppress config-only PRs) | PRs that only touch `.github/`, `AGENTS.md`, or root config are irrelevant to skill consumers | LOW-MEDIUM | Combine `paths: ['skills/**']` trigger filter with a skills-changed check. When the intersection is empty, add `if: steps.changed-skills.outputs.any_changed == 'true'` to the notify step. |
| PR body excerpt or description in message | Helps consumers understand the nature of the change without opening GitHub | MEDIUM | `${{ github.event.pull_request.body }}` is available but often verbose. Truncating to first 280 chars and appending "..." is a standard pattern. Risk: malformed markdown in PR body breaks Block Kit JSON if not escaped. |
| Channel routing by skill (different channels per skill) | Large workspaces may want `qodo-get-rules` changes in one channel and `qodo-pr-resolver` in another | HIGH | Requires a mapping from skill name to webhook URL (as separate secrets per channel) and conditional routing logic. Premature for v1 with a single `#qodo-skills-releases` channel. |
| Message threading (update same message on re-run) | Avoid Slack channel flooding on repeated runs in same day | HIGH | Requires bot token (not webhook), storing thread_ts, and calling `chat.update`. Overkill for merge notifications which should be distinct events. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful but create problems for v1.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Email or DM notifications | Some team members prefer personal channels | Fragments the audience; defeats the shared channel model; requires user identity mapping from GitHub to Slack | Encourage channel subscription; let users set personal notification preferences in Slack |
| Notifications for direct commits (bypassing PRs) | Completeness — what if someone pushes directly to main? | Forces a separate `push` trigger, adds complexity, and the PROJECT.md explicitly calls this out-of-scope because it's not the current workflow | Document the convention: all changes via PR |
| Historical backfill | "What shipped before this automation existed?" | One-time operation; building it into the workflow adds dead code that only runs once | Run a manual script once if needed; don't ship it as part of the automation |
| Notification on every commit (not just PR merges) | Fine-grained visibility | Creates unacceptable noise for consumers of `#qodo-skills-releases`; merge = release is the correct semantic | Keep trigger at PR merge only |
| Multi-platform (Teams, email, PagerDuty) | Some orgs use multiple platforms | Premature generalization; doubles implementation surface area; the project has a single stated channel | Solve Slack first; abstract only when a second platform is actually needed |
| Reaction/acknowledgment tracking ("did anyone see this?") | Accountability for critical changes | Requires a persistent bot, thread monitoring, and reminder jobs; far beyond a CI notification workflow | Trust channel subscribers to read announcements; use @ mentions for critical changes |
| Per-user notification preferences (opt-out per skill) | Power users may only care about specific skills | Requires a preferences store (database or config file), user identity mapping, and custom routing logic | Channel subscription is the opt-in/opt-out mechanism |

## Feature Dependencies

```
[PR merge trigger]
    └──required by──> [Changed-files detection]
                          └──required by──> [Skills list in message]
                          └──enables──> [Suppress notification if no skills changed]

[Slack auth secret]
    └──required by──> [Post message to Slack channel]
                          └──required by──> [PR title / author / link in message]
                          └──required by──> [Skills list in message]

[Post message to Slack channel]
    └──enhanced by──> [Rich Block Kit formatting]
    └──enhanced by──> [Human-readable skills list]

[Rich Block Kit formatting] ──conflicts with──> [Simple text webhook payload]
(choose one approach; mixing them produces malformed messages)
```

### Dependency Notes

- **Changed-files detection requires PR merge trigger:** The `pull_request` event context is what provides the `base_sha`/`head_sha` pair that `tj-actions/changed-files` uses. Without the PR event, diff detection requires a custom git comparison.
- **Skills list requires changed-files detection:** You cannot compute which skills changed without first running a diff against `skills/**`. The output (`all_changed_files` with `dir_names: true`) is what feeds the message.
- **Suppress-if-no-skills-changed enhances changed-files detection:** Once you have the `any_changed` boolean output, adding a `if:` conditional to the notify step is a zero-cost enhancement.
- **Block Kit formatting conflicts with plain text payload:** The `slackapi/slack-github-action` v2 `payload` input accepts either a simple `text` string OR a full Block Kit JSON object. Mixing them produces unexpected results. Decide once and commit.
- **Slack auth secret is a hard prerequisite:** Nothing else runs without a valid `SLACK_WEBHOOK_URL` secret. This must be configured before any testing.

## MVP Definition

### Launch With (v1)

The minimum needed to validate that notifications actually reach the team and contain useful information.

- [ ] Trigger on PR merge to main (`pull_request` closed + merged conditional) — without this, nothing fires
- [ ] Detect changed files under `skills/` (`tj-actions/changed-files` with `dir_names: true`) — without this, notifications lack context
- [ ] Suppress notification if no skills changed — without this, every PR (including CI/docs changes) floods the channel, destroying trust
- [ ] Post to `#qodo-skills-releases` via incoming webhook — target delivery mechanism
- [ ] Message contains: PR title, PR author, PR link, list of changed skills — the four fields called out in PROJECT.md requirements
- [ ] `SLACK_WEBHOOK_URL` stored as GitHub Actions repository secret — required for auth

### Add After Validation (v1.x)

Features to add once v1 is working and the team is actually reading the channel.

- [ ] Rich Block Kit formatting — trigger: team feedback that plain-text messages are hard to scan
- [ ] Human-readable skills list (strip `skills/` prefix, comma-separate) — low-effort polish once the raw output is confirmed working
- [ ] PR body excerpt (first 280 chars) — trigger: team asks "why can't I see what changed without opening the PR?"

### Future Consideration (v2+)

Features to defer until there is demonstrated need.

- [ ] Per-channel routing by skill — defer until there are multiple channels that want different subsets
- [ ] Message threading/updating — defer until notification volume is high enough to cause threading problems
- [ ] Multi-platform delivery — defer until a second platform is explicitly requested

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| PR merge trigger | HIGH | LOW | P1 |
| Changed-files detection (skills/) | HIGH | LOW | P1 |
| Suppress if no skills changed | HIGH | LOW | P1 |
| Post to Slack channel | HIGH | LOW | P1 |
| PR title + author + link in message | HIGH | LOW | P1 |
| Secrets management (webhook URL) | HIGH | LOW | P1 |
| Human-readable skills list | MEDIUM | LOW | P2 |
| Rich Block Kit formatting | MEDIUM | MEDIUM | P2 |
| PR body excerpt | MEDIUM | MEDIUM | P2 |
| Per-channel routing by skill | LOW | HIGH | P3 |
| Message threading | LOW | HIGH | P3 |
| Multi-platform delivery | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

This is an internal tooling workflow, not a market product. The relevant "competitors" are the ecosystem of pre-built actions and the GitHub-native Slack integration.

| Feature | GitHub-native Slack app | Off-the-shelf Slack actions | Our Approach |
|---------|------------------------|-----------------------------|--------------|
| PR merge trigger | Yes (always on) | Yes | Yes — same mechanism |
| Changed-files detection | No | Via separate action | Yes — add as a step |
| Skills-specific filtering | No | No | Yes — custom to this repo's `skills/` directory layout |
| Channel targeting | Per-repo subscription model | Hardcoded at webhook creation | Yes — single channel per PROJECT.md requirements |
| Notification content | GitHub-default (verbose, includes all PR metadata) | Configurable | Curated: title, author, link, skills list only |
| Setup complexity | Low (OAuth app install) | Low-Medium (YAML + secret) | Low (webhook + YAML) |

The key differentiator of this workflow over the GitHub-native Slack app is the skills-specific filtering: the native app notifies on every PR regardless of what changed, generating noise. This automation only fires when a `skills/` directory actually changed, and lists exactly which skills.

## Sources

- [slackapi/slack-github-action — official action v2.1.1](https://github.com/slackapi/slack-github-action) — HIGH confidence (official Slack repo)
- [tj-actions/changed-files — dir_names output support](https://github.com/marketplace/actions/changed-files) — HIGH confidence (official marketplace docs)
- [dorny/paths-filter — PR vs push context behavior](https://github.com/dorny/paths-filter) — HIGH confidence (official repo)
- [GitHub Docs — Events that trigger workflows (pull_request closed + merged)](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) — HIGH confidence (official GitHub docs)
- [GitHub Docs — Using secrets in GitHub Actions](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions) — HIGH confidence (official GitHub docs)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder) — HIGH confidence (official Slack tooling)
- [Axolo — GitHub Actions Slack integration guide 2026](https://axolo.co/blog/p/top-4-github-action-slack-integration) — MEDIUM confidence (third-party, cross-verified)
- [OneUptime — Monorepo path filters in GitHub Actions (Dec 2025)](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view) — MEDIUM confidence (third-party, aligns with official docs)

---
*Feature research for: GitHub Actions Slack notification automation (EB-28)*
*Researched: 2026-03-02*

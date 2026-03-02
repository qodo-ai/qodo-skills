# Pitfalls Research

**Domain:** GitHub Actions + Slack notification automation (CI/CD pipeline)
**Researched:** 2026-03-02
**Confidence:** HIGH (verified against official GitHub docs, Slack API docs, and CVE databases)

---

## Critical Pitfalls

### Pitfall 1: Third-Party Action Supply Chain Compromise

**What goes wrong:**
A third-party GitHub Action used in the workflow is compromised via a supply chain attack. The malicious version dumps CI runner memory — including secrets — into public workflow logs. This is not theoretical: CVE-2025-30066 hit `tj-actions/changed-files` (used in 23,000+ repos) on March 14–15, 2025. Attackers hijacked the maintainer's bot token and retroactively updated version tags to point to a malicious commit.

**Why it happens:**
Workflows pin to mutable version tags like `@v45` instead of immutable commit SHAs. When attackers compromise the action maintainer's account and repoint a tag, every repo using that tag silently runs malicious code on next trigger.

**How to avoid:**
Pin all third-party actions to a specific commit SHA, not a version tag:
```yaml
# BAD — mutable, attackable
uses: tj-actions/changed-files@v45

# GOOD — immutable, safe
uses: tj-actions/changed-files@2f7246ccbb9bab20c35e1d8c5d3a0f6c3b1fecab
```
For this project, prefer using native Git commands (`git diff --name-only`) over third-party changed-files actions entirely. The workflow is simple enough that native Git achieves the same result with zero external dependencies.

**Warning signs:**
- Workflow logs show unexpected output (base64 blobs, env dumps, curl commands)
- Security advisories from CISA or GitHub for actions you use
- Version tag points to a different commit than when you originally set it up

**Phase to address:** Initial workflow setup — pin at creation time, not as a retrofit.

---

### Pitfall 2: Slack Webhook Secret Leakage via Workflow Logs

**What goes wrong:**
The Slack webhook URL is exposed in workflow logs, either by `echo`ing it for debugging, by a compromised third-party action reading env vars (see Pitfall 1), or by a workflow that accidentally prints all environment variables. Once a webhook URL is public, anyone can post to your Slack channel.

**Why it happens:**
- Developers add `echo $SLACK_WEBHOOK_URL` debug lines and forget to remove them
- Using `env:` block at job level puts secrets in environment, where compromised steps can access them
- `set -x` or step-level debugging prints all env vars including secrets

**How to avoid:**
- Store the webhook URL as a GitHub Actions secret: `Settings > Secrets and variables > Actions`
- Reference it only as `${{ secrets.SLACK_WEBHOOK_URL }}` — GitHub Actions redacts these from logs automatically
- Never pass secrets via `env:` at the job level; pass them only to the specific step that needs them
- Never use `set -x` in steps that have access to secrets

**Warning signs:**
- Any workflow step that prints environment variables
- Debugging commits that `echo` secret values
- Third-party actions used with `env:` blocks containing secrets

**Phase to address:** Initial workflow setup — configure secrets before writing a single line of workflow YAML.

---

### Pitfall 3: Triggering on All Closed PRs, Not Just Merged Ones

**What goes wrong:**
The workflow fires when a PR is closed but not merged (e.g., abandoned, rejected, superseded). This sends a Slack notification saying "Skill X was updated" when in reality no change landed on main. Team members lose trust in the channel.

**Why it happens:**
The natural trigger is `on: pull_request: types: [closed]` — but GitHub's `closed` activity type fires for both merged and non-merged closures. Without the `merged == true` guard, every closed PR triggers the notification.

**How to avoid:**
Use the `pull_request` event with an explicit merge guard:
```yaml
on:
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  notify:
    if: github.event.pull_request.merged == true
    ...
```
Alternatively, use the `push` event on the `main` branch — a push to main only occurs when a PR merges (or a direct commit is pushed, but the project has ruled out direct commits).

**Warning signs:**
- Slack notifications arriving for PRs you know were closed without merging
- No `if: github.event.pull_request.merged == true` condition in workflow file
- Workflow firing twice on certain merge operations

**Phase to address:** Initial workflow setup — test with a draft PR closed without merging to verify the guard works.

---

### Pitfall 4: Changed-Files Detection Returns Empty on Shallow Checkout

**What goes wrong:**
The workflow uses `git diff` to detect which skills changed, but `actions/checkout` defaults to `fetch-depth: 1` (a single commit). On a push event, there is no parent commit in the local clone to diff against, so `git diff HEAD~1` returns nothing — and the notification lists zero changed skills or fails silently.

**Why it happens:**
`fetch-depth: 1` only fetches the tip commit. Diffing requires at least the preceding commit. This works fine on developer machines (full clone) but fails in CI with shallow clones.

**How to avoid:**
Set `fetch-depth: 2` to fetch the current commit and its parent (sufficient for single-commit merges):
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 2
```
For merge commits with squash merges, `fetch-depth: 2` covers the squash commit vs. its parent on main. For non-squash merges, use `fetch-depth: 0` (full history) if the PR may have many commits.

**Warning signs:**
- `git diff HEAD~1 --name-only` returns empty output in workflow logs
- Slack notifications arrive with no skills listed
- Works locally, fails in CI

**Phase to address:** Initial workflow setup — test changed-file detection explicitly before wiring up Slack.

---

### Pitfall 5: Forked PRs Gaining Access to Secrets via pull_request_target

**What goes wrong:**
If the workflow is ever migrated to use `pull_request_target` (e.g., to get write permissions or secrets for forked PRs), external contributors submitting PRs from forks gain indirect access to secrets. `pull_request_target` runs in the base repo context with full secret access even for fork-originating PRs.

**Why it happens:**
`pull_request` (the safe trigger) does not expose secrets to forked PRs by design. Developers sometimes switch to `pull_request_target` to work around this limitation — without understanding that this gives fork code the ability to exfiltrate secrets.

**How to avoid:**
This project's trigger is `on: push: branches: [main]` or `on: pull_request: types: [closed]` — neither exposes this issue. The rule is: never use `pull_request_target` unless you have explicitly audited its security implications and never check out fork code within a `pull_request_target` workflow.

**Warning signs:**
- Any occurrence of `pull_request_target` in workflow files
- Workflow files checking out `github.event.pull_request.head.sha` within `pull_request_target` jobs

**Phase to address:** Initial workflow setup — enforce the safe trigger from the start.

---

### Pitfall 6: Slack Channel Does Not Exist at Workflow Execution Time

**What goes wrong:**
The workflow runs successfully (HTTP 200 from the webhook), but the message is silently dropped because `#qodo-skills-releases` has not been created yet. Alternatively, the webhook was configured for a different channel (e.g., a test channel) and notifications never reach the intended audience.

**Why it happens:**
Webhook URLs are channel-specific. Creating the webhook before creating the destination channel, or misconfiguring the Slack app's channel binding, causes silent delivery failures. The Slack webhook endpoint returns HTTP 400 with `channel_not_found` or `channel_is_archived` — errors that are easy to miss if the workflow does not check the HTTP response.

**How to avoid:**
1. Create `#qodo-skills-releases` in Slack before configuring the webhook
2. In the workflow step that sends the Slack message, check the HTTP response code and fail the step on non-200:
```yaml
- name: Send Slack notification
  run: |
    RESPONSE=$(curl -s -o response.txt -w "%{http_code}" \
      -X POST -H 'Content-type: application/json' \
      --data "$PAYLOAD" \
      "${{ secrets.SLACK_WEBHOOK_URL }}")
    cat response.txt
    if [ "$RESPONSE" != "200" ]; then
      echo "Slack notification failed with HTTP $RESPONSE"
      exit 1
    fi
```

**Warning signs:**
- Workflow shows green but no Slack message appears
- Slack API returns `channel_not_found` or `channel_is_archived` in response body
- Webhook was created by a user who later left the workspace (webhook revoked)

**Phase to address:** Pre-implementation setup — create the channel and verify the webhook before writing workflow code.

---

## Moderate Pitfalls

### Pitfall 7: Notification Spam from Non-Skill Changes

**What goes wrong:**
Every merge to main sends a Slack notification, even when the merged PR touched only documentation, CI config files, or the README. The `#qodo-skills-releases` channel floods with irrelevant updates. Team members mute or leave the channel.

**Why it happens:**
The workflow doesn't check whether any files under `skills/` changed. It sends the notification unconditionally on every merge.

**How to avoid:**
Use `git diff` to detect files changed under `skills/` and make notification conditional:
```yaml
CHANGED_SKILLS=$(git diff HEAD~1 --name-only | grep '^skills/' | cut -d'/' -f2 | sort -u)
if [ -z "$CHANGED_SKILLS" ]; then
  echo "No skill changes detected, skipping notification"
  exit 0
fi
```

**Phase to address:** Initial workflow setup — build the filter before the notification step.

---

### Pitfall 8: Webhook URL Belongs to a Deactivated User

**What goes wrong:**
The webhook was created by a team member who later left the company. When their Slack account is deactivated, Slack revokes the tokens and integrations associated with that account. The webhook stops working silently — HTTP 403 or `token_revoked` responses.

**Why it happens:**
Slack incoming webhooks are tied to the Slack app or user who created them. Without a shared/service account or properly scoped Slack app, credentials expire when the creator leaves.

**How to avoid:**
Create the Slack app (and thus the webhook) under a shared team workspace account or a dedicated service account. Document who owns the integration. Verify the webhook is still functional periodically (a monthly manual check or a workflow that tests the webhook).

**Warning signs:**
- Slack notification workflow begins failing after a team member departure
- HTTP 403 or `token_revoked` in workflow logs
- No recent Slack messages in `#qodo-skills-releases` despite known merges

**Phase to address:** Initial Slack app setup — use a team/service account from the start.

---

### Pitfall 9: Duplicate Notifications from Concurrent Workflow Runs

**What goes wrong:**
Two PRs merge in rapid succession. Both trigger the notification workflow simultaneously. Due to Git timing or re-runs, the same merge commit triggers the workflow twice, posting duplicate Slack messages.

**Why it happens:**
Without a concurrency group, GitHub Actions runs all triggered workflows simultaneously. Merge queues or re-triggered runs can cause the same SHA to emit multiple notifications.

**How to avoid:**
Add a concurrency group keyed on the commit SHA:
```yaml
concurrency:
  group: notify-slack-${{ github.sha }}
  cancel-in-progress: false
```
`cancel-in-progress: false` ensures notifications are never dropped — they queue instead of cancel.

**Phase to address:** Initial workflow setup.

---

## Minor Pitfalls

### Pitfall 10: Slack Rate Limit Hit During Batch Merges

**What goes wrong:**
Multiple PRs merge within a short window (e.g., a merge queue flush). Each triggers a notification. Slack's incoming webhook rate limit is 1 message per second with burst tolerance. If 5+ notifications fire within seconds, some return HTTP 429 and are lost.

**Why it happens:**
Each workflow run calls the webhook independently with no backoff logic.

**How to avoid:**
For this project's scale (small team, infrequent merges), the 1/second limit is unlikely to be hit. If it becomes a problem, add a simple retry with backoff in the curl command. Mark this as low-priority until evidence of rate limiting appears.

**Phase to address:** Future enhancement only if observed.

---

### Pitfall 11: Skill Detection Regex Too Broad or Too Narrow

**What goes wrong:**
The regex used to extract skill names from changed file paths either (a) matches non-skill directories under `skills/` (e.g., a `skills/README.md`), or (b) misses renamed skills because it only looks at the new path, not the old one.

**Why it happens:**
`skills/` contains both skill subdirectories and root-level files. Simple `grep '^skills/'` picks up root-level files. Rename detection requires looking at both sides of a rename operation.

**How to avoid:**
Filter to paths with exactly two path components under `skills/`:
```bash
git diff HEAD~1 --name-only | grep -E '^skills/[^/]+/' | cut -d'/' -f2 | sort -u
```
This captures `skills/qodo-get-rules/SKILL.md` as skill `qodo-get-rules` but ignores `skills/README.md`.

**Phase to address:** Initial workflow setup.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `@v45` tag pinning for third-party actions | Easier to read | Vulnerable to supply chain attacks (CVE-2025-30066) | Never — always pin to SHA |
| Use `push` trigger without `paths` filter | Simpler workflow | Notifies on every commit, not just skill changes | Never — add skill path check |
| Skip HTTP response validation on Slack call | Less code | Silent failures — green workflow, no notification | Never — always validate |
| Hardcode channel name in workflow | Easier setup | Channel name changes break silently | Never — use secret or env var |
| Use `pull_request_target` for access to secrets | Access to all secrets | Secrets exposed to fork code | Never for this project |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Slack incoming webhook | Create webhook before creating the destination channel | Create channel first, then configure webhook to that channel |
| Slack incoming webhook | Store webhook URL as plaintext in workflow YAML | Store as GitHub Actions secret, reference as `${{ secrets.SLACK_WEBHOOK_URL }}` |
| GitHub Actions checkout | Use default `fetch-depth: 1` for diff-based detection | Set `fetch-depth: 2` (or `0` for full history) before running `git diff` |
| GitHub Actions trigger | Use `pull_request: types: [closed]` without merge guard | Add `if: github.event.pull_request.merged == true` or switch to `push` on `main` |
| Third-party actions | Pin to version tag | Pin to commit SHA to prevent supply chain attacks |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Printing `$SLACK_WEBHOOK_URL` in workflow logs | Webhook URL becomes public; anyone can spam the channel | Never echo secrets; GitHub redacts them only when referenced via `${{ secrets.* }}` |
| Using `pull_request_target` with fork checkout | Fork code can exfiltrate all CI secrets | Use `pull_request` (no secrets for forks) or `push` on `main` |
| Granting excessive `GITHUB_TOKEN` permissions | Token used in privilege escalation if workflow is compromised | Set `permissions: contents: read` at workflow level — notification workflow needs no write permissions |
| Pinning third-party actions to mutable tags | Supply chain compromise via tag hijacking (CVE-2025-30066) | Pin to commit SHA; audit periodically |
| Webhook URL tied to departing team member account | Credentials revoked when account deactivated | Create under shared/service account |

---

## "Looks Done But Isn't" Checklist

- [ ] **Trigger filter:** Does the workflow have `if: github.event.pull_request.merged == true` (or equivalent `push` trigger)? Verify by closing a PR without merging — no notification should fire.
- [ ] **Skill filter:** Does the notification only fire when `skills/**` files changed? Verify by merging a docs-only PR — no notification should fire.
- [ ] **Changed skills list:** Does the Slack message list the actual skill names? Verify with a PR touching `skills/qodo-get-rules/` — message should say "qodo-get-rules".
- [ ] **Fetch depth:** Is `fetch-depth: 2` (or `0`) set on `actions/checkout`? Verify that `git diff HEAD~1 --name-only` returns non-empty output in workflow logs.
- [ ] **Slack channel exists:** Does `#qodo-skills-releases` exist in the Slack workspace before the webhook is configured?
- [ ] **Webhook secret:** Is `SLACK_WEBHOOK_URL` stored as a GitHub Actions secret (not hardcoded in YAML)?
- [ ] **HTTP validation:** Does the workflow check the Slack API response code and fail on non-200?
- [ ] **Action SHA pinning:** Are all third-party actions pinned to commit SHAs, not version tags?

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Webhook URL leaked in logs | MEDIUM | Rotate webhook immediately in Slack app settings; update GitHub secret; audit who may have seen the logs |
| Webhook stops working (revoked/channel archived) | LOW | Recreate the incoming webhook under a service account; update the GitHub secret |
| Supply chain compromise via third-party action | HIGH | Rotate all CI secrets immediately; audit all workflow run logs; pin actions to SHAs; file incident report |
| Notification spam (filter missing) | LOW | Add skill path filter to workflow; re-deploy; alert team that spam period is over |
| Duplicate notifications (concurrent runs) | LOW | Add concurrency group to workflow; accept that a small number of duplicates may have already fired |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Third-party action supply chain (SHA pinning) | Phase 1: Workflow setup | Check that `uses:` lines reference SHA hashes, not tags |
| Webhook secret leakage | Phase 1: Secrets config | Verify `SLACK_WEBHOOK_URL` is a GitHub Actions secret, not in YAML |
| Firing on closed-not-merged PRs | Phase 1: Trigger config | Close a PR without merging; confirm no notification fires |
| Empty changed-files list (shallow clone) | Phase 1: Checkout config | Check workflow logs for non-empty `git diff` output |
| No skill filter (notification spam) | Phase 1: Filter logic | Merge a docs-only PR; confirm no notification fires |
| Slack channel doesn't exist | Pre-implementation setup | Manually verify channel exists and webhook test posts successfully |
| Webhook owned by departing member | Pre-implementation setup | Document that webhook must be under a shared account |
| Duplicate notifications (concurrency) | Phase 1: Workflow setup | Check for `concurrency:` block in workflow YAML |
| Forked PR secrets exposure | Phase 1: Trigger choice | Confirm workflow uses `push` on `main` or `pull_request` (not `pull_request_target`) |

---

## Sources

- [CVE-2025-30066: tj-actions/changed-files supply chain attack — CISA advisory](https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction) (HIGH confidence — official CISA advisory)
- [GitHub Actions: pull_request_target security and branch protection changes (Dec 2025)](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/) (HIGH confidence — official GitHub changelog)
- [Preventing pwn requests — GitHub Security Lab](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/) (HIGH confidence — official GitHub Security Lab)
- [Slack incoming webhooks rate limits — Slack Developer Docs](https://docs.slack.dev/apis/web-api/rate-limits/) (HIGH confidence — official Slack documentation)
- [Controlling permissions for GITHUB_TOKEN — GitHub Docs](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token) (HIGH confidence — official GitHub documentation)
- [GitHub Actions workflow trigger events — GitHub Docs](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions) (HIGH confidence — official GitHub documentation)
- [Wiz blog: tj-actions/changed-files supply chain attack analysis](https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066) (MEDIUM confidence — security vendor analysis)
- [Orca Security: pull_request_target exploitation](https://orca.security/resources/blog/pull-request-nightmare-part-2-exploits/) (MEDIUM confidence — security vendor research)
- [Detecting and mitigating tj-actions attack — Sysdig](https://www.sysdig.com/blog/detecting-and-mitigating-the-tj-actions-changed-files-supply-chain-attack-cve-2025-30066) (MEDIUM confidence — security vendor analysis)
- [GitHub community: fetch-depth and changed files discussions](https://github.com/tj-actions/changed-files/discussions/1411) (MEDIUM confidence — community discussion with maintainer participation)

---
*Pitfalls research for: GitHub Actions + Slack notification automation*
*Researched: 2026-03-02*

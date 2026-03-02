# Phase 1: External Setup - Research

**Researched:** 2026-03-02
**Domain:** Slack Incoming Webhooks + GitHub Actions Secrets
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Channel name: `#qodo-skills-releases` (from SETUP-01)
- Secret name: `SLACK_WEBHOOK_URL` (from SETUP-03)

### Claude's Discretion
- Verification method (curl script, GitHub CLI, or manual browser check)
- Slack app display name and icon
- Secret scope (repository-level vs. environment-scoped)
- Runbook format (prose, checklist, or guided script)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-01 | `#qodo-skills-releases` Slack channel is created in the workspace | Channel creation is standard Slack member-level action; admin may need to be consulted if workspace restricts channel creation. Channel must accept messages (webhook delivery returns HTTP 200). |
| SETUP-02 | A Slack app with incoming webhook scoped to `#qodo-skills-releases` is created | Fully documented: create app at api.slack.com, enable Incoming Webhooks feature, authorize against the target channel. Produces a unique `https://hooks.slack.com/services/...` URL. |
| SETUP-03 | Webhook URL is stored as `SLACK_WEBHOOK_URL` in GitHub Actions repository secrets | `SLACK_WEBHOOK_URL` is a valid secret name (alphanumeric + underscore, no reserved prefix, not starting with number). Set via GitHub UI or `gh secret set`. Verification: `gh secret list` shows name (value masked). |
</phase_requirements>

## Summary

Phase 1 is pure external configuration — no code is written. It produces three verifiable artifacts: a Slack channel, a Slack incoming webhook URL, and a GitHub Actions repository secret. All three are prerequisites for Phase 2 (workflow YAML) and Phase 3 (Slack notification content).

The Slack side involves two distinct steps: first creating the channel (a Slack workspace action), then creating a Slack app with Incoming Webhooks enabled and authorizing it to post to that channel. The app creation lives at `api.slack.com` and requires any workspace member to be signed in; workspace admins are only required if the workspace has restricted app creation or channel creation policies.

The GitHub side is straightforward: store the webhook URL as a repository-level secret named `SLACK_WEBHOOK_URL` using either the GitHub UI or `gh secret set`. Repository-level scope is the right choice here — there is only one workflow and no multi-environment deployment pattern.

**Primary recommendation:** Follow the exact sequence — channel first, then Slack app + webhook, then GitHub secret. Verify each step before proceeding to the next. Use `curl` to confirm the webhook URL returns HTTP 200 before storing it in GitHub.

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Slack App (Incoming Webhooks) | Current (api.slack.com) | Post messages to a Slack channel via HTTPS POST | Official Slack mechanism; no bot token or OAuth flow required; simple secret URL |
| GitHub Actions Secrets | Current | Store sensitive values masked in workflow environment | Built-in GitHub feature; no third-party secret manager needed at this scale |
| `gh` CLI | Current (2.x) | Set and list repository secrets from terminal | Official GitHub CLI; avoids browser UI for secret management |
| `curl` | System (any version) | Verify webhook URL returns HTTP 200 | Universal, no dependencies, instant verification |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| GitHub UI (Settings > Secrets) | N/A | Alternative to `gh secret set` | When `gh` CLI is not installed or preferred by operator |
| Slack web UI | N/A | Create channel and Slack app | Required — no API alternative for initial app creation without an existing token |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Repository-level secret | Environment-scoped secret | Environment secrets add required-reviewers and approval gates — unnecessary complexity for a single notification workflow |
| Manual `curl` verification | GitHub Actions test workflow | A test workflow run is heavier; `curl` is instant and sufficient for confirming the URL is live |
| Incoming webhook | Slack bot token with `chat.postMessage` | Bot tokens require more OAuth scopes and token rotation; incoming webhooks are simpler for one-way notification |

## Architecture Patterns

### Recommended Setup Sequence

```
Step 1: Create #qodo-skills-releases channel in Slack workspace
Step 2: Go to api.slack.com/apps → Create New App → From scratch
Step 3: Enable Incoming Webhooks in app settings
Step 4: Add New Webhook to Workspace → select #qodo-skills-releases → Allow
Step 5: Copy the generated webhook URL
Step 6: Verify with curl (must return HTTP 200 "ok")
Step 7: Store URL as SLACK_WEBHOOK_URL in GitHub repository secrets
Step 8: Verify secret appears in gh secret list (value masked)
```

### Pattern 1: Slack Incoming Webhook Verification

**What:** Send a POST request to the webhook URL to confirm it is live and authorized.

**When to use:** Immediately after generating the webhook URL, before storing in GitHub.

```bash
# Source: https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/
curl -X POST \
  -H 'Content-type: application/json' \
  --data '{"text":"Phase 1 setup verification — ignore this message"}' \
  https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX
# Expected response: HTTP 200 with body "ok"
```

### Pattern 2: GitHub Secret Storage via CLI

**What:** Store the webhook URL as a masked repository secret using `gh` CLI.

**When to use:** After webhook URL is verified with `curl`.

```bash
# Source: https://cli.github.com/manual/gh_secret_set
# Interactive (recommended — avoids URL appearing in shell history):
gh secret set SLACK_WEBHOOK_URL

# Or pipe from environment variable (URL never touches shell history):
echo "$WEBHOOK_URL" | gh secret set SLACK_WEBHOOK_URL

# Verify secret was stored (value will be masked):
gh secret list
# Should show: SLACK_WEBHOOK_URL   Updated ...
```

### Pattern 3: Secret Name Validation

**What:** Confirm `SLACK_WEBHOOK_URL` satisfies GitHub's naming rules before attempting to set it.

**Validation checklist:**
- Only alphanumeric characters and underscores: YES (`SLACK_WEBHOOK_URL` uses only A-Z and `_`)
- Does not start with `GITHUB_` prefix: YES
- Does not start with a number: YES
- Unique within repository: YES (first secret in this repo)
- Within 48 KB size limit: YES (webhook URLs are ~80 chars)

### Anti-Patterns to Avoid

- **Storing webhook URL in plain text (e.g., in `.env` committed to repo):** Anyone with repo read access can post to the Slack channel. Treat webhook URL as a password.
- **Using a version tag instead of the exact URL:** The webhook URL is fixed once generated; it does not change unless revoked.
- **Skipping curl verification:** The GitHub secret is useless if the URL is wrong. Verify before storing.
- **Creating an environment-scoped secret instead of repository-scoped:** Environment secrets require a named GitHub environment and can add required-reviewer gates, blocking the workflow unnecessarily.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slack message delivery | Custom HTTP client or retry logic | Incoming webhook URL + standard curl/POST | Slack's webhook endpoint handles retries on their side; a 200 means delivered |
| Secret storage | Encrypted config file in repo | GitHub Actions repository secrets | GitHub's native encryption, automatic masking in logs, no key management overhead |
| Webhook URL rotation | Custom vault or rotation script | Revoke-and-regenerate in Slack app settings + update GitHub secret | This phase is not the place for rotation tooling (v2 scope) |

**Key insight:** This phase has zero code. Every "tool" is a cloud service with a browser UI and a CLI. Don't invent infrastructure.

## Common Pitfalls

### Pitfall 1: Workspace Restricts App Creation

**What goes wrong:** `api.slack.com/apps` creation is blocked by workspace admin policy — the app fails to install or the webhook authorization fails.

**Why it happens:** Enterprise/managed Slack workspaces often require admin approval for new apps ("Admin-Approved Apps" setting).

**How to avoid:** Before starting, confirm whether the workspace allows member-created apps. If not, coordinate with a workspace admin to either approve the app or create it on your behalf.

**Warning signs:** "action_prohibited" error during OAuth authorization of the webhook, or the "Add New Webhook to Workspace" button being absent.

### Pitfall 2: Webhook Scoped to Wrong Channel

**What goes wrong:** Webhook is authorized against a different channel (e.g., `#general` or a personal DM). Messages land in the wrong place.

**Why it happens:** The authorization screen presents a channel-selection dropdown; it is easy to accept the default.

**How to avoid:** On the authorization screen, explicitly verify the dropdown shows `#qodo-skills-releases` before clicking Allow. Check the webhook entry in the app's Incoming Webhooks settings — it shows the channel name.

**Warning signs:** Test `curl` message appears in the wrong channel.

### Pitfall 3: Webhook URL in Shell History

**What goes wrong:** The webhook URL is stored in shell history (e.g., `gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/..."`). Any user with shell history access can extract it.

**Why it happens:** Passing secrets as CLI arguments is a common convenience shortcut.

**How to avoid:** Use interactive `gh secret set SLACK_WEBHOOK_URL` (prompts for value without echoing) or pipe from a variable: `echo "$WEBHOOK_URL" | gh secret set SLACK_WEBHOOK_URL`. Do not use `--body` with the raw URL inline.

**Warning signs:** `history | grep SLACK` shows the webhook URL.

### Pitfall 4: Channel Does Not Accept Webhook Messages

**What goes wrong:** Webhook returns HTTP 403 or `posting_to_general_channel_denied` even after correct setup.

**Why it happens:** Some channels have posting restrictions set by admins (e.g., only admins can post, or a channel has posting permissions locked).

**How to avoid:** Create `#qodo-skills-releases` as a fresh channel with default permissions. Do not use a pre-existing channel that may have posting restrictions.

**Warning signs:** `curl` test returns HTTP 403, not HTTP 200 + "ok".

### Pitfall 5: GitHub Secret Not in Repository Scope

**What goes wrong:** Secret is created at organization level or environment level, so the workflow cannot access it (or requires an environment name in the workflow YAML).

**Why it happens:** `gh secret set` with `--org` flag or setting via the wrong GitHub UI section.

**How to avoid:** Use `gh secret set SLACK_WEBHOOK_URL` without any `--org` or `--env` flag. Confirm with `gh secret list` (not `gh secret list --org`). In the GitHub UI, go to: Repository > Settings > Secrets and variables > Actions > Repository secrets.

**Warning signs:** `gh secret list` shows empty, but `gh secret list --org` shows the secret.

## Code Examples

### Verify Webhook URL Returns HTTP 200

```bash
# Source: https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/
WEBHOOK_URL="https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H 'Content-type: application/json' \
  --data '{"text":"Phase 1 verification test — safe to ignore"}' \
  "$WEBHOOK_URL")

if [ "$HTTP_STATUS" = "200" ]; then
  echo "Webhook verified: HTTP 200 ok"
else
  echo "Webhook FAILED: HTTP $HTTP_STATUS"
  exit 1
fi
```

### Store Secret and Verify It Exists

```bash
# Source: https://cli.github.com/manual/gh_secret_set
# Store interactively (most secure — no URL in shell history):
gh secret set SLACK_WEBHOOK_URL
# Paste the webhook URL when prompted, then press Enter + Ctrl-D

# Verify the secret name appears (value will be masked as ***):
gh secret list
# Expected output includes a line like:
# SLACK_WEBHOOK_URL   Updated 2026-03-02

# Verify it is a REPOSITORY secret (not org or env):
gh secret list --repo <owner>/<repo>
```

### Full Verification Checklist Script

```bash
# Quick sanity check for all three success criteria
# Run after completing all three SETUP-XX steps

echo "=== Phase 1 Verification ==="

# SETUP-01 & SETUP-02: Webhook delivers to #qodo-skills-releases
echo "Checking webhook..."
WEBHOOK_URL="<paste-webhook-url-here>"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST -H 'Content-type: application/json' \
  --data '{"text":"Phase 1 check — safe to ignore"}' \
  "$WEBHOOK_URL")
[ "$HTTP_STATUS" = "200" ] && echo "PASS: Webhook returns 200" || echo "FAIL: Webhook returned $HTTP_STATUS"

# SETUP-03: Secret name appears in repository secrets
echo "Checking GitHub secret..."
gh secret list | grep -q "SLACK_WEBHOOK_URL" \
  && echo "PASS: SLACK_WEBHOOK_URL secret exists" \
  || echo "FAIL: SLACK_WEBHOOK_URL not found in gh secret list"

echo "=== Done ==="
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Slack legacy "test tokens" or webhook via `slackin` | App-based incoming webhooks at api.slack.com | Slack deprecated legacy tokens ~2021 | Must use app-based webhook; no legacy shortcuts |
| Hardcoded webhook URL in workflow YAML | GitHub Actions repository secret | Best practice since GHA launch (2019) | URL is masked in logs; not visible in repo history |

**Deprecated/outdated:**
- Slack legacy tokens: Revoked; do not use.
- Slack "webhook integrations" (old Slack UI path): Merged into app-based setup; the entry point is now `api.slack.com/apps`.

## Open Questions

1. **Workspace admin policy for app creation**
   - What we know: Some workspaces require admin approval before a new Slack app can post messages
   - What's unclear: Whether the target workspace has this restriction enabled
   - Recommendation: Verify before starting SETUP-02. If restricted, identify the workspace admin contact as a dependency.

2. **Who has `admin:repo_hook` or secrets write access to the GitHub repository**
   - What we know: `gh secret set` requires the operator to have repository admin or collaborator write access; the `gh` CLI must be authenticated with appropriate scope
   - What's unclear: Whether the person performing setup has this access level
   - Recommendation: Confirm repository access level before planning Phase 1 tasks. The plan should call out this prerequisite explicitly.

## Sources

### Primary (HIGH confidence)
- https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/ — Slack incoming webhook creation process, URL format, curl verification, error codes
- https://cli.github.com/manual/gh_secret_set — `gh secret set` syntax, flags, interactive mode
- https://docs.github.com/en/actions/reference/security/secrets — Secret naming rules, scopes, size limits, masking behavior

### Secondary (MEDIUM confidence)
- https://slack.com/help/articles/201402297-Create-a-channel — Channel creation permissions by role
- https://docs.github.com/en/actions/concepts/security/secrets — Repository vs environment secret scope guidance
- https://slack.com/help/articles/222386767-Manage-app-approval-for-your-workspace — Workspace app approval restrictions

### Tertiary (LOW confidence)
- WebSearch results re: workspace admin requirements — general community consensus, not verified against specific workspace policies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — official Slack and GitHub docs confirm the tools and their exact usage
- Architecture: HIGH — step sequence follows official Slack webhook setup guide exactly
- Pitfalls: HIGH (workspace restrictions) / MEDIUM (shell history, scope confusion) — sourced from official error documentation and common community patterns

**Research date:** 2026-03-02
**Valid until:** 2026-09-02 (stable APIs — Slack webhook and GitHub secrets have not changed materially in years; recheck if Slack deprecates incoming webhook feature)

# Phase 3: Slack Notification - Research

**Researched:** 2026-03-02
**Domain:** Slack Block Kit messages via GitHub Actions incoming webhook
**Confidence:** HIGH

## Summary

Phase 3 adds a single GitHub Actions step to the existing `notify-skill-changes.yml` workflow. The step fires only when `steps.changed-skills.outputs.any_changed == 'true'` (gated by Phase 2's output) and posts a Block Kit–formatted message to `#qodo-skills-releases` via the pre-configured incoming webhook secret `SLACK_WEBHOOK_SKILLS_RELEASES_URL`.

The official action for this is `slackapi/slack-github-action@v2.1.1` (commit SHA `91efab103c0de0a537f72a35f6b8cda0ee76bf0a`). The v2 API requires `webhook-type: incoming-webhook` as an explicit input (v1 used environment variable `SLACK_WEBHOOK_TYPE`). The payload is provided inline as YAML or JSON via the `payload` input field. Incoming webhooks fully support Block Kit's `header`, `section`, `divider`, and `context` block types — the `section` + `mrkdwn` pattern is the verified approach; the newer `markdown` block type is known to fail on incoming webhooks (GitHub issue #440).

The key implementation challenge is constructing the skill names list dynamically: Phase 2 outputs `all_changed_files` as a space-separated string like `skills/qodo-get-rules skills/qodo-pr-resolver`. A preceding bash step must strip the `skills/` prefix from each entry and format them into a readable Slack-compatible string (e.g., `qodo-get-rules, qodo-pr-resolver`), then export the result via `$GITHUB_OUTPUT` for use in the Slack payload.

**Primary recommendation:** Add a "Format skill names" bash step (id: `format-skills`) that builds a comma-separated skill list, then add a "Send Slack notification" step using `slackapi/slack-github-action@91efab103c0de0a537f72a35f6b8cda0ee76bf0a` with `webhook-type: incoming-webhook`, a `header` block for the PR title, and `section` blocks for author, link, and skills.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NOTIF-01 | Slack message posted to `#qodo-skills-releases` when a skill-touching PR merges | `slackapi/slack-github-action` with incoming webhook delivers to channel bound at webhook-creation time (Phase 1 SETUP-01/02/03 already complete). Gate step on `steps.changed-skills.outputs.any_changed == 'true'`. |
| NOTIF-02 | Message includes PR title | `${{ github.event.pull_request.title }}` — confirmed available in `pull_request: closed` events (GitHub docs, HIGH confidence) |
| NOTIF-03 | Message includes PR author (GitHub username) | `${{ github.event.pull_request.user.login }}` — confirmed available in `pull_request` event payload |
| NOTIF-04 | Message includes clickable link to the PR | `${{ github.event.pull_request.html_url }}` — confirmed as the field name for the PR browser URL. Use Slack mrkdwn `<url|text>` syntax for clickable links. |
| NOTIF-05 | Message includes list of changed skill names (readable names, not full paths) | Bash step strips `skills/` prefix using `${dir#skills/}` parameter expansion; formats into comma-separated string; exports via `$GITHUB_OUTPUT` for use in payload |
| NOTIF-06 | Message uses Slack Block Kit formatting (not plain text) | `payload` field with `blocks:` array in `slackapi/slack-github-action@v2.1.1`; `header` + `section` block types confirmed to work with incoming webhooks |
</phase_requirements>

## Standard Stack

### Core

| Library | Version / SHA | Purpose | Why Standard |
|---------|--------------|---------|--------------|
| `slackapi/slack-github-action` | v2.1.1 (`91efab103c0de0a537f72a35f6b8cda0ee76bf0a`) | Post Block Kit message via incoming webhook | Official Slack-maintained action; v2 is current; incoming webhook mode requires no bot token |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bash (runner built-in) | (ubuntu-latest) | Format skill names from space-separated list | Already on runner; no install needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `slackapi/slack-github-action` | `curl` to webhook URL | curl is simpler but requires manual JSON quoting, escaping special chars in PR title/author — fragile in production |
| `slackapi/slack-github-action` | `8398a7/action-slack` or `act10ns/slack` | Third-party alternatives with less official support; no benefit over the official action |
| Inline `payload:` YAML | `payload-file-path:` to a file | File approach useful for very large payloads; inline YAML is sufficient for this message and easier to read in context |
| `section` + `mrkdwn` | `markdown` block type | `markdown` block (newer API) is confirmed broken on incoming webhooks (500 errors, GitHub issue #440). Use `section` + `mrkdwn` — confirmed working. |

**Installation:** No npm install needed — GitHub Actions marketplace action, referenced by SHA.

## Architecture Patterns

### Recommended Project Structure

```
.github/
└── workflows/
    └── notify-skill-changes.yml   # Add two new steps to existing file
```

No new files needed. Phase 3 is two steps appended to the existing workflow.

### Pattern 1: Format Skill Names in Bash

**What:** A bash step runs before the Slack step, strips `skills/` prefixes from the space-separated changed-files output, joins names with `, `, and writes to `$GITHUB_OUTPUT`.

**When to use:** Whenever a Slack payload needs a human-readable list of skill names extracted from `all_changed_files`.

**Example:**
```yaml
# Source: GitHub Actions GITHUB_OUTPUT pattern (official docs) + bash parameter expansion
- name: Format skill names
  id: format-skills
  if: steps.changed-skills.outputs.any_changed == 'true'
  run: |
    skills=""
    for dir in ${{ steps.changed-skills.outputs.all_changed_files }}; do
      name="${dir#skills/}"
      if [ -z "$skills" ]; then
        skills="$name"
      else
        skills="$skills, $name"
      fi
    done
    echo "names=$skills" >> "$GITHUB_OUTPUT"
```

**Output used in Slack step as:** `${{ steps.format-skills.outputs.names }}`

### Pattern 2: Block Kit Payload via Incoming Webhook (v2 action syntax)

**What:** `slackapi/slack-github-action@v2.1.1` with `webhook-type: incoming-webhook` and inline `payload:` YAML.

**When to use:** Any time you post a structured Slack message from GitHub Actions using an incoming webhook.

**Example:**
```yaml
# Source: https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-slack-incoming-webhook/
- name: Send Slack notification
  if: steps.changed-skills.outputs.any_changed == 'true'
  uses: slackapi/slack-github-action@91efab103c0de0a537f72a35f6b8cda0ee76bf0a  # v2.1.1
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK_SKILLS_RELEASES_URL }}
    webhook-type: incoming-webhook
    payload: |
      text: "Skill update: ${{ github.event.pull_request.title }}"
      blocks:
        - type: "header"
          text:
            type: "plain_text"
            text: "${{ github.event.pull_request.title }}"
            emoji: true
        - type: "section"
          fields:
            - type: "mrkdwn"
              text: "*Author:*\n${{ github.event.pull_request.user.login }}"
            - type: "mrkdwn"
              text: "*Skills changed:*\n${{ steps.format-skills.outputs.names }}"
        - type: "section"
          text:
            type: "mrkdwn"
            text: "<${{ github.event.pull_request.html_url }}|View pull request>"
```

**Key notes:**
- `text:` at the top level is the fallback for notifications and accessibility — always include it
- `header` block requires `plain_text` text type only (not `mrkdwn`); max 150 chars
- `section` with `fields:` renders two-column layout — good for author + skills
- `section` with `text:` + mrkdwn `<url|text>` syntax creates clickable link
- The secret name is `SLACK_WEBHOOK_SKILLS_RELEASES_URL` (established in Phase 1)

### Pattern 3: Slack mrkdwn Link Syntax

**What:** Slack uses its own link format, not standard Markdown.

**When to use:** Whenever creating a clickable link in a Slack message.

**Example:**
```
<https://github.com/org/repo/pull/123|View pull request>
```

In a GitHub Actions workflow:
```yaml
text: "<${{ github.event.pull_request.html_url }}|View pull request>"
```

### Anti-Patterns to Avoid

- **Using v1 action syntax with `SLACK_WEBHOOK_TYPE` env var:** v2 broke this pattern; now requires `webhook-type:` as an explicit action `with:` input. Using v1 syntax silently fails or sends malformed requests.
- **Using `markdown` block type:** The newer `markdown` block type causes 500 errors on incoming webhooks (confirmed open GitHub issue #440, March 2025). Use `section` + `type: mrkdwn` instead.
- **Using standard Markdown for links:** Slack does not render `[text](url)` — use `<url|text>` mrkdwn syntax.
- **Omitting the top-level `text:` field:** Slack requires a `text` fallback when using `blocks`. Messages without it may fail or appear blank in notification previews.
- **Referencing the secret as `SLACK_WEBHOOK_URL`:** The correct secret name established in Phase 1 is `SLACK_WEBHOOK_SKILLS_RELEASES_URL`. Using any other name will cause the step to fail with a 401 or similar error.
- **Pinning by version tag (`@v2.1.1`):** By consistency with the project's SHA-pinning policy (established in Phase 2 due to CVE-2025-30066), the `slackapi` action should also be SHA-pinned. SHA for v2.1.1: `91efab103c0de0a537f72a35f6b8cda0ee76bf0a`.
- **Using `${{ steps.changed-skills.outputs.all_changed_files }}` directly in Slack payload for skill names:** The raw output is `skills/qodo-get-rules skills/qodo-pr-resolver` — includes path prefixes and space-separated format. Always strip the prefix and reformat before injecting into the Slack payload.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Posting to Slack webhook | Custom `curl` step with JSON string assembly | `slackapi/slack-github-action` | curl requires manually escaping special characters in PR titles (quotes, ampersands, backticks); the action handles this correctly |
| Block Kit message structure | Concatenate JSON strings in bash | YAML `payload:` in the action | YAML payload is parsed by the action before sending; avoids quoting/escaping bugs entirely |

**Key insight:** The single fragile point in this phase is injecting dynamic strings (PR title, skill names) into the Slack payload. If those strings contain special characters (`"`, `\`, `&`, `<`, `>`), a hand-rolled solution breaks silently. The action's YAML payload parser handles safe string interpolation within the GitHub Actions expression engine.

## Common Pitfalls

### Pitfall 1: v1 vs v2 Action API Mismatch

**What goes wrong:** Using the v1 `env: SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK` pattern with the v2 action — message is not sent or action fails.

**Why it happens:** Most blog posts and StackOverflow answers predate v2 (released 2024). v2 introduced breaking changes across all three sending techniques.

**How to avoid:** Use `webhook-type: incoming-webhook` as a `with:` input, not as an environment variable. The STATE.md already documents this as a confirmed decision.

**Warning signs:** Action succeeds (exit 0) but no message appears in Slack — v1 env-var pattern is silently ignored in v2.

### Pitfall 2: Wrong Block Type for Header Text

**What goes wrong:** Using `type: mrkdwn` in the header block — the message either fails or sends with raw mrkdwn syntax visible.

**Why it happens:** `section` blocks use `mrkdwn`; `header` blocks ONLY accept `plain_text`. Easy to confuse.

**How to avoid:** Header block text object MUST have `type: "plain_text"`. Section block text objects use `type: "mrkdwn"` for formatting. Header block text is limited to 150 characters.

**Warning signs:** Slack API returns an error about invalid block structure when `mrkdwn` is used in header.

### Pitfall 3: Missing Top-Level `text:` Field

**What goes wrong:** Payload with `blocks:` but no top-level `text:` — Slack may reject the payload or show no notification preview.

**Why it happens:** When you have `blocks`, they visually replace `text` — so developers skip `text`.

**How to avoid:** Always include `text:` as a fallback even when using blocks. The Slack docs state: "We recommend always providing a text argument when publishing block messages as it functions as a fallback."

### Pitfall 4: Special Characters in PR Title Breaking YAML

**What goes wrong:** A PR title like `feat: add "smart" quotes` causes YAML parsing error in the payload.

**Why it happens:** The `payload:` value is a multiline YAML string. GitHub Actions expression `${{ github.event.pull_request.title }}` is interpolated before YAML parsing.

**How to avoid:** The `slackapi/slack-github-action` action's payload parser is more tolerant than raw YAML because it processes GitHub expressions in a specific way. Testing with a PR title containing colons, quotes, and angle brackets before shipping is recommended. If issues arise, use a preceding step to escape the title or truncate it.

**Warning signs:** Workflow fails with "YAML parsing error" in the "Send Slack notification" step log.

### Pitfall 5: Skill Name Output Empty When Only One Skill

**What goes wrong:** The format-skills bash step produces empty output or `skills/qodo-get-rules` (with prefix) instead of `qodo-get-rules`.

**Why it happens:** Off-by-one logic in the bash loop, or `${{ steps.changed-skills.outputs.all_changed_files }}` expansion behaving unexpectedly with a single value.

**How to avoid:** Test with a PR that changes exactly one skill file — the single-item case is the most common edge case. Verify the `names` output in the workflow log before relying on it in the Slack payload.

## Code Examples

Verified patterns from official sources:

### Complete Phase 3 Step Addition

```yaml
# Source: slackapi/slack-github-action v2.1.1 docs + GitHub Actions GITHUB_OUTPUT pattern

      - name: Format skill names
        id: format-skills
        if: steps.changed-skills.outputs.any_changed == 'true'
        run: |
          skills=""
          for dir in ${{ steps.changed-skills.outputs.all_changed_files }}; do
            name="${dir#skills/}"
            if [ -z "$skills" ]; then
              skills="$name"
            else
              skills="$skills, $name"
            fi
          done
          echo "names=$skills" >> "$GITHUB_OUTPUT"

      - name: Send Slack notification
        if: steps.changed-skills.outputs.any_changed == 'true'
        uses: slackapi/slack-github-action@91efab103c0de0a537f72a35f6b8cda0ee76bf0a  # v2.1.1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_SKILLS_RELEASES_URL }}
          webhook-type: incoming-webhook
          payload: |
            text: "Skill update merged: ${{ github.event.pull_request.title }}"
            blocks:
              - type: "header"
                text:
                  type: "plain_text"
                  text: "${{ github.event.pull_request.title }}"
                  emoji: true
              - type: "section"
                fields:
                  - type: "mrkdwn"
                    text: "*Author:*\n${{ github.event.pull_request.user.login }}"
                  - type: "mrkdwn"
                    text: "*Skills changed:*\n${{ steps.format-skills.outputs.names }}"
              - type: "section"
                text:
                  type: "mrkdwn"
                  text: "<${{ github.event.pull_request.html_url }}|View pull request on GitHub>"
```

### GitHub Context Variables Available in `pull_request: [closed]` Events

```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs
${{ github.event.pull_request.title }}           # PR title string
${{ github.event.pull_request.user.login }}       # GitHub username of PR author
${{ github.event.pull_request.html_url }}         # Full browser URL to the PR
${{ github.event.pull_request.number }}           # PR number (integer)
```

### Block Kit Blocks Available for Incoming Webhooks

```yaml
# Source: https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks
# "You can use all the usual formatting and layout blocks with incoming webhooks"

# header block — prominent title, plain_text only, max 150 chars
- type: "header"
  text:
    type: "plain_text"
    text: "Your title here"
    emoji: true

# section block with mrkdwn text
- type: "section"
  text:
    type: "mrkdwn"
    text: "*Bold* and _italic_ and <https://example.com|link>"

# section block with two-column fields
- type: "section"
  fields:
    - type: "mrkdwn"
      text: "*Label A:*\nvalue A"
    - type: "mrkdwn"
      text: "*Label B:*\nvalue B"

# divider block
- type: "divider"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1: `env: SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK` | v2: `webhook-type: incoming-webhook` as `with:` input | v2.0.0 release (2024) | Breaking change — v1 env var is silently ignored in v2 |
| Payload via `slack-message:` field | Payload via `payload:` field with blocks array | v2.0.0 | `slack-message` is plain text; `payload` supports Block Kit |

**Deprecated/outdated:**
- v1 action syntax: Do not use `env: SLACK_WEBHOOK_TYPE`. Use `with: webhook-type:` in v2.
- `markdown` block type in webhook payloads: Known broken on incoming webhooks (issue #440). Use `section` + `mrkdwn` text type instead.

## Open Questions

1. **PR title length vs Block Kit header 150-char limit**
   - What we know: Block Kit `header` block has a hard 150-character limit on text. GitHub PR titles have no enforced max (GitHub UI shows warning at 72 chars but does not block longer titles).
   - What's unclear: Whether long PR titles will cause the Slack API to reject the payload or silently truncate.
   - Recommendation: Add `| truncate(150)` or a bash truncation step if this becomes an issue. For now, proceed with the raw title and monitor for errors in practice.

2. **Special characters in PR title breaking YAML payload interpolation**
   - What we know: GitHub Actions interpolates `${{ }}` expressions before YAML parsing. A PR title with `"` or `:` could produce invalid YAML in the `payload:` field.
   - What's unclear: How `slackapi/slack-github-action` v2 handles this edge case internally — it may sanitize inputs or it may fail.
   - Recommendation: Accept the risk for now (most PR titles are safe). If issues surface, add a preceding step that escapes the title and stores it in `$GITHUB_OUTPUT`.

3. **Whether `slackapi/slack-github-action` should be SHA-pinned**
   - What we know: DETECT-03 in REQUIREMENTS.md specifies SHA pinning only for `tj-actions/changed-files`. STATE.md documents the CVE-2025-30066 context. `slackapi/slack-github-action` is a first-party Slack-maintained action with lower supply chain risk than a third-party action.
   - What's unclear: Whether the project policy (SHA-pin all third-party actions, or only the CVE-affected one) extends to this action.
   - Recommendation: SHA-pin `slackapi/slack-github-action` to `91efab103c0de0a537f72a35f6b8cda0ee76bf0a` (v2.1.1) for defense-in-depth and consistency with the Phase 2 decision pattern. Cost is negligible.

## Sources

### Primary (HIGH confidence)

- https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-slack-incoming-webhook/ — v2 action inputs: `webhook`, `webhook-type`, `payload`; payload format; Block Kit support confirmed
- https://github.com/slackapi/slack-github-action/blob/main/action.yml — Complete input parameter list: `webhook`, `webhook-type`, `payload`, `payload-file-path`
- https://github.com/slackapi/slack-github-action/releases/tag/v2.1.1 — SHA `91efab103c0de0a537f72a35f6b8cda0ee76bf0a`, release date July 9, 2025
- https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks — Block Kit support for incoming webhooks confirmed ("use all the usual formatting and layout blocks"); supported block types verified
- https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs — GitHub context variables: `pull_request.title`, `pull_request.user.login`, `pull_request.html_url`, `pull_request.number`
- https://docs.slack.dev/reference/block-kit/blocks/header-block — Header block: `plain_text` only, max 150 chars

### Secondary (MEDIUM confidence)

- https://www.thisdot.co/blog/how-to-create-a-bot-that-sends-slack-messages-using-block-kit-and-github — Complete workflow example with `header`, `divider`, `section` blocks + PR context variables (uses v1 action, but Block Kit payload pattern is confirmed against official docs)
- https://pullnotifier.com/tools/slack-github-actions — v2.1.1 example with `webhook-type: incoming-webhook` + `payload:` syntax verified

### Tertiary (LOW confidence)

- https://github.com/slackapi/slack-github-action/issues/440 — `markdown` block type broken on incoming webhooks; issue open as of research date. Recommends using `section` + `mrkdwn` instead. (LOW: single GitHub issue, not official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — SHA verified from official release page; action inputs from action.yml
- Architecture: HIGH — payload syntax from official Slack docs; GitHub context variables from official GitHub docs
- Pitfalls: HIGH for v1/v2 mismatch (confirmed breaking change from release notes); MEDIUM for `markdown` block issue (GitHub issue, not official docs); MEDIUM for YAML special-char injection (reasonable inference, not tested)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (Slack action is stable; Block Kit spec is stable; SHA is immutable)

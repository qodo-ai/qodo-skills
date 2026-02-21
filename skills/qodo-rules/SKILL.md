---
name: qodo-rules
description: "Manage Qodo coding rules — get, sync, create, update, delete. Use only when user explicitly asks to view, add, edit, or remove rules."
---

# Qodo Rules

CRUD operations for Qodo coding rules.

**Script:** `bash .claude/skills/qodo-rules/scripts/qodo-rules.sh`

**Prerequisites:** `curl`, `jq`, `git` — and authenticated via `/qodo-setup`

---

## Get

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --get
```

Downloads all active rules and saves them as local IDE rule files:

- **Cursor:** `.cursor/rules/qodo-<slug>.mdc` (with frontmatter: `description`, `alwaysApply: true`)
- **Claude Code:** `.claude/rules/qodo-<slug>.md` (plain markdown)

**Location:** saves to the project root if inside a git repo, otherwise falls back to `~/` (user home). Auto-detects the IDE from the workspace (`.cursor/` directory or `CURSOR_TRACE_ID` env var).

All synced files are prefixed with `qodo-` so re-runs clean up old synced rules without affecting manually created ones.

Each rule file includes: name, severity, category, content, and examples (if available).

| Severity | Action |
|----------|--------|
| **ERROR** | Must comply. Ask user if can't satisfy. |
| **WARNING** | Should comply. Explain briefly if skipping. |
| **RECOMMENDATION** | Consider when appropriate. |

---

## Create

**Always use the two-step flow: preview via `--prompt`, then pipe directly into `--create`.**

### Step 1: Preview rule from prompt

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --prompt "Describe the rule in plain English"
```

Calls the server-side LLM to generate a complete rule JSON (name, category, content, examples, severity). Returns the generated `RuleBase` JSON. **Never manually construct rule JSON** — always use `--prompt` to avoid escaping issues.

After getting the JSON, show it to the user in this format:

```
---
**Name:** <name>
**Category:** <category>
**Severity:** <severity>

**Rule:**
<content>

**Good example:**
<goodExamples>

**Bad example:**
<badExamples>

Create this rule?
```

Wait for user confirmation before proceeding to Step 2.

### Step 2: Create (after user approval)

Re-run `--prompt` and pipe its output directly into `--create`. **Never use `echo '<json>'`** — multi-line JSON fields break shell quoting.

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --prompt "Describe the rule in plain English" \
  | bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --create
```

With optional scope override:

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --prompt "Describe the rule in plain English" \
  | bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --create --scope "/org/repo/src/"
```

Scope is auto-added from git remote. Returns `{"ruleId": <id>}`. Rule is created as a suggestion needing admin approval. HTTP 409 = name already exists.

---

## Update

Requires the full rule JSON (admin only).

```bash
echo '<full-rule-json>' | bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --update <rule_id>
```

HTTP 403 = not an admin.

---

## Delete

**Always confirm with user before deleting.**

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --delete <rule_id>
```

HTTP 204 = success. HTTP 403 = not an admin.

---

## Auth

Reads `id_token` and `platform_url` from `~/.qodo/skill_auth.json` (written by `/qodo-setup`).

**Trigger: On any authentication failure, automatically run qodo-setup and retry.**

When the script fails with **any** of these signals:
- Output contains `Not authenticated` or `Token expired`
- HTTP 401 error in the output
- Exit code 1 with auth-related error message

**You MUST automatically recover — never tell the user to authenticate manually:**

1. First try a silent refresh: `bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --check`
2. If `--check` succeeds (exit 0), retry the original qodo-rules command immediately
3. If `--check` fails, run `bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --login` — do NOT ask the user, just run it
4. After login completes, retry the original qodo-rules command


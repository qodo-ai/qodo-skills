# Skill Support Declaration

Every skill in this repository must include a `support.yml` file declaring which coding agents, operating systems, and git providers it has been tested against. This file drives CI validation and feeds future analytics.

---

## Why This Exists

Skills run on different agents (Claude Code, Cursor, Windsurf), different OSes (macOS, Ubuntu, Windows), and may depend on provider-specific CLIs (`gh`, `glab`, etc.). Without explicit declarations:

- There is no way to know which combinations are actually supported
- CI cannot enforce quality on new contributions
- Users cannot discover compatibility at a glance

The `support.yml` file makes these declarations explicit, machine-readable, and enforced on every PR.

---

## Quick Start

Add a `support.yml` to your skill directory:

```yaml
schema_version: "1"
skill: qodo-my-skill

agents:
  - claude-code
  - cursor

os:
  - ubuntu
  - macos
  - windows

git_providers: []   # omit or leave empty if no provider CLI dependency

tests: []           # optional custom test commands (see below)
```

That's it. CI will pick it up automatically.

---

## File Location

```
skills/
  qodo-my-skill/
    SKILL.md          # required: skill instructions
    support.yml       # required: this file
    references/       # optional: progressive disclosure docs
    scripts/          # optional: helper scripts
```

---

## Schema Reference

### `schema_version` (required)

Always `"1"` for the current format. Will increment if the schema changes in a backwards-incompatible way.

```yaml
schema_version: "1"
```

### `skill` (required)

Must exactly match the directory name.

```yaml
skill: qodo-get-rules
```

### `agents` (required)

List of coding agents this skill has been tested with and is declared to support. Must not be empty.

```yaml
agents:
  - claude-code
  - cursor
  - windsurf
  - cline
```

**Known values:**

| Value | Agent |
|-------|-------|
| `claude-code` | Anthropic Claude Code |
| `cursor` | Cursor IDE |
| `windsurf` | Windsurf (Codeium) |
| `cline` | Cline (VS Code extension) |
| `copilot` | GitHub Copilot |
| `codex` | OpenAI Codex |

### `os` (required)

List of operating systems this skill has been tested on and is declared to support. Must not be empty.

```yaml
os:
  - ubuntu
  - macos
  - windows
```

**Known values:**

| Value | Meaning | CI Runner |
|-------|---------|-----------|
| `ubuntu` | Ubuntu/Debian Linux | `ubuntu-latest` |
| `macos` | macOS | `macos-latest` |
| `windows` | Windows | `windows-latest` |

### `git_providers` (optional)

List of git providers this skill explicitly depends on. Only declare a provider if the skill invokes provider-specific CLI tools (`gh`, `glab`, `bb`, `az devops`).

Skills that only read the git remote URL (e.g. for scope detection) do **not** need a git provider declaration.

```yaml
# Skill with no provider CLI dependency:
git_providers: []

# Skill that uses gh and glab:
git_providers:
  - github
  - gitlab
```

**Known values:**

| Value | Provider | CLI Tool |
|-------|----------|----------|
| `github` | GitHub | `gh` |
| `gitlab` | GitLab | `glab` |
| `bitbucket` | Bitbucket | `bb` |
| `azure-devops` | Azure DevOps | `az devops` |

### `tests` (optional)

Custom test commands to run after structural checks. Commands run from the skill root directory. Leave empty if structural checks are sufficient.

```yaml
tests:
  - python3 scripts/validate-something.py
```

> **Note:** Custom test execution is planned for a future version. For now, the field is validated for correct YAML structure but commands are not executed in CI. Structural checks (see below) always run.

---

## What CI Validates

On every PR that touches `skills/**`, the [skill-pr-validation workflow](.github/workflows/skill-pr-validation.yml):

1. Detects which skills were changed
2. Reads each skill's `support.yml` to determine the OS matrix
3. Runs `validate-skill.py` on each (skill, OS) combination

**Structural checks run on every skill:**

| Check | Description |
|-------|-------------|
| `support.yml` exists | File must be present |
| Schema valid | Required fields present and correct |
| Skill name matches directory | `skill:` field = directory name |
| `agents` vocabulary | Only known agent values |
| `os` vocabulary | Only known OS values |
| `git_providers` vocabulary | Only known provider values (if declared) |
| `SKILL.md` exists | Required for every skill |
| Frontmatter valid | YAML between `---` delimiters, with `name` and `description` |
| `SKILL.md` name matches directory | Frontmatter `name:` = directory name |
| File size limits | All `.md` files ≤ 500 lines |
| Relative links resolve | All `[text](path)` links in `SKILL.md` point to existing files |
| Python script syntax | All `scripts/*.py` files compile without errors |

A PR cannot merge if any check fails on any declared OS.

---

## On-Demand Testing

To test a skill outside of a PR (maintenance, debugging, or before opening a PR):

**GitHub Actions UI:**
> Actions → Test Skill On-Demand → Run workflow → enter skill name

**GitHub CLI:**
```bash
gh workflow run skill-test-on-demand.yml -f skill=qodo-get-rules
gh workflow run skill-test-on-demand.yml -f skill=qodo-get-rules -f os=ubuntu
```

**Locally:**
```bash
python3 .github/scripts/validate-skill.py skills/qodo-get-rules
```

---

## Adding a New Skill

1. Create `skills/qodo-my-skill/`
2. Add `SKILL.md` with valid YAML frontmatter (`name`, `description`)
3. Add `support.yml` using the template above
4. Run local validation: `python3 .github/scripts/validate-skill.py skills/qodo-my-skill`
5. Open a PR — CI will validate on each declared OS

---

## Reference Implementation

[`skills/qodo-get-rules/support.yml`](skills/qodo-get-rules/support.yml) is the canonical example. It declares support for all four coding agents, all three OSes, and no git provider dependency.

---

## Design Rationale

**Why `support.yml` instead of extending `SKILL.md` frontmatter?**

Adding support metadata to `SKILL.md` frontmatter would mix agent-execution instructions with CI metadata. A separate file keeps concerns isolated: `SKILL.md` is for agents to read and execute; `support.yml` is for CI and tooling to parse. It also allows validators to parse the declaration without needing to understand Markdown structure.

**Why a controlled vocabulary instead of free-form strings?**

Controlled vocabularies (known agent names, OS names, provider names) make the data usable for future analytics — tracking which agents a skill supports, which OS has the most coverage gaps, etc. Free-form strings would make aggregation error-prone. New values can be added to the vocabulary in `validate-skill.py` and this document.

**Why structural validation rather than runtime testing?**

Skills are AI agent instructions, not executable code. Their "runtime" is an LLM interpreting Markdown. Structural checks (file integrity, schema validity, link resolution, script syntax) are what can be mechanically verified in CI. Runtime behavior is verified manually by the skill author against the test matrix declared in `support.yml`. The declaration serves as an attestation.

**Why an OS matrix in CI?**

Even though skills are Markdown documents, helper scripts in `scripts/` can have OS-specific issues (path separators, command availability, Python invocation). Running structural validation on all declared OS runners catches these before they reach users.

**Why `fail-fast: false` in the matrix strategy?**

So all combinations run on every PR and all failures are visible at once, rather than stopping after the first failure. This makes it faster to fix all issues in a single iteration.

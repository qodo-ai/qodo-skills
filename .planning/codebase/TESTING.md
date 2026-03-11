# Testing Patterns

**Analysis Date:** 2026-03-01

## Overview

This is a **skill collection** for AI coding agents. Testing focuses on:
1. **Skill functionality**: Each skill invokes correctly and produces expected output
2. **Cross-platform compatibility**: macOS, Linux (Ubuntu/Debian), Windows
3. **Coding agent compatibility**: Claude Code, Cursor, Windsurf, Cline
4. **Git provider compatibility**: GitHub, GitLab, Bitbucket, Azure DevOps (when relevant)

There is **no formal test framework** (no pytest, Jest, Vitest). Testing is **manual and procedural**, documented in `AGENTS.md` and `CONTRIBUTING.md`.

## Test Matrix

All skills must be tested across three dimensions:

### 1. Operating Systems (P0)

| OS | Requirement | Verification |
|----|-------------|--------------|
| macOS | Required | Test with zsh/bash and `python3` |
| Linux (Ubuntu/Debian) | Required | Test with bash and `python3` |
| Windows 10+ | Required | Test with cmd and `py -3` |

**Platform-specific concerns:**
- Path separators: Bash handles `/` and `\` correctly
- Path spaces: All wrappers quote paths: `"$path_with_spaces"`
- Line endings: Scripts use platform-native line endings

### 2. Coding Agents (P0)

| Agent | Requirement | Installation | Invocation |
|-------|-------------|--------------|-----------|
| Claude Code | P0 | `npx skills add` → ~/.claude/skills/ | `/skill-name` |
| Cursor | P1 | `npx skills add` → ~/.cursor/skills/ | Command palette |
| Windsurf/Cline | P1 | `npx skills add` → ~/.windsurf/skills/ | Skill menu |

**Test procedure:**
1. Install skill locally: `npx skills add /path/to/skill`
2. Invoke manually (Claude Code): `/qodo-get-rules`
3. Test auto-invoke via triggers (if defined)
4. Verify output appears in chat
5. Test error scenarios

### 3. Git Providers (P0 for provider-dependent skills)

Skills like `qodo-pr-resolver` interact with specific git providers:

| Provider | CLI Tool | Requirement | Verification |
|----------|----------|-------------|--------------|
| GitHub | `gh` | P0 | Test with `gh` CLI installed |
| GitLab | `glab` | P0 | Test with `glab` CLI installed |
| Bitbucket | `bb` | P0 | Test with `bb` CLI installed |
| Azure DevOps | `az` | P0 | Test with `az` CLI + DevOps extension |

**Test procedure:**
- Create a test PR/MR on each provider
- Post a Qodo review comment
- Run skill and verify it finds the PR and parses comments correctly

## Test Scenarios by Skill

### qodo-get-rules

**Checklist before shipping:**

Core functionality:
- [ ] Rules load without errors
- [ ] Output includes "📋 Qodo Rules Loaded" header
- [ ] Rules grouped by severity (ERROR, WARNING, RECOMMENDATION)
- [ ] Pagination works (>50 rules tested)
- [ ] Rules formatted correctly: `- **{name}** ({category}): {description}`

Configuration:
- [ ] API key from config file works
- [ ] Environment variable `QODO_API_KEY` overrides config
- [ ] Missing API key → helpful error message
- [ ] Missing config file → helpful error message

Git repository:
- [ ] Works in git repo with remote
- [ ] Not in git repo → exits gracefully
- [ ] No remote URL → exits gracefully
- [ ] Module-level scope detection works (in `modules/` directory)

Error handling:
- [ ] HTTP 401 (auth error) → helpful message
- [ ] HTTP 403 (forbidden) → helpful message
- [ ] HTTP 404 (endpoint not found) → helpful message
- [ ] HTTP 5xx (server error) → helpful message with retry guidance
- [ ] Network timeout → helpful message

Edge cases:
- [ ] No rules found → outputs "No rules found" message
- [ ] Large rule sets (100+ rules) → pagination handles correctly
- [ ] Special characters in rules → formatting preserves correctly
- [ ] Empty repository scope → handled gracefully

Platform-specific:
- [ ] Works on macOS with `python3`
- [ ] Works on Linux with `python3`
- [ ] Works on Windows with `py -3`
- [ ] Path separators handled correctly (Windows `\` vs Unix `/`)

Agent-specific:
- [ ] Trigger patterns work in Claude Code
- [ ] Skill invokes with `/qodo-get-rules`
- [ ] Output displays correctly in chat
- [ ] Completes within 30 seconds

### qodo-get-relevant-rules

**Checklist before shipping:**

Core functionality:
- [ ] Query generation creates both topic + cross-cutting queries
- [ ] Query format matches Name/Category/Content structure
- [ ] Search endpoint called with `top_k=20`
- [ ] Results deduplicated and ranked correctly
- [ ] Output includes "📋 Qodo Rules Loaded" header
- [ ] Rules formatted: `- **{name}** [{severity}]: {content}`

Query generation:
- [ ] Topic query focuses on assignment's primary concern
- [ ] Cross-cutting query targets architecture/quality patterns
- [ ] Category from list: Security, Correctness, Quality, Reliability, Performance, etc.
- [ ] Queries use structured format, not keyword lists
- [ ] Queries describe specific checks, not generic tasks

Configuration:
- [ ] API key from config file works
- [ ] Environment variable takes precedence
- [ ] Missing API key → helpful error
- [ ] Environment name defaults to production if empty

Error handling:
- [ ] HTTP 401/403/404/5xx → helpful messages
- [ ] Empty results (no rules) → "No relevant rules found" message, does not crash
- [ ] Ambiguous assignment → falls back to verbatim assignment as query
- [ ] Query parsing error → handled gracefully

Platform-specific:
- [ ] Works on macOS, Linux, Windows
- [ ] Query encoding handles special characters
- [ ] URLs constructed correctly for environment name

Agent-specific:
- [ ] Trigger patterns: `get.?relevant.?rules`, `relevant.?rules`, etc.
- [ ] Works with parallel tool execution (Claude Code)
- [ ] Output displays in chat with proper formatting

### qodo-pr-resolver

**Checklist before shipping:**

Core functionality:
- [ ] Detects git provider from remote URL
- [ ] Finds open PR/MR for current branch
- [ ] Fetches Qodo review comments
- [ ] Deduplicates issues across summary and inline comments
- [ ] Displays issues in correct severity order
- [ ] User can choose "Review each" or "Auto-fix all"

Git workflow:
- [ ] Detects uncommitted changes
- [ ] Detects unpushed commits
- [ ] Prompts user to push before review
- [ ] Exits gracefully if review in progress (still analyzing)

Issue parsing:
- [ ] Extracts issue title verbatim (no paraphrasing)
- [ ] Parses location (file path, line number)
- [ ] Extracts severity correctly from action level + position
- [ ] Preserves original issue ordering
- [ ] Captures agent prompt for fixes

Severity mapping:
- [ ] "Action required" issues split into CRITICAL/HIGH
- [ ] "Review recommended" issues split into MEDIUM/LOW
- [ ] "Other" issues always LOW
- [ ] Position within group determines split
- [ ] Example: 7 issues in "Action required" → first 3 CRITICAL, last 4 HIGH

Manual review mode (Step 6):
- [ ] User can review each issue individually
- [ ] User can choose Fix or Defer for each
- [ ] Fix applies Qodo's agent prompt
- [ ] Defer logs decision
- [ ] Commits changes per-issue or in batch

Auto-fix mode (Step 7):
- [ ] All "Fix" issues applied without prompting
- [ ] Uses Qodo's exact agent prompt
- [ ] Single commit with all fixes
- [ ] Summary shows what was fixed

PR commenting (Step 8):
- [ ] Reply to inline comments with decision
- [ ] Summary comment on PR with results
- [ ] Lists fixed issues and deferred issues

Provider detection:
- [ ] GitHub (github.com) → uses `gh` CLI
- [ ] GitLab (gitlab.com) → uses `glab` CLI
- [ ] Bitbucket (bitbucket.org) → uses `bb` CLI
- [ ] Azure DevOps (dev.azure.com) → uses `az` CLI
- [ ] Self-hosted instances → pattern matching works

Platform-specific:
- [ ] Path handling on Windows
- [ ] Git command detection
- [ ] CLI tool invocation

Agent-specific:
- [ ] Trigger patterns work
- [ ] Parses user responses (Review/Auto-fix/Cancel)
- [ ] Respects approval gates (Step 5 user choice)

## Manual Testing Procedure

### 1. Setup

```bash
# Clone repository
git clone https://github.com/qodo-ai/qodo-skills.git
cd qodo-skills

# Install skill locally
npx skills add /path/to/qodo-skills/skills/qodo-get-rules

# Verify installation
npx skills list | grep qodo
```

### 2. Invoke Skill

**Claude Code:**
```
/qodo-get-rules
```

**Cursor/Windsurf/Cline:**
- Open command palette
- Search for "qodo-get-rules"
- Select and invoke

### 3. Verify Output

Check that output:
- Appears in chat without errors
- Contains "📋 Qodo Rules Loaded" header
- Shows rules grouped by severity
- Ends with `---` separator
- No stack traces or exception messages

### 4. Test Triggers (if applicable)

For skills with defined triggers, test natural language invocation:

```
get rules
load qodo rules
fetch coding rules
```

Each should trigger the skill without using the `/skill-name` syntax.

### 5. Test Error Scenarios

**Missing API key:**
```bash
unset QODO_API_KEY
rm ~/.qodo/config.json
/qodo-get-rules
# Verify: helpful error message, not a crash
```

**Not in git repo:**
```bash
cd /tmp
/qodo-get-rules
# Verify: "git repository required" message
```

**Network issue:**
- Disconnect internet or mock `curl` failure
- Verify: graceful error message with retry guidance

### 6. Test Cross-Platform (if possible)

**macOS:**
```bash
which python3          # Verify Python available
./scripts/helper.sh    # Test shell wrapper
```

**Linux (Docker):**
```bash
docker run -it ubuntu:22.04 bash
# Install curl, git, python3
# Run skill
```

**Windows (WSL or PowerShell):**
```powershell
python --version       # or py -3 --version
.\scripts\helper.cmd   # Test batch wrapper
```

## Helper Script Testing

### Test Format

Helper scripts should be testable independently:

```bash
# Test script syntax
python3 -m py_compile scripts/fetch-qodo-rules.py

# Run script directly
python3 scripts/fetch-qodo-rules.py

# Test shell wrapper
./scripts/fetch-qodo-rules.sh

# Test Windows wrapper
.\scripts\fetch-qodo-rules.cmd
```

### Exit Code Expectations

- `0` - Success
- `1` - Error (generic)
- `2` - Configuration error
- `22` - HTTP error
- `other` - Specific error (document in script)

### Test Cases for Scripts

```bash
# Happy path
python3 scripts/fetch-qodo-rules.py
# Expected: Rules output to stdout, exit code 0

# Missing API key
unset QODO_API_KEY
python3 scripts/fetch-qodo-rules.py
# Expected: "API key required" message, exit code 2

# Network error
# (Mock curl to fail)
python3 scripts/fetch-qodo-rules.py
# Expected: "Network error" message, exit code 22

# Help/version
python3 scripts/fetch-qodo-rules.py --help
# Expected: Usage message, exit code 0
```

## Continuous Testing (Future)

Currently, skills are tested **manually before submission**. Future improvements:

- [ ] GitHub Actions workflow for syntax validation
- [ ] `shellcheck` for bash scripts
- [ ] `pylint` or `pycodestyle` for Python scripts
- [ ] Markdown linting for documentation
- [ ] Integration tests with mock git provider APIs
- [ ] Pre-commit hooks to validate SKILL.md format

## Test Documentation

### Where Tests Are Documented

1. **AGENTS.md** (root)
   - `## Testing Requirements` section
   - Test matrix across OS, agents, providers
   - Cross-platform verification checklist
   - Git provider verification checklist

2. **CONTRIBUTING.md**
   - `## Testing Your Skill` section
   - Local testing instructions
   - Test checklist
   - Cross-compatibility checklist

3. **SKILL-specific AGENTS.md** (if applicable)
   - Skill-specific test scenarios
   - Example testing commands
   - Expected behaviors

### Example Test Scenarios

**qodo-get-rules (from AGENTS.md):**
```bash
# Test Python syntax
python3 -m py_compile scripts/fetch-qodo-rules.py

# Test script functionality
python3 scripts/fetch-qodo-rules.py

# Install skill locally
npx skills add /path/to/qodo-skills/skills/qodo-get-rules

# Test in agent
/qodo-get-rules
```

**qodo-get-relevant-rules (from skill-specific AGENTS.md):**
```bash
# Test scenarios:
# 1. Happy path - assignment generates query, rules returned
# 2. Empty results - endpoint returns {}, skill outputs "No relevant rules"
# 3. No API key - helpful error message
# 4. Not in git repo - helpful error message
# 5. HTTP error - appropriate error message
# 6. Short/ambiguous assignment - falls back to verbatim query
```

## Known Testing Limitations

1. **No automated test runner** - Tests are procedural, not automated
2. **Provider testing requires real accounts** - Can't mock all git providers fully
3. **Agent testing requires manual invocation** - Can't fully automate agent behavior
4. **Network testing** - Must have real API access or mock server
5. **Timing** - Some tests depend on external service latency

## Testing Best Practices

### Do's ✅

- **Test on all three platforms** - macOS, Linux, Windows
- **Test with multiple agents** - At least Claude Code and one other
- **Test error paths** - Not just happy path
- **Document test results** - PR should show testing was done
- **Test in isolation** - Script works without manual steps

### Don'ts ❌

- **Skip platform testing** - "It works on my Mac" isn't enough
- **Test only happy path** - Edge cases and errors matter most
- **Skip error messages** - Verify error messages are helpful
- **Assume dependencies** - Check prerequisites are actually installed
- **Ignore timeouts** - Test with slow networks

---

*Testing analysis: 2026-03-01*

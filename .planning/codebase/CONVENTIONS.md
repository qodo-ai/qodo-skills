# Coding Conventions

**Analysis Date:** 2026-03-01

## Overview

This is a **skill collection** codebase for AI coding agents. Code is primarily documentation (SKILL.md files with YAML frontmatter and markdown instructions) and supporting reference documents. There are no traditional source code files (Python, TypeScript, etc.) in the main repository.

## YAML Frontmatter Format

All SKILL.md files must include YAML frontmatter at the top:

```yaml
---
name: qodo-skill-name
description: "Brief 1-2 sentence description for skill discovery"
allowed-tools: ["Bash", "Read", "Write"]
triggers:
  - "trigger.pattern1"
  - "trigger.pattern2"
---
```

**Naming Patterns:**
- **name field**: Must use `qodo-*` prefix (lowercase, hyphens only)
  - Examples: `qodo-get-rules`, `qodo-pr-resolver`, `qodo-get-relevant-rules`
  - Never: `get-rules`, `my-skill`, `qodo_get_rules`

- **description field**: Exactly 1-2 sentences for discovery
  - Be concise and focused
  - Explain when/why to use the skill
  - Example: "Fetches repository-specific coding rules from Qodo before code generation or modification tasks."

- **allowed-tools array**: List tool names the skill requires
  - Common: `["Bash"]`, `["Bash", "Read", "Write"]`
  - Restrict to actual needs for security
  - See `AGENTS.md` for full list

- **triggers array**: Regex-like patterns for auto-invocation
  - Use `?` for optional characters: `qodo.?fix` matches "qodo-fix", "qodo fix", "qodofix"
  - Include 2-3 common variations of skill name
  - Use synonyms where applicable (get/fetch, fix/repair)

## Markdown Formatting

### File Structure

Every SKILL.md follows this structure:

```markdown
---
[YAML frontmatter]
---

# Skill Name

## Description
[1-2 paragraph overview]

## [Section Name]
[Content]

## Common Mistakes
[List of common errors and how to avoid them]
```

**Sections typically include:**
- `Description` - What the skill does
- `Workflow` - Step-by-step instructions (numbered with ### headers)
- `Prerequisites` - Required tools, configs, permissions
- `Instructions` - Main workflow (most detailed)
- `Configuration` - Setup instructions
- `Common Mistakes` - List of errors and solutions
- `Examples` - Usage scenarios (optional)

### Heading Levels

- `# Skill Name` - Main title (top level)
- `## Section` - Major sections (Description, Workflow, Configuration)
- `### Step 1: Description` - Steps within workflow
- `#### Scenario A:` - Sub-cases within steps
- No deeper nesting than ####

### Code Blocks

All code blocks must include syntax highlighting:

```markdown
\`\`\`bash
git status --porcelain
\`\`\`

\`\`\`python
import uuid
print(uuid.uuid4())
\`\`\`

\`\`\`json
{"API_KEY": "sk-xxx", "ENVIRONMENT_NAME": "staging"}
\`\`\`
```

### Lists

**Ordered lists for steps:**
```markdown
1. First action
2. Second action
3. Third action
```

**Unordered lists for options:**
```markdown
- Option A
- Option B
  - Sub-option B1
  - Sub-option B2
```

**Inline emphasis:**
- Bold for UI elements, commands, file names: `**git commit**`, `**~/.qodo/config.json**`
- Backticks for code/commands: `` `git status` ``
- Italics for file paths: `_path/to/file_`

### Tables

Use markdown tables for structured data:

```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
```

Tables appear in:
- Severity/enforcement mappings: `SKILL.md` files
- Header definitions: Reference documents
- Provider comparison: `resources/providers.md`

## Naming Conventions

### File Names

**SKILL.md files:**
- Always `SKILL.md` (uppercase)
- One per skill directory
- Located in `skills/qodo-*/SKILL.md`

**Reference documents:**
- Lowercase with hyphens: `query-generation.md`, `search-endpoint.md`
- Placed in `references/` subdirectory
- One file per atomic concept

**Agent/Claude context files:**
- `AGENTS.md` (universal guidelines)
- `CLAUDE.md` (Claude Code-specific directives)
- Hierarchical: root files + skill-specific subdirectory versions

**Resource documents:**
- Descriptive lowercase: `providers.md`, `output-format.md`
- Placed in `resources/` or `references/` subdirectories

### Directory Names

**Skill directories:**
- Lowercase with hyphens: `qodo-get-rules`, `qodo-pr-resolver`
- Must start with `qodo-` prefix

**Subdirectories within skills:**
- `references/` - Detailed technical references
- `resources/` - Configuration, provider guides
- `scripts/` - Helper scripts (Python, Bash, Windows batch)
- `tests/` - Test scripts (optional)

## Comment Patterns

### When to Comment

Comments appear in:

1. **Shell scripts** - Describe purpose and usage
   ```bash
   #!/bin/bash
   # Description: Fetch rules from Qodo API
   # Usage: ./fetch-qodo-rules.sh [--test]
   ```

2. **Complex decision points** - Explain why, not what
   ```bash
   # Split point: roughly first half of each group gets the higher severity
   # This maps Qodo's position ordering to severity levels
   ```

3. **Error handling** - Clarify recovery strategy
   ```bash
   # If no rules found, exit gracefully - empty result is valid
   ```

### When NOT to Comment

- Obvious code: `git status` is self-explanatory
- API request examples: The header explanation is sufficient
- YAML frontmatter: Field names are self-documenting

## Instructions Writing Style

### Do's ✅

- **Be specific**: Provide exact commands and code snippets
  ```markdown
  Run: `git status --porcelain`
  ```
  Not: "Check git status"

- **Use examples**: Show concrete inputs/outputs
  ```markdown
  Example: "7 Action required issues" → split as Issues 1-3: CRITICAL, Issues 4-7: HIGH
  ```

- **Handle errors**: Include edge cases explicitly
  ```markdown
  If output is empty, skip to Step 3. Otherwise, proceed to Step 2.
  ```

- **Be step-by-step**: Break complex workflows into numbered steps
  ```markdown
  ### Step 1: Verify Git Repository
  ### Step 2: Check Configuration
  ### Step 3: Execute Query
  ```

- **Use markdown formatting**: Bold, lists, code blocks for scannability
- **Test thoroughly**: Verify in different scenarios before documenting

### Don'ts ❌

- **Be vague**: Avoid generic instructions like "do the right thing"
- **Assume context**: Don't assume knowledge of Qodo, Git, or domain
- **Skip error handling**: Always include graceful error messages
- **Over-complicate**: Keep it as simple as possible
- **Forget edge cases**: Anticipate what could fail

## Severity and Enforcement

### Error Handling and Severity Levels

Across SKILL.md files, severity is communicated consistently:

- **🔴 CRITICAL** - Must fix immediately; security or data risk
- **🟠 HIGH** - Should fix; correctness or reliability impact
- **🟡 MEDIUM** - Consider fixing; quality or performance impact
- **⚪ LOW** - Optional; suggestion or best practice

**Enforcement in code generation:**
- **ERROR rules**: Must comply non-negotiably; add comment documenting compliance
- **WARNING rules**: Should comply by default; briefly explain if skipped
- **RECOMMENDATION rules**: Consider when appropriate; no action required if not applicable

### Environment Variables vs Config Files

Conventions for configuration:

- **Config file**: `~/.qodo/config.json` (default location)
  ```json
  {"API_KEY": "sk-xxx", "ENVIRONMENT_NAME": "staging"}
  ```

- **Environment variable** (takes precedence): `QODO_API_KEY`, `QODO_ENVIRONMENT_NAME`
  ```bash
  export QODO_API_KEY="sk-xxx"
  ```

- **Pattern**: Check environment variable first, fall back to config file

## API Request Patterns

### Header Requirements

All HTTP requests to Qodo endpoints must include:

```bash
curl -s \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "request-id: ${REQUEST_ID}" \
  -H "qodo-client-type: skill-qodo-get-rules" \
  "${API_URL}/endpoint"
```

See `skills/qodo-get-rules/references/attribution.md` for full header specifications.

### Request ID Pattern

- Generate once per skill invocation: `uuid.uuid4()` or `uuidgen`
- Reuse on every paginated request (correlates all pages)
- Format: Standard UUID string

## File Size Discipline (CRITICAL)

**Maximum: 500 lines per file. Ideal: ~300 lines.**

**Why this matters:**
- Claude's instruction-following capacity is ~150-200 instructions
- Large files overwhelm context and reduce agent compliance
- Smaller files ensure better agent performance

**When to split:**
- Any file approaching 400 lines → stop and refactor
- Create hierarchical AGENTS.md/CLAUDE.md in subdirectories
- Extract logical sections into separate reference documents
- Use progressive disclosure: reference detailed docs instead of inlining

**Examples:**
- `skills/qodo-get-rules/SKILL.md` (122 lines) - Just right
- `skills/qodo-pr-resolver/SKILL.md` (325 lines) - At limit, uses references heavily
- Reference documents: `query-generation.md` (105 lines), `search-endpoint.md` (123 lines)

## Git Commit Messages

**Format:**
```
Brief description (50 chars or less)

- Key change 1
- Key change 2
- Key change 3

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Branch naming:**
- `feature/skill-name` - New skills
- `fix/issue-description` - Bug fixes
- `docs/what-changed` - Documentation updates
- `improve/what-improved` - Enhancements to existing skills
- `polish/description` - Minor improvements and feedback application

**Guidelines:**
- Use heredoc syntax for multi-line messages: `git commit -m "$(cat <<'EOF'...EOF)"`
- Always include Co-Authored-By footer
- Stage specific files, never `git add .` or `git add -A`
- Never use `--no-verify` flag
- NEVER amend after pre-commit hook failure — create new commit

## Cross-Platform Compatibility

### Path Handling

- Use forward slashes in API URLs: Always `/` regardless of OS
- Python: Use `pathlib.Path` for operations; convert to `PurePosixPath` for URLs
- Bash: Quote paths with spaces: `"$file_path"`

### Script Wrappers

- Provide `.sh` (Unix/macOS/Linux) and `.cmd` (Windows) wrappers for helper scripts
- Unix wrapper: Uses `python3` and `/bin/bash`
- Windows wrapper: Uses `py -3` and `cmd.exe`
- Both wrap the same core logic (Python or Bash) with platform-specific invocation

### Tool Availability

- Check with `command -v` (Bash) or `shutil.which()` (Python)
- Provide helpful error messages if tool is missing
- Document minimum versions required

---

*Convention analysis: 2026-03-01*

# Qodo Skills - Claude Code Directives

> Claude Code-specific guidelines and directives for working on this plugin project.

**Important**: Read AGENTS.md first for universal guidelines. This file contains Claude Code-specific features and workflows.

## File Size Discipline (CRITICAL)

**Maximum file size: 500 lines. Ideal: ~300 lines.**

**Why this matters:**
- Claude's instruction-following capacity is ~150-200 instructions
- Large files overwhelm context and reduce instruction compliance
- Smaller files = better agent performance

**When any file approaches 400 lines:**

1. **Stop and refactor immediately**
2. **Create hierarchical structure**: Add AGENTS.md or CLAUDE.md in subdirectories
3. **Split by concern**: Extract logical sections into separate files
4. **Use progressive disclosure**: Reference detailed docs instead of inlining

**Example of hierarchical approach:**
```
skills/get-rules/
├── AGENTS.md              # Skill-specific agent guidelines (~150 lines)
├── CLAUDE.md              # Claude Code-specific notes (~100 lines)
└── SKILL.md               # Skill instructions (~250 lines)
```

**Check file sizes regularly:**
```bash
find . -name "*.md" -exec wc -l {} + | sort -rn | head -10
```

## Plugin Architecture

This is a **Claude Code plugin** with auto-invocation via hooks:

**Installation:**
- Plugin: `/plugin install github.com/qodo-ai/qodo-skills`
- Individual skills: `npx skills add qodo-ai/qodo-skills/get-rules`

**Auto-invocation:**
- `hooks/hooks.json` defines SessionStart hook
- Automatically runs `fetch-qodo-rules.py` at conversation start
- No user action required - rules load before coding begins

**Skill invocation:**
- `/get-rules` - Fetch and load coding rules
- `/pr-resolver` - Review and fix PR issues

## CRITICAL: get-rules Must Execute First

**NON-NEGOTIABLE RULE:**

**Before ANY code generation or modification task:**
1. Check conversation history for "📋 Qodo Rules Loaded"
2. If NOT found: Execute `/get-rules` immediately
3. Wait for rules to load
4. Then proceed with coding task

**Why this is critical:**
- Rules contain ERROR-level security and quality requirements
- Compliance is mandatory - code without rules violates organizational standards
- Auto-invocation may fail (API key missing, network issues)
- Manual check ensures rules are always loaded

**Implementation:**
```
[User asks to modify code]

Step 1: Check for "📋 Qodo Rules Loaded" in history
Step 2: If not found → /get-rules
Step 3: Wait for output
Step 4: Proceed with coding task applying loaded rules
```

## Skills Workflow

### get-rules Skill

**Purpose**: Fetch repository-specific coding rules from Qodo API

**Auto-invoked**: SessionStart hook (Claude Code plugin only)

**Manual invocation**: `/get-rules` (if auto-invocation failed)

**Output**: Formatted rules by severity
- **ERROR rules**: Must comply non-negotiably
- **WARNING rules**: Should comply preferentially
- **RECOMMENDATION rules**: Consider when appropriate

**Feedback**: Always inform user about rule application:
- ERROR rules applied: List which rules followed
- WARNING rules skipped: Explain why
- No applicable rules: Explicitly state this

### pr-resolver Skill

**Purpose**: Review code with Qodo and fix issues interactively

**Invocation**: `/pr-resolver` or trigger words ("qodo fix", "review qodo", "resolve pr", etc.)

**Workflow (Multi-step with approval gates):**

1. **Parse issues**: Extract from GitHub/GitLab/Bitbucket PR comments
2. **Present to user**: Show categorized issues with priorities
3. **Get selection**: Ask user which issues to fix (single question, not iterative)
4. **Apply fixes**: Use Qodo's agent prompt as PRIMARY guidance
5. **Post summary**: Comment on PR with fixed vs deferred issues

**Critical rules:**
- NEVER skip approval gates
- ALWAYS use Qodo's agent prompt for fix implementation
- ALWAYS post PR summary comment after completion
- Track fixed vs deferred issues with reasons

## Commit Conventions

**Always include Co-Authored-By:**
```bash
git commit -m "$(cat <<'EOF'
Brief description (50 chars)

- Key change 1
- Key change 2
- Key change 3

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Use heredoc for commit messages:**
- Ensures proper multi-line formatting
- Prevents shell escaping issues
- Maintains consistent structure

**Git safety protocol (from system prompt):**
- NEVER use `--no-verify` flag
- NEVER force push to main/master
- NEVER amend commits after pre-commit hook failure (create new commit)
- NEVER use `git add -A` or `git add .` (stage specific files)
- ALWAYS check `git status` before and after commits

## Tool Usage Preferences

**Prefer dedicated tools over Bash:**

| Task | Use This | NOT Bash |
|------|----------|----------|
| Read files | `Read` | `cat`, `head`, `tail` |
| Edit files | `Edit` | `sed`, `awk` |
| Search content | `Grep` | `grep`, `rg` |
| Find files | `Glob` | `find`, `ls` |
| Create files | `Write` | `echo >`, `cat <<EOF` |

**Why**: Dedicated tools are safer, provide better user visibility, and allow for permission controls.

**Bash is for**: Git operations, npm/pip commands, process management, system operations that truly need shell.

## Parallel vs Sequential Execution

**Parallel tool calls (single message with multiple calls):**
- When operations are **independent**
- Example: `git status` + `git diff` + `git log` (all read-only, no dependencies)

**Sequential execution (chained with `&&`):**
- When operations **depend on each other**
- Example: `git add . && git commit && git push` (each needs previous to succeed)
- Example: Write file → Bash to test file (test needs file to exist)

**Never use newlines to separate commands** (newlines OK in quoted strings only)

## Hierarchical AGENTS.md/CLAUDE.md Pattern

**Use hierarchical context files for skills:**

Example for get-rules skill:
```
skills/get-rules/
├── AGENTS.md         # Universal agent guidelines for this skill
│   - API key configuration
│   - Repository scope detection
│   - Module path handling
│   - Testing procedures
│
├── CLAUDE.md         # Claude Code-specific notes
│   - Auto-invocation via hooks
│   - Integration with SessionStart
│   - Tool usage patterns
│   - Commit conventions
│
└── SKILL.md          # Agent instructions (what to do)
    - Step-by-step workflow
    - Error handling
    - User feedback requirements
```

**Benefits:**
- Keeps root AGENTS.md/CLAUDE.md small (~200 lines each)
- Provides skill-specific context when working in that directory
- Agents automatically read nearest file in directory tree
- Progressive disclosure - agent gets relevant context only

## Creating Hierarchical Context Files

**When to create skill-specific AGENTS.md:**
- Skill has unique architecture or patterns
- Skill requires specific development setup
- Skill has domain-specific testing requirements
- Root AGENTS.md approaching 400 lines

**When to create skill-specific CLAUDE.md:**
- Skill uses Claude-specific features (hooks, tool patterns)
- Skill requires specific commit conventions
- Skill has unique workflow in Claude Code
- Root CLAUDE.md approaching 400 lines

**Template for skill-specific AGENTS.md:**
```markdown
# [Skill Name] - Agent Guidelines

> Skill-specific guidelines for working on [skill-name].

## Skill Architecture
[How this skill works]

## Development Setup
[Specific requirements]

## Testing
[How to test this skill]

## Common Patterns
[Patterns used in this skill]

---
See root AGENTS.md for universal guidelines.
```

## Trigger Usage in SKILL.md (HIGHLY ENCOURAGED)

**Always add triggers to SKILL.md YAML frontmatter:**

```yaml
---
name: get-rules
description: "Fetch coding rules from Qodo API"
triggers:
  - "get.?rules"
  - "load.?rules"
  - "fetch.?rules"
---
```

**Why this improves usability:**
- Users can invoke with natural language: "get rules", "load rules", "fetch rules"
- Reduces friction - no need to remember exact skill name
- Enables conversational invocation patterns
- Better agent discovery and auto-invocation

**Best practices:**
- Include 2-3 common variations of skill name
- Use `?` for optional characters (spaces, hyphens)
- Consider synonyms (get/fetch/load, fix/repair/resolve)
- Test patterns with different phrasings

## Resources

**For universal guidelines:** See AGENTS.md
**For contribution workflow:** See CONTRIBUTING.md
**For user documentation:** See README.md
**For skill instructions:** See skills/*/SKILL.md

## Claude Code-Specific Features

**Hooks:**
- `hooks/hooks.json` defines auto-invocation rules
- SessionStart, SessionEnd, ToolUse, etc.
- See Claude Code docs: https://code.claude.com/docs/en/hooks

**Plugin manifest:**
- `.claude-plugin/plugin.json` defines plugin metadata
- name, version, description, author, repository

**Settings:**
- `.claude/settings.local.json` for local development overrides
- Never commit to git (excluded via .gitignore if present)

---

**Note**: This file is Claude Code-specific. For universal agent guidelines, see AGENTS.md.
# Qodo Skills - Agent Guidelines

> Universal guidelines for AI coding agents working on the Qodo Skills plugin project.

## Project Overview

**Purpose**: Shift-left code review skills that bring Qodo's quality standards into local development workflow.

**Compatible Agents**: Claude Code, Cursor, Windsurf, Cline, and any agent supporting the [Agent Skills](https://agentskills.io) standard.

## Repository Structure

```
qodo-skills/
├── AGENTS.md                    # This file - universal guidelines
├── CLAUDE.md                    # Claude Code-specific directives
├── skills/                      # Agent Skills catalog
│   ├── get-qodo-rules/         # Fetch Qodo coding rules
│   │   ├── SKILL.md            # Skill specification
│   │   ├── AGENTS.md           # Skill-specific guidelines
│   │   └── scripts/            # Helper scripts
│   └── qodo-pr-resolver/       # Fix PR review issues
│       ├── SKILL.md
│       └── AGENTS.md
```

## Technology Stack

- **Python 3.6+**: Core scripting (standard library only, zero external dependencies)
- **Bash/Shell**: Cross-platform wrappers (`.sh` for Unix, `.cmd` for Windows)
- **Git**: Repository detection and remote URL parsing
- **Agent Skills Standard**: SKILL.md format for skill definitions

## File Size Guidelines (CRITICAL)

**Keep all files digestible to agents:**

- **Maximum**: 500 lines per file
- **Ideal**: ~300 lines per file
- **Reason**: Frontier LLMs handle ~150-200 instructions consistently; file size limits prevent context overload

**When files exceed limits:**

1. **Split by scope**: Create hierarchical AGENTS.md/CLAUDE.md in subdirectories
2. **Use progressive disclosure**: Point to detailed docs instead of including everything
3. **Refactor code**: Break large scripts into smaller modules
4. **Extract common patterns**: Move shared code to utilities

**Examples of hierarchical structure:**

```
project/
├── AGENTS.md                    # Root guidelines (~200 lines)
├── skills/
│   ├── get-qodo-rules/
│   │   ├── AGENTS.md           # Skill-specific context (~150 lines)
│   │   └── SKILL.md            # Skill instructions (~250 lines)
│   └── qodo-pr-resolver/
│       ├── AGENTS.md           # Skill-specific context (~150 lines)
│       └── SKILL.md            # Skill instructions (~400 lines)
```

## Skill Creation Guidelines

### SKILL.md Format

Every skill requires a SKILL.md file with YAML frontmatter:

```markdown
---
name: my-skill
description: "Brief description (1-2 sentences) for skill discovery"
version: 1.0.0
allowed-tools: ["Bash", "Read", "Edit", "Write"]
triggers:
  - "my.?skill"
  - "invoke.my.skill"
---

# Skill Name

## Description
[Detailed explanation]

## Prerequisites
[Required tools, config, permissions]

## Instructions
[Step-by-step workflow]

## Configuration
[How to configure]

## Error Handling
[Common issues and solutions]
```

### YAML Frontmatter Fields

**Required:**
- `name`: Unique identifier (lowercase, hyphens only)
- `description`: Brief description for discovery (1-2 sentences)

**Optional but STRONGLY RECOMMENDED:**
- `triggers`: Array of patterns for skill invocation (use regex-like patterns)
  - Example: `"qodo.?fix"` matches "qodo-fix", "qodo fix", "qodofix"
  - **Why**: Improves usability by allowing natural language invocation
  - **Best practice**: Include 2-3 common variations of skill name

- `allowed-tools`: Array of tool names (restrict for security)
  - Common: `["Bash", "Read", "Edit", "Write", "Grep", "Glob"]`
  - Advanced: `["WebFetch", "WebSearch", "Task"]`

- `version`: Semantic version (e.g., "1.0.0")

### Instruction Writing Standards

**Do:**
- ✅ Be specific: Exact commands and code snippets
- ✅ Use examples: Concrete inputs/outputs
- ✅ Handle errors: Include edge cases and error messages
- ✅ Be step-by-step: Break complex workflows into numbered steps
- ✅ Use markdown formatting: Headers, code blocks, lists
- ✅ Test thoroughly: Verify in different scenarios

**Don't:**
- ❌ Be vague: Avoid "do the right thing" instructions
- ❌ Assume context: Explain domain-specific concepts
- ❌ Skip error handling: Always include graceful fallbacks
- ❌ Over-complicate: Keep it as simple as possible
- ❌ Forget edge cases: Consider what could go wrong

### Helper Scripts

Place scripts in `scripts/` directory:

**Template:**
```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined var, pipe failure

# Description: What this script does
# Usage: ./helper.sh [args]

# Check prerequisites
if ! command -v required_tool &> /dev/null; then
    echo "Error: required_tool is not installed" >&2
    exit 1
fi

# Main logic
main() {
    # Your code here
    echo "Success message"
}

main "$@"
```

**Exit codes:**
- `0`: Success
- `1-255`: Error (use consistent codes)

## Cross-Platform Considerations

**Python scripts:**
- Use `pathlib.Path` for path operations (handles `/` vs `\`)
- Convert to `PurePosixPath` for URLs (always use `/`)
- URL-encode special characters with `urllib.parse.quote()`
- Add timeouts to HTTP requests: `urlopen(request, timeout=30)`
- Check tool availability: `shutil.which("git")`

**Shell scripts:**
- Provide both `.sh` (Unix) and `.cmd` (Windows) wrappers
- Detect Python: Unix uses `python3`, Windows uses `py -3`
- Use `${VARIABLE}` not `$VARIABLE` for safety
- Quote paths with spaces: `"$file_path"`

## Testing Requirements

**Test Matrix - Must verify across:**

| Dimension | Required Coverage | Priority |
|-----------|------------------|----------|
| **Git Providers** | GitHub, GitLab, Bitbucket, Azure DevOps | P0 for provider-dependent skills |
| **Coding Agents** | Claude Code, Cursor, Windsurf, Cline | P0 for Claude Code, P1 for others |
| **Operating Systems** | macOS, Ubuntu/Debian, Windows | P0 for all three |

**Checklist before submitting:**

- [ ] Skill invokes without errors
- [ ] Instructions are clear and unambiguous
- [ ] Helper scripts work independently
- [ ] Error messages are helpful
- [ ] Edge cases handled gracefully
- [ ] Works with different project structures
- [ ] File size under 500 lines (ideally ~300)

**Cross-platform verification:**
- [ ] **macOS**: Tested with zsh/bash and `python3`
- [ ] **Ubuntu/Debian**: Tested with bash and `python3`
- [ ] **Windows**: Tested with cmd and `py -3`
- [ ] Scripts handle path separators (`/` vs `\`)
- [ ] Scripts handle spaces in paths

**Git provider verification** (if skill interacts with git providers):
- [ ] **GitHub**: Tested with `gh` CLI
- [ ] **GitLab**: Tested with `glab` CLI
- [ ] **Bitbucket**: Tested with `bb` CLI or API
- [ ] **Azure DevOps**: Tested with `az devops` CLI
- [ ] URL parsing works for all providers
- [ ] PR/MR detection works for all providers

**Coding agent verification:**
- [ ] **Claude Code**: Tested with `/plugin install` or `npx skills add`
- [ ] **Cursor**: Tested with `npx skills add`
- [ ] **Windsurf/Cline**: Tested with `npx skills add`
- [ ] Trigger patterns work across agents
- [ ] Error messages display correctly

**Testing commands:**
```bash
# Test Python syntax
python3 -m py_compile scripts/my-script.py

# Test script functionality
python3 scripts/my-script.py --test-arg

# Install skill locally
npx skills add /path/to/qodo-skills/skills/my-skill

# Test in agent
/my-skill
```

## Git Workflow

**Branch naming:**
- `feature/skill-name` - New skills
- `fix/issue-description` - Bug fixes
- `docs/what-changed` - Documentation updates

**Commit messages:**
```
Brief description (50 chars or less)

- Key change 1
- Key change 2
- Key change 3

[Optional: detailed explanation]

Co-Authored-By: [Your Name] <email@example.com>
```

## Common Commands

**Development:**
```bash
# Test Python script
python3 scripts/fetch-qodo-rules.py

# Check syntax
python3 -m py_compile scripts/*.py

# Run unit tests (if available)
python3 -m pytest tests/
```

**Installation:**
```bash
# Install skill locally
npx skills add /path/to/qodo-skills/skills/get-qodo-rules

# Claude Code marketplace: Coming soon
```

**Testing:**
```bash
# Invoke skill manually
/get-qodo-rules
/qodo-pr-resolver

# Check git status
git status

# View recent commits
git log --oneline -10
```

## Resources

- **README.md**: User documentation and installation guide
- **CONTRIBUTING.md**: Detailed skill authoring guidelines with examples
- **SKILL.md files**: Individual skill specifications
- **Agent Skills Standard**: https://agentskills.io
- **npx skills CLI**: https://github.com/vercel-labs/skills

## Questions?

- **General questions**: Open a [Discussion](https://github.com/qodo-ai/qodo-skills/discussions)
- **Bug reports**: Open an [Issue](https://github.com/qodo-ai/qodo-skills/issues)
- **Contributions**: See CONTRIBUTING.md

---

**Note**: For Claude Code-specific directives (tool preferences, commit conventions), see CLAUDE.md.
# Contributing to Qodo Skills

Thank you for your interest in contributing to Qodo Skills! This guide will help you create and submit new skills.

## Quick Start

1. Fork the repository
2. Create a new branch for your skill
3. Add your skill following the format below
4. Test thoroughly
5. Submit a pull request

## Skill Structure

Each skill should be in its own directory with the following structure:

```
my-skill/
├── SKILL.md          # Required: Main skill file
├── scripts/          # Optional: Helper scripts
│   └── helper.sh
├── tests/           # Optional: Tests for scripts
│   └── test.sh
└── README.md        # Optional: Additional documentation
```

## SKILL.md Format

Your `SKILL.md` file must include YAML frontmatter and detailed instructions:

```markdown
---
name: my-skill
description: "Brief description (1-2 sentences) for skill discovery"
version: 1.0.0
allowed-tools: ["Bash", "Read", "Edit", "Write"]
triggers:
  - keyword1
  - keyword2
---

# Skill Name

## Description

Detailed explanation of what the skill does and when to use it.

## Prerequisites

- Required tools (CLI, APIs, etc.)
- Required configuration
- Required permissions

## Instructions

Clear, step-by-step instructions for the AI agent.

### Step 1: Initial Setup

Detailed instructions...

### Step 2: Main Workflow

More detailed instructions...

## Configuration

How to configure the skill...

## Error Handling

Common issues and how to handle them...

## Examples

Example usage scenarios...
```

## YAML Frontmatter Fields

### Required Fields

- **name**: Unique identifier (lowercase, hyphens only)
- **description**: Brief description for skill discovery (1-2 sentences)

### Optional Fields

- **version**: Semantic version (e.g., "1.0.0")
- **allowed-tools**: Array of tool names the skill can use
  - Common tools: `["Bash", "Read", "Edit", "Write", "Grep", "Glob", "WebFetch", "WebSearch"]`
  - Use to restrict tool access for security
- **triggers**: Array of patterns that auto-invoke the skill
  - Use regex-like patterns (e.g., `qodo.?fix` matches "qodo-fix", "qodo fix", "qodofix")
  - Only add triggers if the skill should auto-invoke

## Writing Good Instructions

### Do's ✅

- **Be specific**: Provide exact commands and code snippets
- **Use examples**: Show concrete examples of inputs and outputs
- **Handle errors**: Include error handling and edge cases
- **Be step-by-step**: Break complex workflows into clear steps
- **Use markdown formatting**: Make instructions easy to scan
- **Test thoroughly**: Verify the skill works in different scenarios

### Don'ts ❌

- **Be vague**: Avoid generic instructions like "do the right thing"
- **Assume context**: Don't assume the AI knows your domain
- **Skip error handling**: Always include graceful error handling
- **Over-complicate**: Keep it as simple as possible
- **Forget edge cases**: Think about what could go wrong

## Example: Good vs Bad Instructions

### ❌ Bad

```markdown
## Instructions

Check the git status and commit if needed.
```

### ✅ Good

```markdown
## Instructions

### Step 1: Check Git Status

Run the following command to check for uncommitted changes:

```bash
git status --porcelain
```

If the output is empty, skip to Step 3. Otherwise, proceed to Step 2.

### Step 2: Stage and Commit Changes

If there are uncommitted changes:

1. Review the changes with the user
2. Stage specific files: `git add <file1> <file2>`
3. Commit with a descriptive message:

```bash
git commit -m "Brief description of changes"
```

### Step 3: Handle Errors

- If `git status` fails: Check if the directory is a git repository
- If `git commit` fails: Check for merge conflicts or pre-commit hooks
```

## Helper Scripts

If your skill needs helper scripts:

1. Place them in the `scripts/` directory
2. Make them executable: `chmod +x scripts/helper.sh`
3. Use absolute paths or relative paths from the repository root
4. Include clear error messages
5. Exit with appropriate status codes (0 = success, non-zero = error)

### Script Template

```bash
#!/bin/bash
set -euo pipefail

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

## Testing Your Skill

### Local Testing

1. Install your skill locally:
   ```bash
   npx skills add /path/to/qodo-skills/my-skill
   ```

2. Test in your AI assistant:
   - Invoke manually: `/my-skill`
   - Test auto-invoke (if triggers defined)
   - Try edge cases and error scenarios

3. Test helper scripts independently:
   ```bash
   cd my-skill/scripts
   ./helper.sh --test-arg
   ```

### Test Checklist

- [ ] Skill invokes without errors
- [ ] Instructions are clear and unambiguous
- [ ] Helper scripts work independently
- [ ] Error messages are helpful
- [ ] Edge cases are handled gracefully
- [ ] Works with different project structures
- [ ] Documentation is complete

## Submitting Your Contribution

### 1. Create a Branch

```bash
git checkout -b add-my-skill
```

### 2. Add Your Skill

```bash
git add my-skill/
```

### 3. Commit with a Descriptive Message

```bash
git commit -m "Add my-skill: Brief description

- Key feature 1
- Key feature 2
- Key feature 3"
```

### 4. Push to Your Fork

```bash
git push origin add-my-skill
```

### 5. Create a Pull Request

Use the GitHub CLI or web interface:

```bash
gh pr create \
  --title "Add my-skill: Brief description" \
  --body "## Description

Detailed description of what the skill does and why it's useful.

## Testing

- [ ] Tested with Claude Code
- [ ] Tested with Cursor
- [ ] Tested helper scripts independently
- [ ] Verified error handling

## Related Issues

Closes #123 (if applicable)"
```

## Pull Request Guidelines

### PR Checklist

- [ ] Skill name is unique and descriptive
- [ ] SKILL.md follows the required format
- [ ] YAML frontmatter is valid
- [ ] Instructions are clear and detailed
- [ ] Helper scripts (if any) are tested
- [ ] Error handling is comprehensive
- [ ] Documentation is complete
- [ ] No sensitive information (API keys, tokens, etc.)

### What We Look For

1. **Clarity**: Instructions should be easy for an AI to follow
2. **Completeness**: All edge cases and errors handled
3. **Quality**: Well-tested and reliable
4. **Documentation**: Clear description and usage examples
5. **Compatibility**: Works with multiple AI assistants (when possible)

## Skill Ideas

Looking for inspiration? Here are some skill ideas:

- **Code review**: Automated code review checklists
- **Testing**: Generate and run tests for specific frameworks
- **Documentation**: Auto-generate docs from code
- **Deployment**: Deploy to specific platforms
- **Database**: Database migration helpers
- **API integration**: Common API interaction patterns
- **Security**: Security scanning and compliance checks

## Questions?

- **General questions**: Open a [Discussion](https://github.com/qodo-ai/qodo-skills/discussions)
- **Bug reports**: Open an [Issue](https://github.com/qodo-ai/qodo-skills/issues)
- **Quick questions**: Comment on an existing issue or PR

## Code of Conduct

Be respectful, inclusive, and professional. We're all here to build better tools together.

Thank you for contributing! 🎉

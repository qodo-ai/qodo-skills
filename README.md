# Qodo Skills

A collection of skills for AI coding assistants (Claude Code, Cursor, Windsurf, etc.) that integrate with the Qodo platform.

## Available Skills

### 🔧 get-rules
Automatically fetches repository-specific coding rules from the Qodo platform API at conversation start. Applies security requirements, coding standards, and team conventions during code generation.

**Features:**
- Auto-invokes at conversation start in git repositories
- Repository-aware rule fetching
- Hierarchical rule matching (universal, org, repo, path-level)
- Severity-based enforcement (ERROR, WARNING, RECOMMENDATION)

[View skill details](./get-rules/SKILL.md)

### 🔍 qodo-fix
Review code with Qodo and fix AI-powered code review issues interactively across GitHub, GitLab, and Bitbucket.

**Features:**
- Multi-provider support (GitHub, GitLab, Bitbucket)
- Interactive issue review and fixing
- Auto-fix mode for batch fixes
- Automatic PR/MR comment summaries

[View skill details](./qodo-fix/SKILL.md)

## Installation

### Using npx skills (Recommended)

Install skills directly from this repository using the [skills.sh](https://skills.sh) ecosystem:

```bash
# Install a specific skill
npx skills add qodo-ai/qodo-skills/get-rules
npx skills add qodo-ai/qodo-skills/qodo-fix

# Install all skills from this repository
npx skills add qodo-ai/qodo-skills
```

### Manual Installation

#### For Claude Code

Copy skill directories to your project or global skills directory:

```bash
# Project-specific (recommended)
cp -r get-rules /path/to/your/project/.claude/skills/

# Global installation
cp -r get-rules ~/.claude/skills/
```

#### For Other Agents

Different agents have different skill directories:

- **Cursor**: `.cursor/skills/`
- **Windsurf**: `.windsurf/skills/`
- **Gemini CLI**: `.gemini/skills/`

Example:
```bash
cp -r get-rules /path/to/your/project/.cursor/skills/
```

## Configuration

### get-rules Skill

Create `~/.qodo/config.json`:

```json
{
  "QODO_CLI_API_KEY": "sk-xxxxxxxxxxxxx",
  "QODO_RULES_API_URL": "https://api.qodo.ai"
}
```

Get your API key at: https://app.qodo.ai/settings/api-keys

Or set environment variable:
```bash
export QODO_CLI_API_KEY="sk-xxxxxxxxxxxxx"
```

### qodo-fix Skill

Requires CLI tools for your git provider:

- **GitHub**: `gh` CLI ([install guide](https://cli.github.com/))
- **GitLab**: `glab` CLI ([install guide](https://glab.readthedocs.io/))
- **Bitbucket**: `bb` CLI

## Usage

### In Claude Code

Skills can be invoked automatically (get-rules) or manually:

```bash
# Invoke get-rules manually if needed
/get-rules

# Invoke qodo-fix
/qodo-fix
```

### Finding Skills

Use the interactive skill browser:

```bash
npx skills find
```

Or search for Qodo skills:

```bash
npx skills find qodo
```

## Publishing to skills.sh

This repository is designed to be compatible with the [skills.sh](https://skills.sh) ecosystem. To publish your own fork or contribute new skills:

### 1. Fork this repository

```bash
gh repo fork qodo-ai/qodo-skills
```

### 2. Add your skill

Create a new directory with a `SKILL.md` file:

```markdown
---
name: my-skill
description: What this skill does
allowed-tools: ["Bash", "Read", "Edit"]
---

# My Skill

Instructions for the agent...
```

### 3. Test locally

```bash
# Install from your local directory
npx skills add /path/to/qodo-skills/my-skill

# Or from your GitHub fork
npx skills add yourusername/qodo-skills/my-skill
```

### 4. Submit a Pull Request

If you've created a useful skill, consider contributing it back:

```bash
git checkout -b add-my-skill
git add my-skill/
git commit -m "Add my-skill: brief description"
git push origin add-my-skill
gh pr create --title "Add my-skill" --body "Description of the skill"
```

## Skill Format

Skills follow the standard skills.sh format:

```
skill-name/
├── SKILL.md          # Main skill file with YAML frontmatter
├── scripts/          # Optional: shell scripts or executables
│   └── helper.sh
└── docs/            # Optional: additional documentation
    └── examples.md
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief description for discovery
version: 1.0.0           # Optional
allowed-tools: ["Bash"]  # Optional: restrict tools
triggers:                # Optional: auto-invoke patterns
  - pattern1
  - pattern2
---

# Skill Name

Detailed instructions for the AI agent...
```

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Add your skill following the format above
4. Test thoroughly with your AI assistant
5. Submit a pull request

## Resources

- [skills.sh Documentation](https://skills.sh)
- [Vercel skills GitHub](https://github.com/vercel-labs/skills)
- [Qodo Platform](https://qodo.ai)
- [Claude Code Documentation](https://code.claude.com/docs)

## License

MIT License - see LICENSE file for details

## Support

For issues with:
- **Skills themselves**: Open an issue in this repository
- **Qodo Platform**: Contact [Qodo Support](https://qodo.ai/support)
- **skills.sh tool**: See [vercel-labs/skills](https://github.com/vercel-labs/skills)

# Qodo Skills

Shift-left code review skills for AI coding agents. Bring Qodo's quality standards and code review capabilities into your local development workflow.

**Compatible with:** Claude Code, Cursor, Windsurf, Cline, and any agent supporting the [Agent Skills](https://agentskills.io) standard.

## Available Skills

### 🔧 qodo-get-rules
Fetches repository-specific coding rules from the Qodo platform API. Provides your agent with security requirements, coding standards, and team conventions before generating code.

**Features:**
- 📚 Hierarchical rule matching (universal, org, repo, path-level)
- ⚖️ Severity-based enforcement (ERROR, WARNING, RECOMMENDATION)
- 🔄 Module-specific scope detection (`modules/` directories)
- 📄 Pagination support for large rule sets
- 🪟 **Full Windows support** - Native compatibility without requiring Git Bash/WSL

[View skill details](./skills/qodo-get-rules/SKILL.md)

### 🔍 qodo-pr-resolver
Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision.

**Features:**
- Multi-provider support (GitHub, GitLab, Bitbucket, Azure DevOps)
- Interactive issue review and auto-fix modes
- Per-issue inline comment replies and git commits
- Severity mapping from Qodo's action levels
- Automatic PR/MR summary comments

[View skill details](./skills/qodo-pr-resolver/SKILL.md)

### 🛡️ check-rules
Shift Qodo rule enforcement left -- check code against rules at planning time and before committing. Catches violations before they reach PR review.

**Features:**
- Fetches rules and factors ERROR rules into implementation plans
- Pre-commit check: scans staged changes against rule `badExamples`
- Structured violation report with fix suggestions from `goodExamples`
- Severity-aware: blocks on ERROR, advises on WARNING, skips RECOMMENDATION

[View skill details](./skills/check-rules/SKILL.md)

## Installation

Install skills using the standard Agent Skills CLI:

```bash
# Install all Qodo skills
npx skills add qodo-ai/qodo-skills

# Or install individual skills
npx skills add qodo-ai/qodo-skills/skills/qodo-get-rules
npx skills add qodo-ai/qodo-skills/skills/qodo-pr-resolver
npx skills add qodo-ai/qodo-skills/skills/check-rules
```

**Claude Code Marketplace:**
```
/plugin install qodo-skills@claude-plugins-official
```

**Works with:**
- **Claude Code** - Skills available as `/qodo-get-rules`, `/qodo-pr-resolver`
- **Cursor** - Skills available in command palette
- **Windsurf** - Skills available in flow menu
- **Cline** - Skills available via skill invocation
- **Any agent** supporting [agentskills.io](https://agentskills.io)

### Agent-Specific Directories

Skills are automatically installed to the correct location for your agent:

| Agent | Installation Directory |
|-------|----------------------|
| Claude Code | `~/.claude/skills/` or `.claude/skills/` |
| Cursor | `~/.cursor/skills/` or `.cursor/skills/` |
| Windsurf | `~/.windsurf/skills/` or `.windsurf/skills/` |
| Cline | `~/.cline/skills/` or `.cline/skills/` |

## Prerequisites

### System Requirements

- **Git** - For repository detection
  - Usually pre-installed on macOS and most Linux distributions
  - Windows: Download from https://git-scm.com/download/win
- **curl** - For HTTPS API requests (works with system SSL certificates)
  - Pre-installed on macOS, most Linux distributions, and Windows 10+
  - If needed, install via package manager or download from https://curl.se
  ```bash
  # Check installation
  curl --version

  # Install if needed:
  # macOS: brew install curl (or use system curl)
  # Ubuntu/Debian: apt-get install curl
  # Windows 10+: Included by default
  ```
- **Python 3.6+** - For JSON parsing and path manipulation only (no API calls)
  - Pre-installed on macOS and most Linux distributions
  - Windows: Download from https://www.python.org/downloads/

**Note:** All prerequisites use standard system tools with no external dependencies.

## Configuration

### qodo-get-rules Skill

Create `~/.qodo/config.json`:

```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx",
  "ENVIRONMENT_NAME": "staging"
}
```

**Configuration fields:**
- `API_KEY` (required): Your Qodo API key
- `ENVIRONMENT_NAME` (optional): Environment name for API URL
  - If empty/omitted: Uses `https://qodo-platform.qodo.ai/rules/v1/`
  - If specified: Uses `https://qodo-platform.<ENVIRONMENT_NAME>.qodo.ai/rules/v1/`
- `QODO_API_URL` (optional): Direct API base URL — overrides `ENVIRONMENT_NAME`
  - Use for self-hosted, on-prem, or custom deployments
  - Example: `"QODO_API_URL": "https://qodo.my-company.com"`
  - The skill appends `/rules/v1` internally; provide the base URL only

**URL resolution priority:** `QODO_API_URL` → `ENVIRONMENT_NAME` → production default

Get your API key at: https://app.qodo.ai/account/api-keys

**Minimal configuration (production):**
```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx"
}
```

**Custom deployment:**
```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx",
  "QODO_API_URL": "https://qodo.my-company.com"
}
```

**Environment variables (take precedence over config file):**
```bash
export QODO_API_KEY="sk-xxxxxxxxxxxxx"
export QODO_ENVIRONMENT_NAME="staging"  # optional
```

### qodo-pr-resolver Skill

Requires CLI tools for your git provider:

- **GitHub**: `gh` CLI ([install guide](https://cli.github.com/))
- **GitLab**: `glab` CLI ([install guide](https://glab.readthedocs.io/))
- **Bitbucket**: `bb` CLI
- **Azure DevOps**: `az` CLI with DevOps extension ([install guide](https://docs.microsoft.com/cli/azure/))

## Usage

### In Your Agent

After installation, invoke skills directly in your agent:

**Claude Code:**
```bash
/qodo-get-rules      # Fetch coding rules
/qodo-pr-resolver    # Fix PR review issues
```

**Cursor / Windsurf / Cline:**
- Open command palette
- Search for "qodo-get-rules" or "qodo-pr-resolver"
- Or invoke via agent command input

### Managing Skills

**Update skills:**
```bash
# Update individual skills
npx skills update qodo-ai/qodo-skills/skills/qodo-get-rules
npx skills update qodo-ai/qodo-skills/skills/qodo-pr-resolver
```

**List installed skills:**
```bash
npx skills list
```

**Remove skills:**
```bash
npx skills remove qodo-get-rules
```

## Repository Structure

This repository follows the [Agent Skills](https://agentskills.io) standard:

```
qodo-skills/
├── skills/
│   ├── qodo-get-rules/           # Fetch coding rules skill
│   │   ├── SKILL.md         # Agent Skills standard
│   │   └── scripts/
│   │       ├── fetch-qodo-rules.py   # Main script (cross-platform)
│   │       ├── fetch-qodo-rules.sh   # Unix/macOS/Linux wrapper
│   │       └── fetch-qodo-rules.cmd  # Windows wrapper
│   └── qodo-pr-resolver/        # Fix PR review issues skill
│       └── SKILL.md
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

### How It Works

1. Skills are installed to agent-specific directories via `npx skills add`
2. Available for manual invocation in any compatible agent
3. Skills execute via their SKILL.md instructions

### Testing Locally

**Test with any agent:**
```bash
npx skills add /path/to/qodo-skills/skills/get-qodo-rules
```

## Troubleshooting

### Skill not found?

**Verify installation:**
```bash
npx skills list | grep qodo
```

**Reinstall if needed:**
```bash
npx skills add qodo-ai/qodo-skills
```

### Rules not loading?

**Check you're in a git repository:**
```bash
git status
```

**Verify API key is configured:**
```bash
cat ~/.qodo/config.json
```

**Check Python is installed:**
```bash
python3 --version || python --version
```

**Manually test the fetch script:**
```bash
# Navigate to your agent's skills directory and run the Python script directly
cd ~/.claude/skills/qodo-get-rules  # or ~/.cursor/skills/qodo-get-rules, etc.
python3 scripts/fetch-qodo-rules.py

# Or use the shell wrapper (Unix/macOS/Linux):
scripts/fetch-qodo-rules.sh

# Or use the batch wrapper (Windows):
scripts\fetch-qodo-rules.cmd
```

### No rules found?

- Rules must be configured in the Qodo platform for your repository
- Visit https://app.qodo.ai to set up rules
- Check that your repository remote URL matches the configured scope

### Windows-specific issues?

**Python not found:**
- Ensure Python 3.6+ is installed and in PATH
- Test: `python --version` or `py -3 --version` in PowerShell/cmd
- Reinstall Python with "Add Python to PATH" option checked

**Git not found:**
- Install Git for Windows: https://git-scm.com/download/win
- Test: `git --version` in PowerShell/cmd

**Path separators:**
- The script automatically handles Windows backslashes (`\`) vs Unix forward slashes (`/`)
- API URLs always use forward slashes regardless of platform

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test thoroughly with your preferred agent (Claude Code, Cursor, etc.)
5. Submit a pull request

## Resources

- [Agent Skills Standard](https://agentskills.io) - Universal skill format
- [npx skills CLI](https://github.com/vercel-labs/skills) - Install and manage skills
- [Qodo Platform](https://qodo.ai) - Set up coding rules and review
- [Claude Code Documentation](https://code.claude.com/docs) - Claude Code specific features

## License

MIT License - see [LICENSE](./LICENSE) file for details

## Support

For issues with:
- **Skills themselves**: [Open an issue](https://github.com/qodo-ai/qodo-skills/issues) in this repository
- **Qodo Platform**: Contact [Qodo Support](https://qodo.ai/support)
- **npx skills tool**: See [vercel-labs/skills](https://github.com/vercel-labs/skills)
- **Your agent**: Refer to your agent's documentation (Claude Code, Cursor, Windsurf, etc.)

# Qodo Skills

Shift-left code review skills for AI coding agents. Bring Qodo's quality standards and code review capabilities into your local development workflow.

**Compatible with:** Claude Code, Cursor, Windsurf, Cline, and any agent supporting the [Agent Skills](https://agentskills.io) standard.

## Available Skills

### 🔧 get-rules
Fetches repository-specific coding rules from the Qodo platform API. Provides your agent with security requirements, coding standards, and team conventions before generating code.

**Features:**
- 🎯 **Must load before coding**: Agent invokes before any code generation/modification task (if not already loaded)
- 📚 Hierarchical rule matching (universal, org, repo, path-level)
- ⚖️ Severity-based enforcement (ERROR, WARNING, RECOMMENDATION)
- 🔄 Module-specific scope detection (`modules/` directories)
- 📄 Pagination support for large rule sets
- ⚡ Auto-executes via SessionStart hook (Claude Code plugin only)
- 🪟 **Full Windows support** - Native compatibility without requiring Git Bash/WSL

[View skill details](./skills/get-rules/SKILL.md)

### 🔍 qodo-fix
Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision.

**Features:**
- Multi-provider support (GitHub, GitLab, Bitbucket, Azure DevOps)
- Interactive issue review and auto-fix modes
- Per-issue inline comment replies and git commits
- Severity mapping from Qodo's action levels
- Automatic PR/MR summary comments

[View skill details](./qodo-fix/SKILL.md)

## Installation

### Using npx skills (Recommended)

Install skills using the standard Agent Skills CLI:

```bash
# Install all Qodo skills
npx skills add qodo-ai/qodo-skills

# Or install individual skills
npx skills add qodo-ai/qodo-skills/get-rules
npx skills add qodo-ai/qodo-skills/qodo-fix
```

**Works with:**
- **Claude Code** - Skills available as `/get-rules`, `/qodo-fix`
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

### Auto-Invocation (Claude Code Only)

For automatic rule fetching at session start in Claude Code, install as a plugin:

```bash
# Claude Code plugin installation
/plugin install https://github.com/qodo-ai/qodo-skills
```

**Plugin features:**
- ✅ Auto-fetches rules at every session start
- ✅ Works across all projects automatically
- ✅ Zero per-project configuration
- ✅ Version management with `/plugin update`

**Note:** Other agents can use the skills but require manual invocation (e.g., `/get-rules`).

## Prerequisites

### System Requirements

- **Git** - For repository detection
  - Usually pre-installed on macOS and most Linux distributions
  - Windows: Download from https://git-scm.com/download/win
- **Python 3.6+** - For API requests and cross-platform compatibility
  - No external dependencies required (uses standard library only)
  ```bash
  # Check installation
  python3 --version
  # or
  python --version

  # Install if needed:
  # macOS: brew install python3
  # Ubuntu/Debian: apt-get install python3
  # Windows: https://www.python.org/downloads/
  #   (Make sure to check "Add Python to PATH" during installation)
  ```

**Note:** The script automatically detects Python using:
- **Windows:** `py -3` → `python3` → `python`
- **Unix/macOS/Linux:** `python3` → `python`

## Configuration

### get-rules Skill

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

Get your API key at: https://app.qodo.ai/settings/api-keys

**Minimal configuration (production):**
```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx"
}
```

**Environment variables (take precedence over config file):**
```bash
export QODO_API_KEY="sk-xxxxxxxxxxxxx"
export QODO_ENVIRONMENT_NAME="staging"  # optional
```

### qodo-fix Skill

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
/get-rules      # Fetch coding rules
/qodo-fix       # Fix PR review issues
```

**Cursor / Windsurf / Cline:**
- Open command palette
- Search for "get-rules" or "qodo-fix"
- Or invoke via agent command input

### Automatic Rule Loading (Claude Code)

If installed as a Claude Code plugin, `get-rules` automatically fetches rules at session start:

```
📋 Loading Qodo rules from API...

# 📋 Qodo Rules Loaded

Repository: `/your-org/your-repo/`
Rules loaded: 12 (universal, org level, repo level, and path level rules)
```

You can manually refresh mid-session:
```bash
/get-rules
```

### Managing Skills

**Update skills:**
```bash
npx skills update qodo-ai/qodo-skills
```

**List installed skills:**
```bash
npx skills list
```

**Remove skills:**
```bash
npx skills remove get-rules
```

### Claude Code Plugin Management

If installed as a Claude Code plugin:

```bash
/plugin                        # List installed plugins
/plugin update qodo-skills     # Update to latest version
/plugin disable qodo-skills    # Disable temporarily
/plugin enable qodo-skills     # Re-enable
/plugin uninstall qodo-skills  # Uninstall
```

## Repository Structure

This repository follows the [Agent Skills](https://agentskills.io) standard with Claude Code plugin extensions:

```
qodo-skills/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest (Claude Code)
├── skills/
│   ├── get-rules/           # Fetch coding rules skill
│   │   ├── SKILL.md         # Agent Skills standard
│   │   └── scripts/
│   │       ├── fetch-qodo-rules.py   # Main script (cross-platform)
│   │       ├── fetch-qodo-rules.sh   # Unix/macOS/Linux wrapper
│   │       └── fetch-qodo-rules.cmd  # Windows wrapper
│   └── qodo-fix/           # Fix PR review issues skill
│       └── SKILL.md
├── hooks/
│   └── hooks.json           # Auto-invocation hooks (Claude Code)
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

### How It Works

**Standard Installation (npx skills):**
1. Skills are installed to agent-specific directories
2. Available for manual invocation in any compatible agent
3. Skills execute via their SKILL.md instructions

**Plugin Installation (Claude Code only):**
1. Installed as a Claude Code plugin via `/plugin install`
2. SessionStart hook automatically runs `fetch-qodo-rules.py` at session start (works on all platforms)
3. Rules are loaded into context before you start working
4. Can still invoke manually with `/get-rules`

### Testing Locally

**Test with any agent:**
```bash
npx skills add /path/to/qodo-skills/skills/get-rules
```

**Test as Claude Code plugin:**
```bash
cd /path/to/qodo-skills
claude --plugin-dir .

# Enable debug mode to see hook execution
/debug

# Check that rules loaded at session start
# Look for: "📋 Loading Qodo rules from API..."
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
cd ~/.claude/skills/get-rules  # or ~/.cursor/skills/get-rules, etc.
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

### Auto-fetch not working (Claude Code)?

**Enable debug mode:**
```bash
/debug
# Look for hook execution logs
```

**Disable/re-enable plugin:**
```bash
/plugin disable qodo-skills
/plugin enable qodo-skills
```

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

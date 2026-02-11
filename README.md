# Qodo Skills

A Claude Code plugin that provides Qodo coding standards and best practices with automatic rule fetching.

## Available Skills

### 🔧 get-rules
Automatically fetches repository-specific coding rules from the Qodo platform API at conversation start. Applies security requirements, coding standards, and team conventions during code generation.

**Features:**
- ✨ Auto-invokes at conversation start (via plugin hooks)
- 🎯 Repository-aware rule fetching
- 📚 Hierarchical rule matching (universal, org, repo, path-level)
- ⚖️ Severity-based enforcement (ERROR, WARNING, RECOMMENDATION)
- 🔄 Module-specific scope detection (`modules/` directories)
- 📄 Pagination support for large rule sets

[View skill details](./skills/get-rules/SKILL.md)

### 🔍 qodo-fix
Review code with Qodo and fix AI-powered code review issues interactively across GitHub, GitLab, and Bitbucket.

**Features:**
- Multi-provider support (GitHub, GitLab, Bitbucket)
- Interactive issue review and fixing
- Auto-fix mode for batch fixes
- Automatic PR/MR comment summaries

[View skill details](./qodo-fix.md)

## Installation

### As a Claude Code Plugin (Recommended)

Install as a plugin for automatic rule loading across all your projects:

```bash
# Install the plugin (works for all projects)
/plugin install https://github.com/qodo-ai/qodo-skills

# Or if using a plugin marketplace
/plugin marketplace add qodo-ai/plugin-marketplace
/plugin install qodo-skills
```

**What you get:**
- ✅ Auto-fetches rules at every session start
- ✅ Works across all projects automatically
- ✅ Zero per-project configuration
- ✅ Version management with `/plugin update`

**Installation scopes:**
```bash
# User scope (default) - available in all your projects
/plugin install qodo-skills

# Project scope - shared with team via git
/plugin install qodo-skills --scope project

# Local scope - personal, not shared
/plugin install qodo-skills --scope local
```

### Manual Installation (Alternative)

For individual skills or other AI assistants:

```bash
# Copy skills directory to your project
cp -r skills/get-rules /path/to/your/project/.claude/skills/

# For other AI assistants (Cursor, Windsurf, etc.)
cp -r skills/get-rules /path/to/your/project/.cursor/skills/
```

**Note:** Manual installation requires configuring hooks separately in `.claude/settings.json` for auto-invocation.

## Prerequisites

### System Requirements

- **Git** - For repository detection
- **jq** - For JSON parsing
  ```bash
  # macOS
  brew install jq

  # Ubuntu/Debian
  apt-get install jq

  # Check installation
  jq --version
  ```
- **curl** - For API requests (usually pre-installed)

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

## Usage

### Automatic (Plugin Installation)

When installed as a plugin, `get-rules` automatically fetches coding rules at every session start. You'll see:

```
📋 Loading Qodo rules from API...

# 📋 Qodo Rules Loaded

Repository: `/your-org/your-repo/`
Rules loaded: 12 (universal, org level, repo level, and path level rules)
```

### Manual Invocation

You can also manually refresh rules mid-session:

```bash
# If installed as plugin
/qodo-skills:get-rules

# If installed manually (without plugin)
/get-rules

# Invoke qodo-fix
/qodo-fix
```

### Managing the Plugin

```bash
# Check installed plugins
/plugin

# Update to latest version
/plugin update qodo-skills

# Disable temporarily
/plugin disable qodo-skills

# Enable again
/plugin enable qodo-skills

# Uninstall
/plugin uninstall qodo-skills
```

## Plugin Structure

This repository is a Claude Code plugin with the following structure:

```
qodo-skills/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest
├── skills/
│   ├── get-rules/           # Auto-fetch coding rules skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── fetch-qodo-rules.sh
│   └── qodo-fix/           # Fix code review issues skill
│       └── SKILL.md
├── hooks/
│   └── hooks.json           # SessionStart hook for auto-invocation
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

### How It Works

1. **Plugin Installation**: Users run `/plugin install qodo-skills`
2. **SessionStart Hook**: Automatically runs `fetch-qodo-rules.sh` at every session start
3. **Rule Fetching**: Script queries Qodo API based on git repository and working directory
4. **Context Injection**: Rules are loaded into Claude's context for the entire session
5. **Manual Refresh**: Users can run `/qodo-skills:get-rules` to refresh mid-session

### Testing Locally

```bash
# Test the plugin from local directory
cd /path/to/qodo-skills
claude --plugin-dir .

# Enable debug mode to see hook execution
/debug

# Check that rules loaded at session start
# Look for: "📋 Loading Qodo rules from API..."
```

## Troubleshooting

### Rules not loading?

**Check you're in a git repository:**
```bash
git status
```

**Verify API key is configured:**
```bash
cat ~/.qodo/config.json
```

**Check jq is installed:**
```bash
jq --version
```

**Enable debug mode to see hook execution:**
```bash
/debug
# Look for hook execution logs
```

**Manually test the fetch script:**
```bash
~/.claude/plugins/cache/qodo-skills/qodo-skills-1.0.0/skills/get-rules/scripts/fetch-qodo-rules.sh
```

### No rules found?

- Rules must be configured in the Qodo platform for your repository
- Visit https://app.qodo.ai to set up rules
- Check that your repository remote URL matches the configured scope

### Want to disable auto-fetch?

```bash
/plugin disable qodo-skills
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test thoroughly with Claude Code
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

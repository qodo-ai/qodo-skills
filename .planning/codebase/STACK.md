# Technology Stack

**Analysis Date:** 2026-03-01

## Languages

**Primary:**
- Python 3.6+ - Core implementation for Qodo API client and rule fetching (`scripts/fetch-qodo-rules.py`)
- Bash - Unix/macOS/Linux wrapper scripts (`scripts/fetch-qodo-rules.sh`)
- Batch/CMD - Windows wrapper scripts (`scripts/fetch-qodo-rules.cmd`)

**Markdown:**
- Markdown - Skill documentation and references (SKILL.md, references/*.md)

## Runtime

**Environment:**
- Python 3 (cross-platform support)
- Bash shell (Unix/macOS/Linux)
- Command prompt/PowerShell (Windows)

**Package Manager:**
- None - Uses only Python standard library
- No external dependencies (intentional design for minimal setup overhead)

## Frameworks

**Core:**
- No framework dependencies - Pure Python standard library implementation
- urllib/http clients for HTTPS API requests (built-in)
- json for payload parsing (built-in)
- subprocess for git command execution (built-in)

**Scripting:**
- Bash/Batch wrappers for cross-platform Python execution

**Build/Dev:**
- Agent Skills CLI (`npx skills add`) - For skill installation and management
- Git - For repository detection and scope extraction

## Key Dependencies

**System Tools (Required):**
- Git - Repository detection and remote URL parsing
  - Used for: `git config --get remote.origin.url`, `git rev-parse --show-toplevel`
  - Cross-platform: macOS (pre-installed), Linux (pre-installed), Windows (must install)
- curl - HTTPS API requests (used indirectly)
  - Pre-installed on macOS 10+, most Linux distributions, Windows 10+
- Python 3.6+ - Main runtime
  - Cross-platform availability required

**Git Provider CLIs (Conditional - for qodo-pr-resolver only):**
- `gh` CLI - GitHub support (install: `brew install gh` or https://cli.github.com)
- `glab` CLI - GitLab support (install: `brew install glab` or https://glab.readthedocs.io)
- `bb` CLI - Bitbucket support (install: https://bitbucket.org/product/cli)
- `az` CLI - Azure DevOps support (install: `brew install azure-cli` or https://docs.microsoft.com/cli/azure)

## Configuration

**Environment:**
- Configuration file: `~/.qodo/config.json`
  - Fields: `API_KEY` (required), `ENVIRONMENT_NAME` (optional)
  - Location: User home directory `.qodo` subdirectory
  - Format: JSON key-value pairs

**Environment Variables (override config file):**
- `QODO_API_KEY` - Qodo platform API key (takes precedence over config file)
- `QODO_ENVIRONMENT_NAME` - API environment name for staging/custom deployments (optional)
- `TRACE_ID` - Optional tracing ID for request correlation (used in API headers)

**Build:**
- `hooks.json` - Claude plugin session start hooks (in `.planning/codebase/`)
- Hook type: Python script execution via SessionStart matcher
- Timeout: 30 seconds for rule fetching at session start

## Platform Requirements

**Development:**
- Python 3.6+ installed and in PATH
- Git installed and configured with repository remotes
- For Windows: Native Python 3 support (no Git Bash required)

**Production:**
- Agent platform compatibility: Claude Code, Cursor, Windsurf, Cline
- Deployment: Agent-specific skill directories
  - Claude Code: `~/.claude/skills/` or `.claude/skills/`
  - Cursor: `~/.cursor/skills/` or `.cursor/skills/`
  - Windsurf: `~/.windsurf/skills/` or `.windsurf/skills/`
  - Cline: `~/.cline/skills/` or `.cline/skills/`

**Network:**
- HTTPS connectivity required
- System SSL certificates used for TLS validation
- Timeout: 30 seconds per API request

---

*Stack analysis: 2026-03-01*

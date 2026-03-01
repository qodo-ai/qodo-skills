# Architecture

**Analysis Date:** 2026-03-01

## Pattern Overview

**Overall:** Modular skill collection following the Agent Skills standard

**Key Characteristics:**
- **Distributed architecture**: Each skill is independently deployable and installable
- **Skill-based design**: Encapsulated, reusable components for distinct code review workflows
- **Configuration-driven**: Minimal runtime state, external configuration via `~/.qodo/config.json` and environment variables
- **Cross-platform compatibility**: Python core with platform-specific shell wrappers (`.sh` for Unix, `.cmd` for Windows)
- **Standards-based**: Conforms to [agentskills.io](https://agentskills.io) specification for universal agent compatibility

## Layers

**Skill Layer:**
- Purpose: Entry point for agent invocation; contains workflow logic and decision trees
- Location: `skills/[skill-name]/SKILL.md`
- Contains: Step-by-step instructions, error handling, user interaction flow
- Depends on: Agent runtime, external CLI tools (git, gh, glab, az, bb), Qodo API
- Used by: Claude Code, Cursor, Windsurf, Cline, or any Agent Skills compatible agent

**Configuration Layer:**
- Purpose: Loads and validates API credentials, environment settings, and repository scope
- Location: `~/.qodo/config.json` (user config), environment variables (overrides)
- Contains: API keys, environment names, request IDs
- Depends on: Filesystem, environment
- Used by: All skills during initialization (Steps 2-3 in each skill workflow)

**API Integration Layer:**
- Purpose: Communicates with Qodo platform for rules/reviews
- Location: Defined in skill workflows (raw curl/HTTP calls via agent)
- Contains: Qodo API endpoint specifications, pagination logic, request/response handling
- Depends on: curl, HTTPS, valid API key
- Used by: `qodo-get-rules`, `qodo-get-relevant-rules` for rule fetching; `qodo-pr-resolver` for review data

**Git Provider Layer:**
- Purpose: Abstracts multi-provider support (GitHub, GitLab, Bitbucket, Azure DevOps)
- Location: `skills/qodo-pr-resolver/resources/providers.md`
- Contains: Provider-specific CLI commands, URL parsing, PR/MR detection
- Depends on: Provider CLI tools (gh, glab, bb, az)
- Used by: `qodo-pr-resolver` to detect provider, find PRs, fetch reviews, post comments

**Helper/Reference Layer:**
- Purpose: Encapsulates reusable patterns and detailed specifications
- Location: `skills/[skill-name]/references/` directory
- Contains: Query generation, pagination algorithms, output formatting, repository scope detection
- Depends on: Nothing (read-only reference)
- Used by: Agents implementing skill workflows

## Data Flow

**qodo-get-rules Workflow:**

1. Agent checks conversation for "Qodo Rules Loaded" marker
2. → If found: skip; if not: proceed
3. Agent verifies git repository exists, extracts remote origin URL
4. → Determine repository scope (universal/org/repo/path-level)
5. Agent loads Qodo config: API key, environment, generates request ID
6. Agent calls `GET /rules?scope=...&page=N` with pagination (50 rules/page, max 100 pages)
7. → Accumulate all rule pages
8. Agent formats rules: group by severity (ERROR, WARNING, RECOMMENDATION)
9. Agent outputs: "📋 Qodo Rules Loaded" header + rule list + "---" footer
10. Agent applies rules during code generation:
    - ERROR rules: mandatory, document compliance in code comments
    - WARNING rules: should comply, explain if skipped
    - RECOMMENDATION rules: consider when appropriate
11. Agent reports which rules were applied or deferred

**qodo-get-relevant-rules Workflow:**

1. Agent checks conversation for "Qodo Rules Loaded" marker
2. → If found: skip; if not: proceed
3. Agent verifies git repository exists (no scope extraction)
4. Agent loads Qodo config: API key, environment, generates request ID
5. Agent generates **two structured search queries** from coding assignment:
   - **Topic query**: Focused on the assignment's primary concern (Name/Category/Content format)
   - **Cross-cutting query**: Targets architectural/quality patterns (Code Quality and Architecture Compliance)
6. Agent calls `POST /rules/search` **twice** (once per query) with `top_k=20`
7. → Merge results, deduplicate by rule ID
8. Agent formats rules: list in relevance order (no severity grouping)
9. Agent outputs: "📋 Qodo Rules Loaded" header + query + ranked rule list + "---" footer
10. Agent applies all returned rules during code generation (already ranked by relevance)
11. Agent reports which rules were applied

**qodo-pr-resolver Workflow:**

1. Agent checks git status: uncommitted changes? unpushed commits? → ask user
2. Agent detects git provider from remote URL (GitHub/GitLab/Bitbucket/Azure DevOps)
3. Agent uses provider CLI to find open PR/MR for current branch
4. Agent fetches Qodo review comments from PR/MR:
   - PR-level summary comments (compliance guide, code suggestions, code review)
   - Inline review comments (attached to specific code lines)
5. → Deduplicate issues by matching title (summary + inline = single issue)
6. Agent parses issues: extract title, location, description, severity, agent prompt
7. Agent displays issue table in Qodo's original order
8. Agent asks user: "Review each issue" / "Auto-fix all" / "Cancel"
9. **If "Review each":**
   - For each "Fix" issue: read file → show Qodo agent prompt → show current code → show proposed diff → ask approval (Apply/Defer/Modify)
   - If approved: apply fix via Edit, reply to inline comment, commit
   - If deferred: ask reason, reply to inline comment
10. **If "Auto-fix all":**
    - For each "Fix" issue: read file → apply fix → reply to inline comment → commit
11. After all issues addressed: post summary comment to PR/MR
12. Agent asks user: push to remote?
13. → If yes: git push

**State Management:**

- **Conversation memory**: Checks for "Qodo Rules Loaded" marker to avoid re-fetching
- **Git state**: Checked at runtime (uncommitted/unpushed changes, current branch)
- **Configuration state**: Loaded once per skill invocation from filesystem/environment
- **API requests**: Stateless — each request includes request ID for correlation
- **Code changes**: Applied via Edit/Write tools, tracked by git

## Key Abstractions

**Skill:**
- Purpose: A self-contained, agent-invokable capability following Agent Skills standard
- Examples: `skills/qodo-get-rules/SKILL.md`, `skills/qodo-pr-resolver/SKILL.md`, `skills/qodo-get-relevant-rules/SKILL.md`
- Pattern: YAML frontmatter (name, description, triggers, allowed-tools) + markdown instructions

**Repository Scope:**
- Purpose: Identifies the context for rule application (universal, org-wide, repo-wide, path-specific)
- Examples: `/` (universal), `/myorg/` (org level), `/myorg/myrepo/` (repo level), `/myorg/myrepo/src/auth/` (path level)
- Pattern: Extracted from git remote URL and working directory location

**Severity Levels:**
- Purpose: Indicates enforcement strength for rules in `qodo-get-rules`
- Values: ERROR (mandatory), WARNING (should comply), RECOMMENDATION (consider)
- Pattern: Each rule has a severity that determines how strictly it must be applied

**Search Query:**
- Purpose: Semantic query for retrieving relevant rules by topic and intent
- Format: Structured three-field block (Name/Category/Content) mirroring rule embedding format
- Pattern: Two queries per task (topic + cross-cutting) for comprehensive coverage

**Issue/Review Comment:**
- Purpose: Represents a single code review finding from Qodo
- Attributes: Title, location (file:line), severity (CRITICAL/HIGH/MEDIUM/LOW), agent prompt, type (bug/rule/advisory)
- Pattern: Deduplicated across summary comments and inline comments by matching title

## Entry Points

**qodo-get-rules Skill:**
- Location: `skills/qodo-get-rules/SKILL.md`
- Triggers: `/qodo-get-rules`, `/get-rules`, `/load-rules`, `/fetch-rules`, `/qodo-rules`, `/coding-rules`, and variants
- Responsibilities:
  - Verify git repo and API configuration
  - Fetch all rules with pagination
  - Format and output rules grouped by severity
  - Guide agent on rule application during code generation

**qodo-get-relevant-rules Skill:**
- Location: `skills/qodo-get-relevant-rules/SKILL.md`
- Triggers: `/get-relevant-rules`, `/relevant-rules`, `/search-rules`, `/find-relevant-rules`, `/qodo-relevant`, `/qodo-search-rules`
- Responsibilities:
  - Verify git repo and API configuration
  - Generate structured search queries from coding assignment
  - Search API for top relevant rules
  - Format and output ranked rules
  - Guide agent on rule application

**qodo-pr-resolver Skill:**
- Location: `skills/qodo-pr-resolver/SKILL.md`
- Triggers: `/qodo-pr-resolver`, `/pr-resolver`, `/resolve-pr`, `/qodo-fix`, `/fix-qodo`, `/qodo-review`, `/review-qodo`, `/qodo-issues`, `/show-qodo`, `/get-qodo`
- Responsibilities:
  - Check code push status (uncommitted/unpushed)
  - Detect git provider
  - Find open PR/MR for current branch
  - Fetch and parse Qodo review comments
  - Present issues to user in interactive or auto-fix mode
  - Apply fixes, reply to comments, commit changes
  - Post summary to PR/MR
  - Optionally push to remote

## Error Handling

**Strategy:** Graceful degradation with user-friendly messaging

**Patterns:**

- **Git repository check**: If not in git repo, inform user and exit gracefully (don't attempt code generation)
- **Git remote parsing**: If remote URL cannot be parsed, inform user and exit gracefully
- **Configuration missing**: If API key not found, display setup instructions with config file location and env var alternatives
- **API errors**:
  - HTTP 401/403: Authentication/authorization failed — inform user to check API key
  - HTTP 404: Endpoint not found — inform user and suggest checking environment/ENVIRONMENT_NAME
  - HTTP 5xx: Server error — inform user to try again later
  - Network timeout: Inform user and suggest checking connection
- **No rules found**: Valid result — inform user that no rules are configured for this scope
- **PR/MR not found**: Ask user if they want to create one or exit gracefully
- **Review in progress**: Inform user to wait a few minutes and try again
- **Provider CLI not installed**: Provide installation instructions for the detected provider
- **Empty search results**: Valid in `qodo-get-relevant-rules` — proceed without rule constraints

## Cross-Cutting Concerns

**Logging:** Each skill workflow step is logged via agent's internal logging (no external logging service required)

**Validation:**
- Git repository existence and remote URL validity
- Qodo API configuration presence and format
- HTTP response status codes and JSON structure
- Rule format and required fields
- Provider CLI availability and authentication

**Authentication:**
- Qodo API: Bearer token via API key (`Authorization: Bearer sk-...`)
- Git providers: Provider CLI handles authentication (gh, glab, az, bb manage credentials independently)
- SSH keys: Not used; provider CLIs handle auth internally

**Platform Compatibility:**
- Python 3.6+ for core logic (standard library only, zero external dependencies)
- Bash/Shell for Unix wrappers, `.cmd` for Windows batch wrappers
- Path handling: Python uses `pathlib.Path` (handles `/` vs `\`); URLs always use `/` (converted via `PurePosixPath`)
- Process execution: Agent runtime handles subprocess management and output capture

---

*Architecture analysis: 2026-03-01*

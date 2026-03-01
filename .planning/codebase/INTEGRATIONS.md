# External Integrations

**Analysis Date:** 2026-03-01

## APIs & External Services

**Qodo Platform API:**
- Qodo Rules API - Fetches coding rules and compliance requirements
  - Base URL: `https://qodo-platform.qodo.ai/rules/v1/` (production)
  - Alternate: `https://qodo-platform.{ENVIRONMENT_NAME}.qodo.ai/rules/v1/` (staging/custom)
  - SDK/Client: Python urllib (built-in)
  - Auth: Bearer token (API_KEY from `~/.qodo/config.json` or `QODO_API_KEY` env var)
  - Endpoints used:
    - `GET /rules` - Fetch all rules with pagination support
      - Query params: `scopes`, `state`, `page`, `page_size`
      - Response: Array of rule objects (50 per page)
      - Pagination: Manual iteration from page 1 until < 50 results returned
      - Safety limit: 100 pages maximum (5000 rules max)
    - `POST /rules/search` - Search rules by semantic query
      - Body: `{"query": "<search_query>", "top_k": 20}`
      - Response: Ranked array of rules (most relevant first)
      - Used by: `qodo-get-relevant-rules` skill for targeted rule retrieval

**Qodo Review/PR API:**
- Qodo PR Review Comments - AI-generated code review feedback
  - Accessed via git provider CLIs (GitHub, GitLab, Bitbucket, Azure DevOps)
  - Bot identifiers: `pr-agent-pro`, `pr-agent-pro-staging`, `qodo-merge[bot]`, `qodo-ai[bot]`
  - Used by: `qodo-pr-resolver` skill to fetch and resolve PR issues

## Data Storage

**Databases:**
- None - Skills are stateless and do not use databases
- All data is ephemeral and output to stdout for agent consumption

**File Storage:**
- Local filesystem only
- Configuration: `~/.qodo/config.json` (user home directory)
- No cloud storage integration

**Caching:**
- None - No persistent caching mechanism
- Each skill invocation makes fresh API calls

## Authentication & Identity

**Auth Provider:**
- Qodo Platform API - Custom bearer token auth
  - Implementation: HTTP `Authorization: Bearer {API_KEY}` header
  - Token format: `sk-xxxxxxxxxxxxx` (API key format)
  - Token location: `~/.qodo/config.json` or `QODO_API_KEY` environment variable
  - Scope: Repository-specific rules access via organization/repository scope paths

**Git Provider Auth:**
- GitHub: `gh` CLI authentication (via `gh auth login`)
- GitLab: `glab` CLI authentication (via `glab auth login`)
- Bitbucket: `bb` CLI authentication (built-in or API tokens)
- Azure DevOps: `az` CLI authentication (via `az login`)
- These are used only by `qodo-pr-resolver` to access PR/MR comments

## Monitoring & Observability

**Error Tracking:**
- None - Skills output errors to stdout for agent/user visibility
- Error messages are human-readable and guide users toward resolution

**Logs:**
- Stdout/stderr - All output streams to agent stdout for display
- Status messages: `📋 Loading Qodo rules from API...` (session hook)
- No persistent logging to files or external services

**Tracing:**
- Optional: `TRACE_ID` environment variable for request correlation
  - When set: Included as HTTP header in API requests (`trace_id: {TRACE_ID}`)
  - Purpose: Correlate requests on the platform side for debugging
  - Format: Any string value (typically a UUID)

## CI/CD & Deployment

**Hosting:**
- Agent platforms (not cloud-hosted)
  - Claude Code, Cursor, Windsurf, Cline
  - Installed locally via `npx skills add`

**Distribution:**
- GitHub repository: `qodo-ai/qodo-skills`
- npm skills registry: `npx skills add qodo-ai/qodo-skills`
- Claude Code Marketplace: `qodo-skills@claude-plugins-official`

**CI Pipeline:**
- None detected - Skills use manual testing and deployment via git

## Environment Configuration

**Required env vars:**
- `QODO_API_KEY` - Qodo platform API key (required to fetch rules)
  - Format: `sk-xxxxxxxxxxxxx`
  - Priority: Overrides value in `~/.qodo/config.json`
  - Get from: https://app.qodo.ai/account/api-keys

**Optional env vars:**
- `QODO_ENVIRONMENT_NAME` - API environment for staging/custom deployments
  - Default: Uses production endpoint (`qodo-platform.qodo.ai`)
  - Priority: Overrides value in `~/.qodo/config.json`
- `TRACE_ID` - Request tracing ID for platform-side correlation
  - Optional; skipped silently if not set

**Secrets location:**
- Config file: `~/.qodo/config.json` (user home directory, not committed to git)
- Environment variables (preferred for CI/CD scenarios)
- `.gitignore` pattern: Prevents accidental commit of config files

## Webhooks & Callbacks

**Incoming:**
- Session start hook (Claude plugin)
  - Trigger: `startup|resume` matcher
  - Action: Auto-execute rule fetching at session start
  - Timeout: 30 seconds
  - File: `hooks.json` (Claude plugin configuration)

**Outgoing:**
- None - Skills do not initiate outbound webhooks
- All integration is request/response based

## API Request Headers

**Standard Headers:**
- `Authorization: Bearer {API_KEY}` - Bearer token authentication
- `Content-Type: application/json` - JSON request/response format
- `request-id: {REQUEST_ID}` - UUID for request correlation across paginated calls
- `qodo-client-type: skill-{SKILL_NAME}` - Identifies which skill made the request
  - Values: `skill-qodo-get-rules`, `skill-qodo-get-relevant-rules`
- `trace_id: {TRACE_ID}` - Optional tracing ID when `TRACE_ID` env var is set

## Rate Limiting & Quotas

**API Rate Limits:**
- Not documented in codebase
- Error handling for `429` (rate limit exceeded) with graceful exit message
- Exponential backoff: Not implemented (single request per page)

**Safety Limits:**
- Pagination: Maximum 100 pages per rule fetch (5000 rules safety limit)
- Search: `top_k=20` per query (2 queries total for cross-cutting retrieval)
- Timeout: 30 seconds per API request

---

*Integration audit: 2026-03-01*

---
name: get-rules
description: "Fetch and load repository coding rules from Qodo API. MUST be invoked at conversation start before any code generation or modification task, if rules are not already loaded in context."
version: 1.0.0
allowed-tools: ["Bash", "Read"]
triggers:
  - "get.?rules"
  - "load.?rules"
  - "fetch.?rules"
  - "qodo.?rules"
  - "coding.?rules"
  - "code.?rules"
  - "before.?cod"
  - "start.?coding"
  - "write.?code"
  - "implement"
  - "create.*code"
  - "build.*feature"
  - "add.*feature"
  - "fix.*bug"
  - "refactor"
  - "modify.*code"
  - "update.*code"
---

# Get Rules Skill

## Description

Fetches repository-specific coding rules from the Qodo platform API before code generation or modification tasks. Rules include security requirements, coding standards, quality guidelines, and team conventions that must be applied during code generation.

**When to invoke**: At conversation start before any coding task, if rules not already loaded in context.

## Key Features

- **Automatic loading**: Runs at conversation start without user prompt
- **Repository-aware**: Infers repository from git remote URL
- **Context-aware scopes**: Automatically detects module-level rules based on working directory
- **Hierarchical rule matching**: Returns universal, repository-level, and path-level rules
- **Severity-based enforcement**: ERROR (must comply), WARNING (should comply), RECOMMENDATION (consider)
- **Transparent feedback**: Always informs user about rule loading status and application
- **Graceful degradation**: Continues without rules if API unavailable or not configured

## How Scope Levels Work

The skill automatically determines the most specific scope based on your current working directory and fetches matching rules at all hierarchy levels.

**Scope Hierarchy** (as defined in codebase):
- **Universal** (`/`) - applies everywhere
- **Org Level** (`/org/`) - applies to organization
- **Repo Level** (`/org/repo/`) - applies to repository
- **Path Level** (`/org/repo/path/`) - applies to specific paths

**Automatic Detection**:
- Working in module directory (e.g., `modules/rules/`) → queries with path-level scope
- Working at repository root → queries with repo-level scope
- API automatically returns all matching parent scopes via prefix matching

**Example**: Query `/codium-ai/qodo-platform/modules/rules/` returns:
- Universal rules (`/`)
- Org level rules (`/codium-ai/`)
- Repo level rules (`/codium-ai/qodo-platform/`)
- Path level rules (`/codium-ai/qodo-platform/modules/rules/`)

## Workflow

### Step 1: Check if Rules Already Loaded

**CRITICAL - Before ANY code generation, modification, or review task**, check if rules are already in context:
- Look for "📋 Qodo Rules Loaded" in conversation history
- If found: Skip execution, rules are active - proceed with coding task
- If NOT found: Execute this skill immediately before proceeding

**This check is mandatory for all coding tasks.** Rules must be loaded to ensure code complies with organizational standards.

### Step 2: Execute the Fetch Script

**When the skill is invoked, you'll see the base directory path for this skill's installation.**

**Use the platform-appropriate wrapper for cross-platform reliability:**

**For macOS/Linux** (platform: darwin, linux):
```bash
bash ${SKILL_BASE_DIR}/scripts/fetch-qodo-rules.sh
```

**For Windows** (platform: win32):
```
${SKILL_BASE_DIR}\scripts\fetch-qodo-rules.cmd
```

Replace `${SKILL_BASE_DIR}` with the actual skill installation directory path.

**Platform detection**: Agents have access to platform information in their environment (e.g., "Platform: darwin"). Use this to select the correct wrapper automatically.

**If wrappers fail, fallback to Python directly:**
```bash
# Try python3 first (most systems)
python3 ${SKILL_BASE_DIR}/scripts/fetch-qodo-rules.py

# If python3 not found (exit code 127), try python
python ${SKILL_BASE_DIR}/scripts/fetch-qodo-rules.py
```

**The wrapper/script automatically handles:**
- ✅ Python version detection (python3 vs python)
- ✅ Git repository detection
- ✅ API key from QODO_API_KEY env var or ~/.qodo/config.json
- ✅ Repository scope extraction from git remote URL
- ✅ Working directory scope detection (module-specific vs repository-wide)
- ✅ Rules fetching from Qodo API
- ✅ Formatting by severity (ERROR/WARNING/RECOMMENDATION)
- ✅ Graceful error handling with user-friendly messages
- ✅ Cross-platform compatibility

**Script Output:**
The output automatically becomes conversation context:
- Repository scope
- Total rule count
- Rules grouped by severity with descriptions
- User-friendly error messages if API unavailable

**No additional processing needed** - the output is ready to use.

### Step 3: Apply Rules During Code Generation

**When generating or modifying code**, enforce rules based on severity:

#### ERROR Rules (Must Comply)
- Apply strictly and non-negotiably
- Add comment documenting compliance:
  ```python
  # Following Qodo rule: No Hardcoded Credentials
  api_key = os.environ.get("API_KEY")
  ```
- If cannot satisfy: Explain to user and ask for guidance

#### WARNING Rules (Should Comply)
- Apply preferentially unless strong reason not to
- No documentation needed (apply silently)
- If skipping: Briefly explain why in response

#### RECOMMENDATION Rules (Consider)
- Consider as helpful suggestions
- Apply when appropriate, ignore when not
- No documentation needed

### Step 4: Provide Feedback on Rule Application

**After code generation**, inform the user about rule application:

**If ERROR rules were applied**:
- List which ERROR rules were followed: `"I followed these Qodo rules: [rule names]"`

**If WARNING rules were skipped**:
- Explain: `"I didn't apply the '{rule_name}' rule because {reason}"`

**If no rules were applicable**:
- Inform: `"No Qodo rules were applicable to this code change"`

**RECOMMENDATION rules**: Mention only if specifically relevant or if they influenced a design decision

---

## Examples

### Typical Session Flow

```bash
# Session starts - Claude checks for rules
[Checking conversation history for "📋 Qodo Rules Loaded"...]
[Not found - invoking /get-rules]

# Rules load successfully
📋 Qodo Rules Loaded

Repository: `/my-org/my-repo/`
Rules loaded: 15 (universal, org level, repo level)

# Now coding can proceed with rules applied
```

### When Working in a Module

```bash
# Working in modules/api/ directory
cd modules/api

# Running get-rules detects module-specific scope
/get-rules

# Output includes path-level rules
📋 Qodo Rules Loaded

Repository: `/my-org/my-repo/`
Module: `modules/api`
Rules loaded: 18 (includes path-level rules for modules/api/)
```

### Natural Language Invocation

The skill responds to various coding-related phrases:
- "Let's implement a new feature" → Auto-invokes get-rules
- "I need to write some code" → Auto-invokes get-rules
- "Please fix this bug" → Auto-invokes get-rules
- "Can you refactor this?" → Auto-invokes get-rules

---

## Configuration

The script automatically reads configuration from:

**Config file**: `~/.qodo/config.json`
```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx",
  "ENVIRONMENT_NAME": "staging"
}
```

**Configuration fields:**
- `API_KEY` (required): Your Qodo API key
- `ENVIRONMENT_NAME` (optional): Environment name for API URL
  - If empty/omitted: Uses production (`https://qodo-platform.qodo.ai/rules/v1/`)
  - If specified: Uses `https://qodo-platform.<ENVIRONMENT_NAME>.qodo.ai/rules/v1/`

**Environment variables** (take precedence over config file):
```bash
export QODO_API_KEY="sk-xxxxxxxxxxxxx"
export QODO_ENVIRONMENT_NAME="staging"  # optional
```

**Minimal config** (production environment):
```json
{
  "API_KEY": "sk-xxxxxxxxxxxxx"
}
```

Get your API key at: https://app.qodo.ai/settings/api-keys

---

## Error Handling

The script handles all errors gracefully and provides user-friendly messages:
- ✅ Not in git repo → Silent exit (no error)
- ✅ No API key → Helpful message with setup instructions
- ✅ Invalid API key → Message with link to API key settings
- ✅ API unavailable → Generic error message
- ✅ No rules found → Informational message

**All errors are non-fatal** - the script always exits cleanly so the session continues without rules.

---

## Troubleshooting

**Rules not loading?**
- Check: `cat ~/.qodo/config.json` (verify API key)
- Test: `python3 ~/.claude/skills/get-rules/scripts/fetch-qodo-rules.py`
- Verify: `git status` (must be in git repository)

**Wrong scope?**
- Module detection requires `modules/` directory structure
- Check remote: `git config --get remote.origin.url`

**API issues?**
- Verify key at: https://app.qodo.ai/settings/api-keys
- Test connectivity: `curl -I https://qodo-platform.qodo.ai/rules/v1/health`

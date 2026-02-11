#!/bin/bash
# Fetch Qodo rules and output them as context for Claude
# This script's stdout becomes part of Claude's context automatically

set -euo pipefail

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0  # Not in a git repo, exit silently
fi

# Check for API key and URL from config file or environment
if [ -f "$HOME/.qodo/config.json" ]; then
    API_KEY=$(jq -r '.QODO_CLI_API_KEY // .api_key // empty' "$HOME/.qodo/config.json" 2>/dev/null || echo "")
    API_URL=$(jq -r '.QODO_RULES_API_URL // empty' "$HOME/.qodo/config.json" 2>/dev/null || echo "")
fi

# Environment variables take precedence
API_KEY="${QODO_CLI_API_KEY:-$API_KEY}"
API_URL="${QODO_RULES_API_URL:-$API_URL}"

# Default API URL if not set
if [ -z "$API_URL" ]; then
    API_URL="https://api.qodo.ai"
fi

# Remove trailing slash from API_URL if present
API_URL="${API_URL%/}"

if [ -z "$API_KEY" ]; then
    echo "ℹ️  No Qodo API key configured. To enable repository-specific coding rules, set the QODO_CLI_API_KEY environment variable or create ~/.qodo/config.json"
    echo "Get your API key at: https://app.qodo.ai/settings/api-keys"
    exit 0
fi

# Extract repository from git remote
REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    exit 0  # No git remote, exit silently
fi

# Parse repository scope from remote URL
# Examples:
#   git@github.com:org/repo.git -> /org/repo/
#   https://github.com/org/repo.git -> /org/repo/
REPO_SCOPE=$(echo "$REMOTE_URL" | sed -E 's|^.*[:/]([^/]+/[^/]+)\.git$|/\1/|')

if [ -z "$REPO_SCOPE" ] || [ "$REPO_SCOPE" = "$REMOTE_URL" ]; then
    echo "⚠️  Could not parse repository from git remote: $REMOTE_URL"
    exit 0
fi

# Detect module-specific scope based on current working directory
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$REPO_ROOT" ]; then
    CWD=$(pwd)
    REL_PATH="${CWD#$REPO_ROOT/}"

    # Check if we're in a module directory (modules/*)
    if [[ "$REL_PATH" == modules/* ]] && [ "$REL_PATH" != "$CWD" ]; then
        # Extract module path: modules/rules/src/service.py → modules/rules
        MODULE_PATH=$(echo "$REL_PATH" | sed -E 's|(modules/[^/]+).*|\1|')

        # Build module-specific scope
        QUERY_SCOPE="${REPO_SCOPE}${MODULE_PATH}/"
        SCOPE_CONTEXT="Module: \`$MODULE_PATH\`"
    else
        # Use repository-level scope
        QUERY_SCOPE="$REPO_SCOPE"
        SCOPE_CONTEXT="Scope: Repository-wide"
    fi
else
    # Fallback to repository scope if we can't determine repo root
    QUERY_SCOPE="$REPO_SCOPE"
    SCOPE_CONTEXT="Scope: Repository-wide"
fi

# Fetch all rules from API with pagination
# API enforces max 50 rules per page, so we need to loop through pages
ALL_RULES="[]"
PAGE=1
PAGE_SIZE=50

while true; do
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $API_KEY" \
        "${API_URL}/rules/v1/rules?scopes=${QUERY_SCOPE}&state=active&page=${PAGE}&page_size=${PAGE_SIZE}" 2>&1)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    # Handle API errors
    if [ "$HTTP_CODE" != "200" ]; then
        if [ "$HTTP_CODE" = "401" ]; then
            echo "⚠️  Invalid or expired Qodo API key. Please check your API key at https://app.qodo.ai/settings/api-keys"
        elif [ "$HTTP_CODE" = "000" ]; then
            echo "⚠️  Could not connect to Qodo API at ${API_URL}"
        else
            echo "⚠️  Failed to fetch Qodo rules (HTTP $HTTP_CODE)"
        fi
        exit 0
    fi

    # Extract rules from this page
    PAGE_RULES=$(echo "$BODY" | jq -r '.rules' 2>/dev/null || echo "[]")
    PAGE_COUNT=$(echo "$PAGE_RULES" | jq 'length')

    # Append this page's rules to all rules
    ALL_RULES=$(echo "$ALL_RULES" | jq --argjson page_rules "$PAGE_RULES" '. + $page_rules')

    # If we got fewer than PAGE_SIZE rules, we've reached the last page
    if [ "$PAGE_COUNT" -lt "$PAGE_SIZE" ]; then
        break
    fi

    # Move to next page
    PAGE=$((PAGE + 1))
done

# Count total rules fetched
RULE_COUNT=$(echo "$ALL_RULES" | jq 'length')

if [ "$RULE_COUNT" = "0" ]; then
    echo "ℹ️  No Qodo rules configured for repository: $REPO_SCOPE"
    exit 0
fi

# Output formatted rules as context for Claude
echo "# 📋 Qodo Rules Loaded"
echo ""
echo "Repository: \`$REPO_SCOPE\`"
echo "$SCOPE_CONTEXT"
echo "Rules loaded: **$RULE_COUNT** (universal, org level, repo level, and path level rules)"
echo ""
echo "These rules must be applied during code generation based on severity:"
echo ""

# Format ERROR rules (must comply)
ERROR_RULES=$(echo "$ALL_RULES" | jq -r '.[] | select(.severity == "error")' 2>/dev/null)
if [ -n "$ERROR_RULES" ]; then
    ERROR_COUNT=$(echo "$ERROR_RULES" | jq -s 'length')
    echo "## ❌ ERROR Rules (Must Comply) - $ERROR_COUNT"
    echo ""
    echo "$ERROR_RULES" | jq -r '"- **\(.name)** (\(.category)): \(.description)"'
    echo ""
fi

# Format WARNING rules (should comply)
WARNING_RULES=$(echo "$ALL_RULES" | jq -r '.[] | select(.severity == "warning")' 2>/dev/null)
if [ -n "$WARNING_RULES" ]; then
    WARNING_COUNT=$(echo "$WARNING_RULES" | jq -s 'length')
    echo "## ⚠️  WARNING Rules (Should Comply) - $WARNING_COUNT"
    echo ""
    echo "$WARNING_RULES" | jq -r '"- **\(.name)** (\(.category)): \(.description)"'
    echo ""
fi

# Format RECOMMENDATION rules (consider)
REC_RULES=$(echo "$ALL_RULES" | jq -r '.[] | select(.severity == "recommendation")' 2>/dev/null)
if [ -n "$REC_RULES" ]; then
    REC_COUNT=$(echo "$REC_RULES" | jq -s 'length')
    echo "## 💡 RECOMMENDATION Rules (Consider) - $REC_COUNT"
    echo ""
    echo "$REC_RULES" | jq -r '"- **\(.name)** (\(.category)): \(.description)"'
    echo ""
fi

echo "---"
echo ""

exit 0

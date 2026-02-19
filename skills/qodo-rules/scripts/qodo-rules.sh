#!/bin/bash
# qodo-rules.sh — CRUD for Qodo coding rules
#
# Usage:
#   qodo-rules.sh --get                              (download rules as local IDE rule files)
#   qodo-rules.sh --prompt "<description>"           (generate rule JSON from prompt)
#   qodo-rules.sh --create [--scope "/org/repo/"]    (reads JSON from stdin)
#   qodo-rules.sh --update <rule_id>                 (reads JSON from stdin)
#   qodo-rules.sh --delete <rule_id>

set -euo pipefail

command -v jq &>/dev/null || { echo "Error: jq is required" >&2; exit 1; }

# --- Argument parsing ---
MODE="" SCOPE_OVERRIDE="" RULE_ID="" PROMPT_TEXT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --get)     MODE="get";  shift ;;
        --prompt)  MODE="prompt"; [ -z "${2:-}" ] && { echo "Error: --prompt requires a description" >&2; exit 1; }; PROMPT_TEXT="$2"; shift 2 ;;
        --create)  MODE="create"; shift ;;
        --update)  MODE="update"; [ -z "${2:-}" ] && { echo "Error: --update requires a rule ID" >&2; exit 1; }; RULE_ID="$2"; shift 2 ;;
        --delete)  MODE="delete"; [ -z "${2:-}" ] && { echo "Error: --delete requires a rule ID" >&2; exit 1; }; RULE_ID="$2"; shift 2 ;;
        --scope)   [ -z "${2:-}" ] && { echo "Error: --scope requires a path" >&2; exit 1; }; SCOPE_OVERRIDE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -z "$MODE" ] && { echo "Usage: qodo-rules.sh --get | --prompt <desc> | --create | --update <id> | --delete <id>"; exit 1; }

# --- Prerequisites ---
for cmd in curl git; do
    command -v "$cmd" &>/dev/null || { echo "Error: $cmd is required" >&2; exit 1; }
done

# --- Auth ---
[ -f "$HOME/.qodo/skill_auth.json" ] || { echo "ℹ️  Not authenticated. Run: /qodo-setup --login" >&2; exit 1; }
_auth=$(cat "$HOME/.qodo/skill_auth.json")
API_KEY=$(echo "$_auth" | jq -r '.id_token // empty')
API_URL=$(echo "$_auth" | jq -r '.platform_url // empty')
[ -z "$API_URL" ] && API_URL="https://qodo-platform.qodo.ai"
API_URL="${API_URL%/}"

[ -z "$API_KEY" ] && { echo "ℹ️  Not authenticated. Run: /qodo-setup --login" >&2; exit 1; }

# --- API call helper ---
# call <METHOD> <path> [extra curl args]
call() {
    local method="$1" path="$2"; shift 2
    curl -s -w "\n%{http_code}" -X "$method" -H "Authorization: Bearer $API_KEY" "$@" "${API_URL}${path}" 2>/dev/null
}
code() { echo "$1" | tail -n1; }
body() { echo "$1" | sed '$d'; }

# --- Scope detection ---
detect_scope() {
    if [ -n "$SCOPE_OVERRIDE" ]; then
        QUERY_SCOPE="$SCOPE_OVERRIDE"; SCOPE_CONTEXT="Custom scope"; return
    fi
    local remote; remote=$(git config --get remote.origin.url 2>/dev/null || echo "")
    [ -z "$remote" ] && { echo "Error: No git remote" >&2; return 1; }
    QUERY_SCOPE=$(echo "$remote" | sed -E 's|\.git$||' | sed -E 's|^.*[:/]([^/]+/[^/]+)$|/\1/|')
    [ -z "$QUERY_SCOPE" ] || [ "$QUERY_SCOPE" = "$remote" ] && { echo "Error: Could not parse scope from git remote" >&2; return 1; }
    SCOPE_CONTEXT="Repository"
    local root; root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    if [ -n "$root" ]; then
        local rel="${PWD#"$root"/}"
        if [[ "$rel" == modules/* ]] && [ "$rel" != "$PWD" ]; then
            local mod; mod=$(echo "$rel" | cut -d'/' -f1-2)
            QUERY_SCOPE="${QUERY_SCOPE}${mod}/"
            SCOPE_CONTEXT="Module: \`${mod}\`"
        fi
    fi
}

# --- Get: download rules as local IDE rule files ---
if [ "$MODE" = "get" ]; then
    detect_scope || { echo "⚠️  Could not detect scope. Skipping rules get."; exit 0; }

    # Determine rules directory: project root if in a git repo, else user home
    GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    BASE_DIR="${GIT_ROOT:-$HOME}"

    RULES_DIR="" RULES_EXT="" IDE_NAME=""
    if [ -d "${BASE_DIR}/.cursor" ] || [ -n "${CURSOR_TRACE_ID:-}" ]; then
        RULES_DIR="${BASE_DIR}/.cursor/rules"
        RULES_EXT=".mdc"
        IDE_NAME="Cursor"
    else
        RULES_DIR="${BASE_DIR}/.claude/rules"
        RULES_EXT=".md"
        IDE_NAME="Claude"
    fi

    ALL_RULES="[]"; PAGE=1; PAGE_SIZE=50
    while true; do
        ENC=$(printf '%s' "$QUERY_SCOPE" | jq -Rr @uri)
        set +e; R=$(call GET "/rules/v1/rules?scopes=${ENC}&state=active&page=${PAGE}&page_size=${PAGE_SIZE}"); EC=$?; set -e
        [ $EC -ne 0 ] && { echo "⚠️  Network error" >&2; exit 1; }
        C=$(code "$R"); B=$(body "$R")
        [ "$C" = "401" ] && { echo "⚠️  Token expired. Run: /qodo-setup --login" >&2; exit 1; }
        [ "$C" != "200" ] && { echo "⚠️  Failed to get rules (HTTP $C)" >&2; exit 1; }
        PAGE_RULES=$(echo "$B" | jq '.rules // []')
        ALL_RULES=$(echo "$ALL_RULES $PAGE_RULES" | jq -s '.[0] + .[1]')
        COUNT=$(echo "$PAGE_RULES" | jq 'length')
        [ "$COUNT" -lt "$PAGE_SIZE" ] && break
        PAGE=$((PAGE + 1))
    done

    TOTAL=$(echo "$ALL_RULES" | jq 'length')
    [ "$TOTAL" -eq 0 ] && { echo "ℹ️  No rules for: ${QUERY_SCOPE}"; exit 0; }

    mkdir -p "$RULES_DIR"

    # Remove previously synced qodo rules
    for old_file in "$RULES_DIR"/qodo-*"${RULES_EXT}"; do
        [ -f "$old_file" ] && rm "$old_file"
    done

    echo "$ALL_RULES" | jq -c '.[]' | while IFS= read -r rule; do
        NAME=$(echo "$rule" | jq -r '.name')
        SEVERITY=$(echo "$rule" | jq -r '.severity // "recommendation"')
        CATEGORY=$(echo "$rule" | jq -r '.category // ""')
        CONTENT=$(echo "$rule" | jq -r '.content // .description // ""')
        DESCRIPTION=$(echo "$rule" | jq -r '.description // .name')
        GOOD_EXAMPLES=$(echo "$rule" | jq -r 'if .goodExamples and .goodExamples != "" then .goodExamples else empty end')
        BAD_EXAMPLES=$(echo "$rule" | jq -r 'if .badExamples and .badExamples != "" then .badExamples else empty end')

        SLUG=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')
        FILEPATH="${RULES_DIR}/qodo-${SLUG}${RULES_EXT}"

        {
            if [ "$IDE_NAME" = "Cursor" ]; then
                echo "---"
                echo "description: ${DESCRIPTION}"
                echo "alwaysApply: true"
                echo "---"
                echo ""
            fi
            echo "# ${NAME}"
            echo ""
            SEVERITY_UPPER=$(echo "$SEVERITY" | tr '[:lower:]' '[:upper:]')
            echo "**Severity:** ${SEVERITY_UPPER} | **Category:** ${CATEGORY}"
            echo ""
            echo "${CONTENT}"
            if [ -n "${GOOD_EXAMPLES:-}" ]; then
                echo ""
                echo "## Good Examples"
                echo ""
                echo "${GOOD_EXAMPLES}"
            fi
            if [ -n "${BAD_EXAMPLES:-}" ]; then
                echo ""
                echo "## Bad Examples"
                echo ""
                echo "${BAD_EXAMPLES}"
            fi
        } > "$FILEPATH"

        echo "  ✓ ${NAME} → qodo-${SLUG}${RULES_EXT}"
    done

    echo ""
    echo "Synced ${TOTAL} Qodo rules to ${RULES_DIR}/ (${IDE_NAME} format)"
    exit 0
fi

# --- Prompt to Rule ---
if [ "$MODE" = "prompt" ]; then
    J=$(jq -n --arg p "$PROMPT_TEXT" '{prompt: $p}')
    R=$(call POST "/rules/v1/prompt-to-rule" -H "Content-Type: application/json" -d "$J")
    C=$(code "$R"); B=$(body "$R")
    [ "$C" != "200" ] && { echo "Error: Failed to generate rule (HTTP $C)" >&2; echo "$B" >&2; exit 1; }
    echo "$B"; exit 0
fi

# --- Create ---
if [ "$MODE" = "create" ]; then
    detect_scope || { echo "Error: Could not detect scope" >&2; exit 1; }
    J=$(cat | jq --arg s "$QUERY_SCOPE" '. + {scopes: [$s]}')
    R=$(call POST "/rules/v1/rule" -H "Content-Type: application/json" -d "$J")
    C=$(code "$R"); B=$(body "$R")
    [ "$C" != "201" ] && { echo "Error: Failed to create rule (HTTP $C)" >&2; echo "$B" >&2; exit 1; }
    echo "$B"; exit 0
fi

# --- Update ---
if [ "$MODE" = "update" ]; then
    J=$(cat)
    [ -n "$SCOPE_OVERRIDE" ] && J=$(echo "$J" | jq --arg s "$SCOPE_OVERRIDE" '. + {scopes: [$s]}')
    R=$(call PUT "/rules/v1/rule/${RULE_ID}" -H "Content-Type: application/json" -d "$J")
    C=$(code "$R"); B=$(body "$R")
    [ "$C" != "200" ] && { echo "Error: Failed to update rule (HTTP $C)" >&2; echo "$B" >&2; exit 1; }
    echo "$B"; exit 0
fi

# --- Delete ---
if [ "$MODE" = "delete" ]; then
    R=$(call DELETE "/rules/v1/rule/${RULE_ID}")
    C=$(code "$R")
    [ "$C" != "204" ] && { echo "Error: Failed to delete rule (HTTP $C)" >&2; body "$R" >&2; exit 1; }
    echo "Rule ${RULE_ID} deleted"; exit 0
fi

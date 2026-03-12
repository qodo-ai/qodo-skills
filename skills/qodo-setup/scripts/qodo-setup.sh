#!/bin/bash
# qodo-setup.sh — Qodo platform authentication via OIDC
#
# Usage:
#   qodo-setup.sh --check              # Check if authenticated (auto-refreshes if expired)
#   qodo-setup.sh --login              # Interactive browser login
#   qodo-setup.sh --set-token <token>  # Set JWT token manually
#   qodo-setup.sh --clear              # Clear stored token

set -euo pipefail

CONFIG_DIR="$HOME/.qodo"
AUTH_FILE="$CONFIG_DIR/skill_auth.json"
API_URL="${QODO_PLATFORM_URL:-https://qodo-platform.qodo.ai}"
API_URL="${API_URL%/}"

MODE=""
TOKEN_VALUE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --check) MODE="check"; shift ;;
        --login) MODE="login"; shift ;;
        --set-token)
            MODE="set-token"
            if [ -z "${2:-}" ]; then echo "Error: --set-token requires a JWT token" >&2; exit 1; fi
            TOKEN_VALUE="$2"; shift 2 ;;
        --clear) MODE="clear"; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$MODE" ]; then
    echo "Usage: qodo-setup.sh --check | --login | --set-token <token> | --clear"
    exit 1
fi

# --- Helpers ---

generate_trace_id() {
    if command -v uuidgen &>/dev/null; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    else
        python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || echo "$(date +%s)-$RANDOM"
    fi
}

decode_jwt_payload() {
    local token="$1"
    [[ "$token" =~ ^[^.]+\.[^.]+\.[^.]+$ ]] || return 1
    local payload padded
    payload=$(echo "$token" | cut -d'.' -f2)
    padded="$payload"
    case $((${#payload} % 4)) in
        2) padded="${payload}==" ;;
        3) padded="${payload}=" ;;
    esac
    echo "$padded" | tr '_-' '/+' | { base64 --decode 2>/dev/null || base64 -D 2>/dev/null; } || return 1
}

save_tokens() {
    local id_token="$1" refresh_token="${2:-}" expires_at="$3" platform_url="${4:-}"
    mkdir -p "$CONFIG_DIR" && chmod 700 "$CONFIG_DIR"
    jq -n \
        --arg id "$id_token" \
        --arg rt "$refresh_token" \
        --arg url "$platform_url" \
        --argjson exp "$expires_at" \
        --argjson now "$(date +%s)" \
        '{id_token: $id, refresh_token: $rt, platform_url: $url, expires_at: $exp, updated_at: $now}' \
        > "$AUTH_FILE"
    chmod 600 "$AUTH_FILE"
}

detect_platform_url() {
    local token="$1"
    local response http_code body
    response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $token" "${API_URL}/rules/v1/rules?page=1&page_size=1" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "409" ]; then
        local redirect_url base_url platform_url verify_code
        redirect_url=$(echo "$body" | jq -r '.detail.redirectTo // empty' 2>/dev/null || echo "")
        if [ -n "$redirect_url" ]; then
            base_url=$(echo "$redirect_url" | sed 's|^\(https\{0,1\}://[^/]*\).*|\1|')
            platform_url=$(echo "$base_url" | sed 's|://app\.|://qodo-platform.|')
            verify_code=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "Authorization: Bearer $token" \
                "${platform_url}/rules/v1/rules?page=1&page_size=1" 2>/dev/null)
            [ "$verify_code" = "200" ] && echo "$platform_url" && return 0
        fi
    fi

    echo "$API_URL"
}

# --- Check mode ---
if [ "$MODE" = "check" ]; then
    [ -f "$AUTH_FILE" ] || exit 1
    auth_data=$(cat "$AUTH_FILE" 2>/dev/null || echo "")
    [ -n "$auth_data" ] || exit 1

    id_token=$(echo "$auth_data" | jq -r '.id_token // empty' 2>/dev/null || echo "")
    expires_at=$(echo "$auth_data" | jq -r '.expires_at // 0' 2>/dev/null || echo "0")
    now=$(date +%s)

    # Token still valid (5-minute buffer)
    [ -n "$id_token" ] && [ "$now" -lt "$((expires_at - 300))" ] && exit 0

    # Token expired — attempt refresh
    refresh_token=$(echo "$auth_data" | jq -r '.refresh_token // empty' 2>/dev/null || echo "")
    [ -z "$refresh_token" ] && exit 1

    response=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}/auth/v1/oidc/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "grant_type=refresh_token" \
        --data-urlencode "refresh_token=${refresh_token}" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    [ "$http_code" != "200" ] && exit 1

    new_id_token=$(echo "$body" | jq -r '.id_token // empty')
    new_refresh_token=$(echo "$body" | jq -r '.refresh_token // empty')
    new_expires_in=$(echo "$body" | jq -r '.expires_in // 3600')
    existing_platform_url=$(echo "$auth_data" | jq -r '.platform_url // empty' 2>/dev/null || echo "")
    [ -z "$existing_platform_url" ] && existing_platform_url="https://qodo-platform.qodo.ai"

    [ -z "$new_id_token" ] && exit 1
    [ -z "$new_refresh_token" ] && new_refresh_token="$refresh_token"

    save_tokens "$new_id_token" "$new_refresh_token" "$((now + new_expires_in))" "$existing_platform_url"
    exit 0
fi

# --- Clear mode ---
if [ "$MODE" = "clear" ]; then
    rm -f "$AUTH_FILE"
    echo "✓ Authentication cleared"
    exit 0
fi

# --- Login mode (OIDC flow) ---
if [ "$MODE" = "login" ]; then
    TRACE_ID=$(generate_trace_id)

    init_response=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}/auth/v1/oidc/init_login" \
        -H "Content-Type: application/json" \
        -H "Qodo-Client-Type: skill" \
        -d "{\"trace_id\": \"$TRACE_ID\", \"init_client\": \"command\"}" 2>/dev/null)

    http_code=$(echo "$init_response" | tail -n1)
    response_body=$(echo "$init_response" | sed '$d')

    if [ "$http_code" != "200" ]; then
        echo "Error: Failed to initialize login (HTTP $http_code)" >&2
        echo "$response_body" >&2
        exit 1
    fi

    login_url=$(echo "$response_body" | jq -r '.login_url // empty')
    session_id=$(echo "$response_body" | jq -r '.session_id // empty')
    poll_delay=$(echo "$response_body" | jq -r '.poll_delay // 2')
    poll_interval=$(echo "$response_body" | jq -r '.poll_interval // 2')
    poll_timeout=$(echo "$response_body" | jq -r '.poll_timeout // 300')

    if [ -z "$login_url" ] || [ -z "$session_id" ]; then
        echo "Error: Invalid init_login response" >&2; exit 1
    fi

    echo "Opening browser: $login_url"
    if command -v xdg-open &>/dev/null; then xdg-open "$login_url" &>/dev/null
    elif command -v open &>/dev/null; then open "$login_url" &>/dev/null
    else echo "Please open this URL manually: $login_url"; fi

    echo -n "Waiting for authentication"
    sleep "$poll_delay"

    attempt=1
    max_attempts=$((poll_timeout / poll_interval))

    while [ $attempt -le $max_attempts ]; do
        poll_response=$(curl -s -w "\n%{http_code}" \
            -X POST "${API_URL}/auth/v1/oidc/poll_token" \
            -H "Content-Type: application/json" \
            -H "Qodo-Client-Type: skill" \
            -H "X-Request-Attempt: $attempt" \
            -d "{\"trace_id\": \"$TRACE_ID\", \"session_id\": \"$session_id\"}" 2>/dev/null)

        poll_http_code=$(echo "$poll_response" | tail -n1)
        poll_body=$(echo "$poll_response" | sed '$d')

        if [ "$poll_http_code" = "200" ]; then
            id_token=$(echo "$poll_body" | jq -r '.id_token // empty')
            refresh_token=$(echo "$poll_body" | jq -r '.refresh_token // empty')
            expires_in=$(echo "$poll_body" | jq -r '.expires_in // 3600')

            [ -z "$id_token" ] && { echo "" && echo "Error: No id_token in response" >&2; exit 1; }

            now=$(date +%s)
            payload=$(decode_jwt_payload "$id_token" 2>/dev/null || echo "")
            email=$(echo "$payload" | jq -r '.email // empty' 2>/dev/null || echo "")

            echo ""
            detected_url=$(detect_platform_url "$id_token")
            save_tokens "$id_token" "$refresh_token" "$((now + expires_in))" "$detected_url"

            echo "✓ Authenticated"
            [ -n "$email" ] && echo "  Email: $email"
            echo "  Platform URL: $detected_url"
            echo "  Token expires in: $((expires_in / 3600)) hours"
            exit 0

        elif [ "$poll_http_code" = "202" ]; then
            echo -n "."
            sleep "$poll_interval"
            attempt=$((attempt + 1))
        else
            echo ""
            echo "Error: Polling failed (HTTP $poll_http_code)" >&2
            echo "$poll_body" >&2
            exit 1
        fi
    done

    echo "" && echo "Error: Authentication timeout" >&2; exit 1
fi

# --- Set token mode ---
if [ "$MODE" = "set-token" ]; then
    [[ "$TOKEN_VALUE" =~ ^[^.]+\.[^.]+\.[^.]+$ ]] || {
        echo "Error: Invalid JWT format (expected header.payload.signature)" >&2; exit 1
    }

    payload=$(decode_jwt_payload "$TOKEN_VALUE" 2>/dev/null || echo "")
    [ -z "$payload" ] && { echo "Error: Failed to decode JWT" >&2; exit 1; }

    exp=$(echo "$payload" | jq -r '.exp // empty' 2>/dev/null || echo "")
    email=$(echo "$payload" | jq -r '.email // empty' 2>/dev/null || echo "")
    [ -z "$exp" ] && { echo "Error: JWT missing expiration" >&2; exit 1; }

    detected_url=$(detect_platform_url "$TOKEN_VALUE")
    save_tokens "$TOKEN_VALUE" "" "$exp" "$detected_url"

    echo "✓ Token saved"
    [ -n "$email" ] && echo "  Email: $email"
    echo "  Platform URL: $detected_url"
    echo "  Token expires in: $(( (exp - $(date +%s)) / 3600 )) hours"
    exit 0
fi

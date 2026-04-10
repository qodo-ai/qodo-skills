#!/usr/bin/env bash
# E2E assertion script for qodo-pr-resolver — Azure DevOps provider (Linux/macOS)
#
# Run from inside the cloned test repository.
# Required env vars: PR_ID, ADO_TOKEN (set by workflow)
set -euo pipefail

OUTPUT=$(claude -p --dangerously-skip-permissions "/qodo-pr-resolver auto-fix all" 2>&1)

PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  if [ "$result" = "true" ]; then
    echo "[PASS] $label"
    PASS=$((PASS + 1))
  else
    echo "[FAIL] $label"
    FAIL=$((FAIL + 1))
  fi
}

# Fetch ADO PR threads to check what was posted
ADO_B64=$(printf ':%s' "$ADO_TOKEN" | base64 | tr -d '\n')
THREADS=$(curl -s -H "Authorization: Basic $ADO_B64" \
  "https://dev.azure.com/qodoinc/pr-agent-tests/_apis/git/repositories/pr-agent-tests/pullRequests/${PR_ID}/threads?api-version=7.0" 2>&1)
COMMENTS=$(echo "$THREADS" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    parts = []
    for t in data.get('value', []):
        for c in t.get('comments', []):
            parts.append(c.get('content', ''))
    print('\n'.join(parts))
except Exception as e:
    print('', file=sys.stderr)
" 2>/dev/null)

# Criterion 1: Mock issue title parsed from comment (Phase 1 — content)
if echo "$OUTPUT" | grep -qi "syntax"; then
  check "Mock Qodo issue parsed" true
else
  check "Mock Qodo issue parsed" false
fi

# Criterion 2: Severity label in output OR in posted ADO comment (Phase 2)
if echo "$OUTPUT $COMMENTS" | grep -qiE "CRITICAL|HIGH|MEDIUM|LOW"; then
  check "Severity labels derived" true
else
  check "Severity labels derived" false
fi

# Criterion 3: Skill completed through Step 10 — PR URL echoed (Phase 3 proxy)
if echo "$OUTPUT" | grep -q "🔗 PR:"; then
  check "PR URL echoed (Step 10 reached)" true
else
  check "PR URL echoed (Step 10 reached)" false
fi

# Criterion 4: Summary comment actually posted to ADO (Phase 3 — actual write)
if echo "$COMMENTS" | grep -qiE "Fix Summary|✅ Fixed|Deferred|fix summary"; then
  check "Summary comment posted to ADO" true
else
  check "Summary comment posted to ADO" false
fi

TOTAL=$((PASS + FAIL))
echo ""
echo "--- Result: $PASS/$TOTAL criteria passed ---"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

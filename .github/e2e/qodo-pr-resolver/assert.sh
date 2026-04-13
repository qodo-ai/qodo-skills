#!/usr/bin/env bash
# E2E assertion script for qodo-pr-resolver — GitHub provider (Linux/macOS)
#
# Run from inside the cloned test repository.
# Required env vars: PR_NUMBER, TEST_REPO (set by workflow)
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

# Criterion 1: Mock issue title parsed from comment (Phase 1 — content)
if echo "$OUTPUT" | grep -qi "SyntaxError"; then
  check "Mock Qodo issue parsed" true
else
  check "Mock Qodo issue parsed" false
fi

# Criterion 2: Severity label in output OR in posted GitHub comment (Phase 2)
COMMENTS=$(gh pr view "$PR_NUMBER" --repo "$TEST_REPO" --json comments --jq '.comments[].body' 2>&1)
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

# Criterion 4: Summary comment actually posted to GitHub (Phase 3 — real write)
if echo "$COMMENTS" | grep -qiE "Fix Summary|✅ Fixed|Deferred|fix summary"; then
  check "Summary comment posted to GitHub" true
else
  check "Summary comment posted to GitHub" false
fi

TOTAL=$((PASS + FAIL))
echo ""
echo "--- Result: $PASS/$TOTAL criteria passed ---"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

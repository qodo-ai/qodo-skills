#!/usr/bin/env bash
# E2E assertion script for qodo-get-rules (Linux/macOS)
set -euo pipefail

OUTPUT=$(claude -p --dangerously-skip-permissions "/qodo-get-rules implement a JWT login endpoint for our Express API" 2>&1)

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

# Criterion 1: Rules loaded header
if echo "$OUTPUT" | grep -qi "Qodo Rules Loaded"; then
  check "Rules loaded header" true
else
  check "Rules loaded header" false
fi

# Criterion 2: At least one rule returned
if echo "$OUTPUT" | grep -qiE "\bERROR\b|\bWARNING\b|\bRECOMMENDATION\b"; then
  check "Rules returned (non-empty)" true
else
  check "Rules returned (non-empty)" false
fi

# Criterion 3: Security-relevant rules for JWT/auth prompt
if echo "$OUTPUT" | grep -qiE "Security|Authentication|JWT|Authorization|Credential|Token"; then
  check "Category relevance (Security/auth terms present)" true
else
  check "Category relevance (Security/auth terms present)" false
fi

TOTAL=$((PASS + FAIL))
echo ""
echo "--- Result: $PASS/$TOTAL criteria passed ---"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

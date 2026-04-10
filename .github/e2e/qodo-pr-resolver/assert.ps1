# E2E assertion script for qodo-pr-resolver — GitHub provider (Windows/PowerShell)
#
# Run from inside the cloned test repository.
# Required env vars: PR_NUMBER, TEST_REPO (set by workflow)
$ErrorActionPreference = 'Stop'

$OUTPUT = claude -p --dangerously-skip-permissions "/qodo-pr-resolver auto-fix all" 2>&1 | Out-String

$PASS = 0
$FAIL = 0

function Check-Criterion {
    param([string]$Label, [bool]$Result)
    if ($Result) {
        Write-Host "[PASS] $Label"
        $script:PASS++
    } else {
        Write-Host "[FAIL] $Label"
        $script:FAIL++
    }
}

# Criterion 1: Mock issue title parsed from comment (Phase 1 — content)
Check-Criterion "Mock Qodo issue parsed" ($OUTPUT -imatch "SyntaxError")

# Criterion 2: Severity label in output OR in posted GitHub comment (Phase 2)
$COMMENTS = gh pr view $env:PR_NUMBER --repo $env:TEST_REPO --json comments --jq '.comments[].body' 2>&1 | Out-String
Check-Criterion "Severity labels derived" (($OUTPUT + $COMMENTS) -imatch "CRITICAL|HIGH|MEDIUM|LOW")

# Criterion 3: Skill completed through Step 10 — PR URL echoed (Phase 3 proxy)
Check-Criterion "PR URL echoed (Step 10 reached)" ($OUTPUT -match "🔗 PR:")

# Criterion 4: Summary comment actually posted to GitHub (Phase 3 — real write)
Check-Criterion "Summary comment posted to GitHub" ($COMMENTS -imatch "Fix Summary|✅ Fixed|Deferred|fix summary")

$TOTAL = $PASS + $FAIL
Write-Host ""
Write-Host "--- Result: $PASS/$TOTAL criteria passed ---"

if ($FAIL -gt 0) {
    exit 1
}

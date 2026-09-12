# E2E assertion script for qodo-get-rules (Windows/PowerShell)
$ErrorActionPreference = 'Stop'

$OUTPUT = claude -p --dangerously-skip-permissions "/qodo-get-rules implement a JWT login endpoint for our Express API" 2>&1 | Out-String

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

# Criterion 1: Rules loaded header
Check-Criterion "Rules loaded header" ($OUTPUT -imatch "Qodo Rules Loaded")

# Criterion 2: At least one rule returned
Check-Criterion "Rules returned (non-empty)" ($OUTPUT -imatch "\bERROR\b|\bWARNING\b|\bRECOMMENDATION\b")

# Criterion 3: Security-relevant rules for JWT/auth prompt
Check-Criterion "Category relevance (Security/auth terms present)" ($OUTPUT -imatch "Security|Authentication|JWT|Authorization|Credential|Token")

$TOTAL = $PASS + $FAIL
Write-Host ""
Write-Host "--- Result: $PASS/$TOTAL criteria passed ---"

if ($FAIL -gt 0) {
    exit 1
}

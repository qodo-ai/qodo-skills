# E2E assertion script for qodo-pr-resolver — Azure DevOps provider (Windows/PowerShell)
#
# Run from inside the cloned test repository.
# Required env vars: PR_ID, ADO_TOKEN (set by workflow)
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

# Fetch ADO PR threads to check what was posted
$B64 = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes(":$($env:ADO_TOKEN)"))
$Headers = @{ Authorization = "Basic $B64" }
try {
    $ThreadsResponse = Invoke-RestMethod `
        -Uri "https://dev.azure.com/qodoinc/pr-agent-tests/_apis/git/repositories/pr-agent-tests/pullRequests/$($env:PR_ID)/threads?api-version=7.0" `
        -Headers $Headers -Method Get
    $COMMENTS = ($ThreadsResponse.value | ForEach-Object { $_.comments | ForEach-Object { $_.content } }) -join "`n"
} catch {
    $COMMENTS = ""
}

# Criterion 1: Mock issue title parsed from comment (Phase 1 — content)
Check-Criterion "Mock Qodo issue parsed" ($OUTPUT -imatch "SyntaxError")

# Criterion 2: Severity label in output OR in posted ADO comment (Phase 2)
Check-Criterion "Severity labels derived" (($OUTPUT + $COMMENTS) -imatch "CRITICAL|HIGH|MEDIUM|LOW")

# Criterion 3: Skill completed through Step 10 — PR URL echoed (Phase 3 proxy)
Check-Criterion "PR URL echoed (Step 10 reached)" ($OUTPUT -match "🔗 PR:")

# Criterion 4: Summary comment actually posted to ADO (Phase 3 — actual write)
Check-Criterion "Summary comment posted to ADO" ($COMMENTS -imatch "Fix Summary|✅ Fixed|Deferred|fix summary")

$TOTAL = $PASS + $FAIL
Write-Host ""
Write-Host "--- Result: $PASS/$TOTAL criteria passed ---"

if ($FAIL -gt 0) {
    exit 1
}

---
name: scaffold-e2e-ci
description: "Scaffold E2E CI assets for a skill — interviews the skill builder to define a test prompt and observable criteria, then generates workflow yml, assert scripts, and config"
triggers:
  - "scaffold.?e2e"
  - "scaffold.?ci"
  - "generate.?e2e"
  - "create.?e2e.?ci"
---

# scaffold-e2e-ci

Generates E2E CI infrastructure for a skill in this repository by interviewing the skill builder. The interview is the core of this skill — it guides the builder to define a meaningful test, not just a passing one.

## Step 1 — Identify the skill

Ask the skill builder which skill to scaffold if not provided:
> "Which skill are we scaffolding E2E CI for?"

Then read `skills/<skill>/support.yml` and extract:
- `os` list — drives the GitHub Actions matrix
- `skill` field — used for file naming

**OS → GitHub Actions runner:**
| `support.yml` | runner |
|---------------|--------|
| `ubuntu`      | `ubuntu-latest` |
| `macos`       | `macos-latest`  |
| `windows`     | `windows-latest` |

Determine groups needed:
- **unix** — `ubuntu` or `macos` is declared
- **windows** — `windows` is declared

## Step 2 — Interview: define the test prompt

Ask the builder to describe a real task a user would bring to this skill:

> "What's a realistic prompt a user would give this skill? Describe the scenario — what are they trying to do, and what context would they provide?"

Listen to their answer, then push back with one of these if the answer is too generic:
- If it's a one-liner with no context: "Can you make it more concrete? A real user prompt usually includes what they're building, not just the action."
- If it's abstract: "What would a developer actually type? Give me the messy real version, not a clean description of it."
- If it's perfect: proceed.

Once you have a good prompt, confirm: "I'll use this as the E2E test input: `<prompt>`. Does that look right?"

## Step 3 — Interview: define observable criteria

This is the most important part. Guide the builder to define what *observable evidence* in the skill's output would prove it worked correctly. Not "it ran" — proof that the right thing happened.

Ask:
> "If this skill ran successfully on that prompt, what would you expect to see in the output? Think about: what text, headers, or terms would only appear if the skill actually did its job?"

For each thing they describe, ask a follow-up:
- "Is that something we could grep for? What exact text or pattern?"
- If they say something that's not grep-able (e.g., "the code would be correct"): "That's important but hard to verify mechanically. What *observable text in the output* would signal that? For example: a header, a label, a category name?"
- If they're stuck: "Think about it this way — if someone broke the skill so it returned nothing useful, what would be *missing* from the output?"

Push for 2–4 concrete, grep-able criteria. Each must be:
1. **Observable** — visible as text in stdout
2. **Specific** — would only match if the skill actually did its job (not just "any output")
3. **Grep-able** — matchable with a case-insensitive regex

Once the builder has described all criteria, summarize them back:
> "Here's what I'll check for:
> 1. `<pattern>` — <what it proves>
> 2. `<pattern>` — <what it proves>
> ...
> Does this capture what you're looking for? Anything missing or wrong?"

Revise until confirmed.

## Step 4 — Write config.json

Write `.github/e2e/<skill>/config.json`:

```json
{
  "skill": "<skill>",
  "prompt": "<confirmed prompt>",
  "criteria": [
    { "id": "<slug>", "description": "<what it proves>", "match": "<regex>", "flags": "i" }
  ]
}
```

Use a short kebab-case `id` (e.g., `rules-loaded`, `topic-relevance`).

## Step 5 — Write assert.sh (Unix)

Only write if the skill declares `ubuntu` or `macos` support.

Write `.github/e2e/<skill>/assert.sh`:

```bash
#!/usr/bin/env bash
# E2E assertion script for <skill> (Linux/macOS)
set -euo pipefail

OUTPUT=$(claude -p --dangerously-skip-permissions "/<skill> <prompt>" 2>&1)

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

# Criterion N: <description>
if echo "$OUTPUT" | grep -qi "<match>"; then
  check "<description>" true
else
  check "<description>" false
fi
# ... one block per criterion

TOTAL=$((PASS + FAIL))
echo ""
echo "--- Result: $PASS/$TOTAL criteria passed ---"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
```

**Grep flag:** use `-qi` for plain strings, `-qiE` for patterns with `|`, `\b`, `+`, etc.

## Step 6 — Write assert.ps1 (Windows)

Only write if the skill declares `windows` support.

Write `.github/e2e/<skill>/assert.ps1`:

```powershell
# E2E assertion script for <skill> (Windows/PowerShell)
$ErrorActionPreference = 'Stop'

$OUTPUT = claude -p --dangerously-skip-permissions "/<skill> <prompt>" 2>&1 | Out-String

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

# Criterion N: <description>
Check-Criterion "<description>" ($OUTPUT -imatch "<match>")
# ... one line per criterion

$TOTAL = $PASS + $FAIL
Write-Host ""
Write-Host "--- Result: $PASS/$TOTAL criteria passed ---"

if ($FAIL -gt 0) {
    exit 1
}
```

## Step 7 — Write workflow yml

Write `.github/workflows/e2e-<skill>.yml`. Build the `os` matrix from the declared OSes only.

```yaml
name: E2E Test — <skill>

# Runs a live end-to-end test of the <skill> skill whenever a PR touches
# the skill's source files.
#
# Requires the `ci` environment which holds QODO_API_KEY, QODO_API_URL, and
# ANTHROPIC_API_KEY. Secrets are never exposed to fork PRs.

on:
  pull_request:
    branches:
      - main
    paths:
      - "skills/<skill>/**"

jobs:
  e2e:
    name: E2E test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    environment: ci

    strategy:
      matrix:
        os: [<comma-separated runners>]
      fail-fast: false

    if: github.event.pull_request.head.repo.full_name == github.repository

    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

    steps:
      - name: Checkout
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Install Claude Code CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Configure Qodo API key (Unix)
        if: runner.os != 'Windows'
        shell: bash
        run: |
          mkdir -p ~/.qodo
          printf '{"API_KEY":"%s","QODO_API_URL":"%s"}' "$QODO_API_KEY" "$QODO_API_URL" > ~/.qodo/config.json
        env:
          QODO_API_KEY: ${{ secrets.QODO_API_KEY }}
          QODO_API_URL: ${{ secrets.QODO_API_URL }}

      - name: Configure Qodo API key (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          New-Item -Force -ItemType Directory "$HOME/.qodo" | Out-Null
          $config = '{"API_KEY":"' + $env:QODO_API_KEY + '","QODO_API_URL":"' + $env:QODO_API_URL + '"}'
          Set-Content -Path "$HOME/.qodo/config.json" -Value $config
        env:
          QODO_API_KEY: ${{ secrets.QODO_API_KEY }}
          QODO_API_URL: ${{ secrets.QODO_API_URL }}

      - name: Install skill from PR branch (Unix)
        if: runner.os != 'Windows'
        shell: bash
        run: |
          mkdir -p .claude/skills
          rm -rf .claude/skills/<skill>
          cp -r skills/<skill> .claude/skills/<skill>

      - name: Install skill from PR branch (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          New-Item -Force -ItemType Directory ".claude/skills" | Out-Null
          Remove-Item -Recurse -Force ".claude/skills/<skill>" -ErrorAction SilentlyContinue
          Copy-Item -Recurse "skills/<skill>" ".claude/skills/<skill>"

      - name: Run skill and assert criteria (Unix)
        if: runner.os != 'Windows'
        shell: bash
        run: bash .github/e2e/<skill>/assert.sh

      - name: Run skill and assert criteria (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: .github/e2e/<skill>/assert.ps1
```

Omit Windows-specific steps entirely if `windows` is not declared. Omit Unix-specific steps entirely if neither `ubuntu` nor `macos` is declared.

## Step 8 — Report

After writing all files:

```
Generated E2E CI for <skill>:
  .github/e2e/<skill>/config.json      — test prompt + <N> criteria
  .github/e2e/<skill>/assert.sh        — bash assertions (Linux/macOS)
  .github/e2e/<skill>/assert.ps1       — PowerShell assertions (Windows)
  .github/workflows/e2e-<skill>.yml    — CI workflow (matrix: <runners>)

Next steps:
  1. Review the criteria in config.json — these are what CI will enforce on every PR
  2. git add and commit the 4 files
  3. Open a PR to trigger the workflow
```

Omit any file that was skipped from the report.

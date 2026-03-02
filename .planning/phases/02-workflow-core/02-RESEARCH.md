# Phase 2: Workflow Core - Research

**Researched:** 2026-03-02
**Domain:** GitHub Actions workflow triggers, PR event detection, changed-files action
**Confidence:** HIGH

## Summary

Phase 2 creates the GitHub Actions workflow YAML file that: (1) fires only when a PR is merged to main, not merely closed; (2) detects which `skills/` subdirectories changed in that PR; and (3) exits cleanly without side effects when no `skills/` files changed. The workflow is the sole code artifact of this phase — no application code, no scripts outside the YAML.

The trigger pattern is well-established in GitHub Actions: `pull_request: types: [closed]` at the event level combined with `if: github.event.pull_request.merged == true` at the job level. This correctly filters out PR closures without merge and only runs job logic on actual merges.

The changed-files detection uses `tj-actions/changed-files`, which must be pinned to a commit SHA (not a version tag) due to CVE-2025-30066 — a confirmed March 2025 supply chain compromise of this exact action that caused 23,000+ repository exposures. The SHA for v47.0.4 is `7dee1b0c1557f278e5c7dc244927139d78c0e22a`. The action's `dir_names: 'true'` output mode combined with `files: skills/**` gives the exact list of changed skill directories needed.

**Primary recommendation:** Use `tj-actions/changed-files@7dee1b0c1557f278e5c7dc244927139d78c0e22a` with `files: skills/**` and `dir_names: 'true'`; gate all subsequent steps on `steps.<id>.outputs.any_changed == 'true'`; pin `actions/checkout` to `11bd71901bbe5b1630ceea73d27597364c9af683` (v4.2.2).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRIG-01 | Workflow triggers only when a PR is merged to main (not merely closed) | `pull_request: types: [closed]` + `if: github.event.pull_request.merged == true` job condition — confirmed by GitHub official docs |
| TRIG-02 | Uses `pull_request: types: [closed]` event with `if: github.event.pull_request.merged == true` job condition | Exact pattern documented in GitHub Actions official docs; not a workaround — it is the canonical approach |
| DETECT-01 | Detects which `skills/` subdirectories were modified in the merged PR | `tj-actions/changed-files` with `files: skills/**` + `dir_names: 'true'` + `dir_names_max_depth: '2'` outputs space-separated list of changed skill dirs |
| DETECT-02 | Suppresses notification when no `skills/` files changed | Gate subsequent steps with `if: steps.<id>.outputs.any_changed == 'true'`; workflow runs but exits cleanly when false |
| DETECT-03 | Third-party changed-files action pinned to commit SHA, not version tag | SHA for v47.0.4: `7dee1b0c1557f278e5c7dc244927139d78c0e22a` — CVE-2025-30066 makes SHA pinning mandatory |
</phase_requirements>

## Standard Stack

### Core

| Library | Version / SHA | Purpose | Why Standard |
|---------|--------------|---------|--------------|
| `actions/checkout` | v4.2.2 (`11bd71901bbe5b1630ceea73d27597364c9af683`) | Check out repository code so changed-files can diff it | Required by tj-actions/changed-files; v4 is current LTS |
| `tj-actions/changed-files` | v47.0.4 (`7dee1b0c1557f278e5c7dc244927139d78c0e22a`) | Detect which files/dirs changed in the PR | Standard ecosystem tool; purpose-built for this use case; supports `dir_names` mode |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ubuntu-latest` runner | (managed) | Workflow execution environment | Default for all non-platform-specific GH Actions work |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tj-actions/changed-files` | `dorny/paths-filter` | paths-filter is simpler but outputs boolean per pattern, not the list of changed directories — DETECT-01 needs the list |
| `tj-actions/changed-files` | `git diff --name-only` in a shell step | More control but requires `fetch-depth: 0` on push events; on `pull_request` events the action handles diffing correctly without extra fetch |
| SHA pinning | Version tag pinning | Tags are mutable; CVE-2025-30066 showed `tj-actions/changed-files` tags were all rewritten to a malicious commit in March 2025. SHA is immutable |

## Architecture Patterns

### Recommended File Structure

```
.github/
└── workflows/
    └── notify-skill-changes.yml   # Single workflow file — all of Phase 2 and 3 output
```

### Pattern 1: Merge-Only Trigger

**What:** Use `pull_request: types: [closed]` event with `if: github.event.pull_request.merged == true` on the job.

**When to use:** Any time you need to act only on PR merges, not all closures.

**Why not `push`:** Push events do not carry PR metadata (title, author, PR URL) — required in Phase 3.

**Example:**
```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#pull_request
on:
  pull_request:
    types: [closed]
    branches:
      - main

jobs:
  notify:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - run: echo "PR was merged"
```

### Pattern 2: SHA-Pinned Changed-Files Detection

**What:** Use `tj-actions/changed-files` pinned to a full commit SHA, scoped to `skills/**`, with `dir_names: 'true'` to get directory names.

**When to use:** Whenever detecting which subdirectories changed in a PR/push.

**Key outputs used:**
- `any_changed` — boolean string `'true'` or `'false'`
- `all_changed_files` — space-separated list of changed dirs (when `dir_names: 'true'`)

**Example:**
```yaml
# Source: https://github.com/tj-actions/changed-files
- name: Detect changed skills
  id: changed-skills
  uses: tj-actions/changed-files@7dee1b0c1557f278e5c7dc244927139d78c0e22a
  with:
    files: skills/**
    dir_names: 'true'
    dir_names_max_depth: '2'
```

### Pattern 3: Conditional Exit for Non-Skill PRs

**What:** Gate all downstream steps on `any_changed == 'true'`. When false, the job completes with no side effects.

**When to use:** DETECT-02 — when non-skill PRs must not trigger notifications.

**Two approaches — both valid:**

Option A: Per-step `if` condition (used in Phase 2 for logging):
```yaml
- name: Log changed skills
  if: steps.changed-skills.outputs.any_changed == 'true'
  run: |
    echo "Changed skills: ${{ steps.changed-skills.outputs.all_changed_files }}"
```

Option B: Early exit step (explicit, readable):
```yaml
- name: Skip if no skill changes
  if: steps.changed-skills.outputs.any_changed == 'false'
  run: |
    echo "No skills/ changes detected — skipping notification"
```

**Recommendation:** Use Option A for Phase 2's logging step. Phase 3 will naturally gate the Slack step the same way.

### Pattern 4: Extracting Skill Names from Dir Paths

**What:** Strip the `skills/` prefix from directory paths to get just the skill name.

**When to use:** NOTIF-05 in Phase 3 (readable skill names). Research it now because `dir_names_max_depth: '2'` already produces `skills/qodo-get-rules` — the skill name is the second path component.

**Bash parameter expansion (no external tools):**
```bash
# Input:  "skills/qodo-get-rules skills/qodo-pr-resolver"
# Output: "qodo-get-rules" "qodo-pr-resolver"
for dir in ${{ steps.changed-skills.outputs.all_changed_files }}; do
  skill_name="${dir#skills/}"   # strip "skills/" prefix
  echo "Skill: $skill_name"
done
```

### Anti-Patterns to Avoid

- **Using `push` event instead of `pull_request: [closed]`:** Push events have no `github.event.pull_request` context — title, author, and PR URL are unavailable. This would break Phase 3.
- **Pinning by version tag (`@v47`):** Tags are mutable. CVE-2025-30066 demonstrated that all `tj-actions/changed-files` tags were updated simultaneously to a malicious commit. SHA is the only immutable reference.
- **Using `fetch-depth: 0` without understanding why:** For `pull_request` events, `actions/checkout` default fetch depth works correctly with `tj-actions/changed-files`. `fetch-depth: 0` is needed for `push` events. On `pull_request`, the action diffs against the base branch automatically.
- **Checking `any_changed` at the workflow level (top-level `if`):** The `pull_request.merged` check must be at job level. `any_changed` is only known after the detection step runs, so it must be a step-level `if`, not a job-level `if`.
- **Comparing `any_changed` as a boolean:** The output is a string. Compare with `== 'true'` (string), not `== true` (boolean).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting changed files in a PR | Custom `git diff` shell script | `tj-actions/changed-files` | The action handles base SHA resolution, merge commits, force-pushes, and both PR and push event diffing. Manual `git diff` requires careful SHA computation, `fetch-depth` management, and fails on edge cases |
| Filtering by directory pattern | Shell `grep` on git diff output | `files:` input on `tj-actions/changed-files` | The action's glob matching handles subdirectories, deletions, renames, and type changes correctly |

**Key insight:** `tj-actions/changed-files` exists precisely because correct diff detection across all GitHub event types is non-trivial. The edge cases (squash merges, force pushes, renamed files that cross directory boundaries) make hand-rolling error-prone.

## Common Pitfalls

### Pitfall 1: Wrong Event for Merge Detection

**What goes wrong:** Using `on: push` — the workflow fires on direct commits too, and PR context is missing.

**Why it happens:** "Merge to main" sounds like a push event to beginners.

**How to avoid:** Use `pull_request: types: [closed]` + `if: github.event.pull_request.merged == true`. Confirmed by official GitHub docs as the canonical pattern.

**Warning signs:** If `github.event.pull_request` is null in your workflow, you used the wrong event.

### Pitfall 2: Version Tag vs SHA Pin

**What goes wrong:** Using `tj-actions/changed-files@v47` — the tag can be rewritten (was rewritten in March 2025 during CVE-2025-30066).

**Why it happens:** Tags are easier to type and look stable.

**How to avoid:** Always use the full 40-character SHA: `tj-actions/changed-files@7dee1b0c1557f278e5c7dc244927139d78c0e22a`

**Warning signs:** Any action reference ending in `@v{number}` or `@latest` is a version tag — replace it.

### Pitfall 3: String vs Boolean Comparison for `any_changed`

**What goes wrong:** `if: steps.changed-skills.outputs.any_changed == true` — this is a boolean comparison; the output is the string `'true'`, so it may not behave as expected in all evaluation contexts.

**Why it happens:** The output name sounds boolean.

**How to avoid:** Use `if: steps.changed-skills.outputs.any_changed == 'true'` (single-quoted string).

### Pitfall 4: `dir_names_max_depth` Off-by-One

**What goes wrong:** Using `dir_names_max_depth: '1'` outputs `skills` (just the top-level directory name), not `skills/qodo-get-rules`.

**Why it happens:** The depth counts from the root, not from `skills/`.

**How to avoid:** Use `dir_names_max_depth: '2'` to get `skills/<skill-name>` paths. Then strip the prefix in shell: `"${dir#skills/}"`.

**Verification:** Check output by logging `${{ steps.changed-skills.outputs.all_changed_files }}` after a test merge.

### Pitfall 5: `branches` Filter vs Job Condition for Main-Only

**What goes wrong:** Omitting `branches: [main]` from the event filter means the workflow triggers on PRs merged to any branch, then the job condition has to do all the filtering.

**Why it happens:** Developers rely solely on the job-level `if` for filtering.

**How to avoid:** Add `branches: [main]` under the `pull_request` event to pre-filter at the workflow level. This is more efficient and explicit.

```yaml
on:
  pull_request:
    types: [closed]
    branches:
      - main
```

## Code Examples

Verified patterns from official sources:

### Complete Phase 2 Workflow Structure

```yaml
# Source: GitHub Actions official docs + tj-actions/changed-files README
name: Notify Skill Changes

on:
  pull_request:
    types: [closed]
    branches:
      - main

jobs:
  detect-skill-changes:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Detect changed skills
        id: changed-skills
        uses: tj-actions/changed-files@7dee1b0c1557f278e5c7dc244927139d78c0e22a  # v47.0.4
        with:
          files: skills/**
          dir_names: 'true'
          dir_names_max_depth: '2'

      - name: Log changed skills
        if: steps.changed-skills.outputs.any_changed == 'true'
        run: |
          echo "Changed skills detected:"
          for dir in ${{ steps.changed-skills.outputs.all_changed_files }}; do
            skill_name="${dir#skills/}"
            echo "  - $skill_name"
          done

      - name: No skill changes — skipping
        if: steps.changed-skills.outputs.any_changed == 'false'
        run: echo "No skills/ changes in this PR — no notification needed"
```

### Verifying Trigger Behavior (Manual Test)

```bash
# To verify TRIG-01 (merged-only): Close a PR WITHOUT merging.
# Expected: Workflow runs (event fires), but job is SKIPPED (if: false).
# To verify TRIG-01 (merged): Merge a PR to main.
# Expected: Job runs.

# To verify DETECT-02 (non-skill suppression): Merge a PR touching only README.md.
# Expected: Job runs, "No skill changes" step executes, "Log changed skills" step is skipped.

# To verify DETECT-01 (skill detection): Merge a PR touching skills/qodo-get-rules/SKILL.md.
# Expected: "Log changed skills" step executes and prints "qodo-get-rules".
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pin by version tag (`@v47`) | Pin by full commit SHA | March 2025 (CVE-2025-30066) | SHA is now mandatory for supply chain safety |
| `on: push` for merge detection | `on: pull_request: types: [closed]` + merged check | Always correct; awareness increased post-2023 | PR metadata (title, author) only available with PR event |
| `tj-actions/changed-files@v1` syntax | Current v47 with `dir_names` input | Action has evolved significantly | `dir_names` eliminates need for manual path parsing |

**Deprecated/outdated:**
- Version tag pinning (`@v47`, `@latest`): Not deprecated by GitHub, but insecure after CVE-2025-30066. Always use SHA.
- `tj-actions/changed-files` before v46.0.1: The versions compromised in March 2025 were patched at v46.0.1. v47.0.4 is clean.

## Open Questions

1. **Should `actions/checkout` also be SHA-pinned?**
   - What we know: DETECT-03 only requires the changed-files action to be SHA-pinned. `actions/checkout` is a first-party GitHub action (lower supply chain risk).
   - What's unclear: Whether the project wants SHA pinning for all actions or only third-party.
   - Recommendation: Pin `actions/checkout` to SHA as well (`11bd71901bbe5b1630ceea73d27597364c9af683` for v4.2.2) for defense-in-depth. The cost is negligible; the safety improvement is real.

2. **Is `branches: [main]` necessary or redundant with the job condition?**
   - What we know: The job `if: github.event.pull_request.merged == true` will handle filtering. The `branches` filter adds an extra layer.
   - What's unclear: Whether the repo uses `main` or `master` as its default branch.
   - Recommendation: Include `branches: [main]` based on the existing STATE.md references to "main". This makes intent explicit and prevents spurious workflow runs on non-main merges.

3. **What is the exact output format of `all_changed_files` with `dir_names: 'true'`?**
   - What we know: The README states it is space-separated. Multiple sources confirm this.
   - What's unclear: Edge case behavior when a skill directory is deleted (not just modified).
   - Recommendation: The `all_changed_files` output includes added, modified, and deleted paths. Deleted skill directories will appear in the list — this is correct behavior for Phase 2 (any change to `skills/` triggers notification, including deletions).

## Sources

### Primary (HIGH confidence)
- GitHub Actions official docs (events-that-trigger-workflows) — `pull_request: types: [closed]` trigger syntax and `github.event.pull_request.merged == true` condition pattern
- https://github.com/tj-actions/changed-files/releases/tag/v47.0.4 — SHA `7dee1b0c1557f278e5c7dc244927139d78c0e22a` for v47.0.4
- https://github.com/actions/checkout/releases/tag/v4.2.2 — SHA `11bd71901bbe5b1630ceea73d27597364c9af683` for v4.2.2
- https://github.com/tj-actions/changed-files/blob/main/action.yml — `dir_names`, `dir_names_max_depth`, `files`, `any_changed`, `all_changed_files` inputs/outputs

### Secondary (MEDIUM confidence)
- https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066 — CVE-2025-30066 supply chain compromise context (CISA advisory)
- Multiple WebSearch results confirming `any_changed` string comparison pattern and `dir_names_max_depth` behavior

### Tertiary (LOW confidence)
- WebSearch results on bash `${var#prefix}` parameter expansion — standard bash, LOW only because not verified against a specific authoritative source (it is standard POSIX shell syntax universally documented)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — SHAs verified directly from GitHub release pages
- Architecture: HIGH — trigger pattern from official GitHub docs; changed-files inputs from action.yml
- Pitfalls: HIGH for SHA pinning (CVE-2025-30066 is documented public event); MEDIUM for `dir_names_max_depth` behavior (from README, not tested)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (SHAs are immutable; action inputs are stable in v47)

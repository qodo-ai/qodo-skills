No real review would run. Here, `qodo` means the verified installed invocation. Context files below would live outside the reviewed worktrees; their contents are proposals only.

### 1. `milestone`: start an auto checkpoint

This is a coherent, previously unreviewed slice. Review the committed slice now, then continue independent integration work while it runs. No reason calls for fast or deep effort.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-milestone.json" --async --json
```

Context:
```json
{
  "decisions": [],
  "notes": "The API implementation slice is complete and the worktree is clean after its task commit. The slice was tested, but check names and pass/fail results were not supplied. Independent integration work remains. This is a midwork checkpoint, not final coverage of that future work.",
  "recent_work": ["Completed the coherent API implementation slice awaiting its first review."]
}
```

Retain the submitted snapshot identity. Integration changes made afterward need reconciliation before final handoff.

### 2. `dirty-final`: use the verified clean task-only worktree

Run from the available clean worktree at the intended PR-candidate commit, covering **every intended changed path** against the base.

Do not run ordinary capture in the original dirty worktree. Path filtering cannot separate unrelated staged edits within the same file. Do not stash, reset, commit, or otherwise alter the original files or index; no committed-only option is available.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-dirty-final.json" --async --json
```

Context:
```json
{
  "decisions": ["The user requested final review of the committed PR candidate while preserving all original working files and the index."],
  "notes": "Collection runs from the verified clean task-only worktree at the intended commit. It excludes the original worktree's unrelated staged and unstaged edits and private untracked scratch file. Verification results and implementation details were not supplied.",
  "recent_work": ["The committed PR candidate awaits final review; its detailed changes and prior-review delta were not supplied."]
}
```

Final status alone does not justify `--deep` or `--full`.

### 3. `already-covered`: reuse the completed assessment

**Ready locally.** The exact intended snapshot, base, full scope and policy already have complete compatible auto coverage; required findings are settled and tests passed.

Do not submit another review. Hand over the existing assessment and its snapshot/coverage references. This establishes local readiness, not hosted-review, CI or merge status.

### 4. `trivial`: continue without review

Do not automatically review the internal-comment typo. No submission or review context is needed.

### 5. `report-only`: review the uncommitted working scope

Collect the requested safe working scope without committing or editing anything. Use default auto effort.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-report-only.json" --async --json
```

Context:
```json
{
  "decisions": ["The user requested review only, with no edits or commits and no PR preparation."],
  "notes": "Review the requested uncommitted working scope, which is safe to collect. Implementation requirements and verification results were not supplied.",
  "recent_work": ["The requested uncommitted changes await their first review; detailed code changes were not supplied."]
}
```

Assess and report the findings, then stop. Do not apply fixes, write dismissals, or solicit permission to turn this into implementation.

### 6. `light-to-final`: request ordinary auto final coverage

**Reason for another assessment:** the completed fast checkpoint does not establish ordinary final coverage, even though it covered every path and nothing changed.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-light-to-final.json" --async --json
```

Use the full intended scope, with no temporary path restrictions.

```json
{
  "decisions": ["The user now requests ordinary final review before handoff."],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. Ordinary auto final coverage is still missing; the review budget is not exhausted.",
  "recent_work": []
}
```

Omit `--fast`, `--deep` and `--full`. Let the Engine determine continuation or reuse, then verify the returned effort and coverage actually satisfy the final requirement.

### 7. `explicit-fresh`: honor the requested `--full`

**Reason for another assessment:** the user explicitly requests a fresh assessment within budget.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-explicit-fresh.json" --full --async --json
```

Keep the same base and full intended scope.

```json
{
  "decisions": ["The user explicitly requested a fresh assessment with --full within the review budget."],
  "notes": "The unchanged snapshot already has complete compatible auto coverage and settled findings. This submission requests freshness, not deeper effort. No new evidence appeared.",
  "recent_work": []
}
```

### Collection for each new submission

Retain its returned operation ID, base, snapshot, scope and context. Collect that same operation rather than resubmitting:

```sh
qodo review status "$operation_id" --json
```

Respect returned polling delays. For additional stored detail, use `--extended`, not another assessment.

Before claiming readiness, inspect complete inventory and coverage, warnings, reviewer commentary, earlier open findings and relevant check results. Acceptance is not completion; zero new findings alone is not readiness.

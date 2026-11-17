### 1. `milestone`

Submit an **auto, asynchronous checkpoint now**: the slice is coherent and tested, and feedback can guide remaining integration work. No `--fast`, `--deep` or `--full` is needed.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

Proposed context:
```json
{
  "decisions": [],
  "notes": "Review the completed API implementation slice at the task commit. The worktree is clean. Tests were run, but their commands and outcomes were not supplied. Independent integration work remains; this is not final handoff.",
  "recent_work": [
    "Completed a coherent API implementation slice that has not previously been reviewed."
  ]
}
```

Retain the accepted operation ID and submitted snapshot, continue independent integration work, and collect the result at a natural pause. Recheck findings against any changes made while review runs.

### 2. `dirty-final`

Run from the **verified task-only clean worktree at the intended commit**, covering every intended PR path.

Ordinary collection in the original worktree would include unrelated changes. Path filtering cannot separate unrelated edits within the same file, and this CLI has no committed-only option. Leave the original files and index untouched—no stash, reset or additional commits.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

Proposed context:
```json
{
  "decisions": [
    "The user requires final review of the committed PR candidate while preserving all original working files and the index."
  ],
  "notes": "Collect the full intended candidate from the verified task-only clean worktree at the intended commit. Unrelated staged, unstaged and untracked work in the original worktree is outside scope. Candidate behavior, implementation rationale and test outcomes were not supplied.",
  "recent_work": [
    "The committed PR candidate is awaiting final assessment; its implementation details were not supplied."
  ]
}
```

Use auto effort. Final-review status alone justifies neither `--deep` nor `--full`. Verify the reported scope, exclusions and omissions before claiming candidate coverage.

### 3. `already-covered`

**Do not submit another assessment.** The exact intended snapshot already has compatible, complete auto coverage, settled required findings and passing tests.

Hand off as **ready locally**, referencing the existing assessment and checks. That does not establish hosted-review cleanliness, CI success or merge readiness.

### 4. `trivial`

**Skip automatic review and continue the task.** An internal-comment typo with no behavior change does not warrant a checkpoint. No review command or context submission is needed.

### 5. `report-only`

Review the requested safe working scope **without editing or committing**. Do not broaden this into PR preparation.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

Proposed context:
```json
{
  "decisions": [
    "The user requested review only, with no edits or commits and no PR preparation."
  ],
  "notes": "Review the requested uncommitted working scope, which is safe to collect. No existing review covers it. Implementation details and verification outcomes were not supplied.",
  "recent_work": [
    "Uncommitted changes are awaiting their first requested assessment."
  ]
}
```

Collect and independently assess Qodo’s findings, report them, and stop. Do not apply fixes, store dismissals or solicit permission to convert this report-only task into implementation.

### 6. `light-to-final`

**Submit an ordinary auto final assessment.** The concrete reason is missing ordinary final coverage: the completed `--fast` checkpoint alone is insufficient, even though the snapshot is unchanged.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

Proposed context:
```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. There is no completed auto final assessment. Required ordinary final coverage remains outstanding; the user budget is not exhausted.",
  "recent_work": []
}
```

Omit `--fast` and `--deep`. Do not add `--full` merely because this is final review. Let the Engine determine continuation or reuse, then verify that the returned assessment actually satisfies final coverage; do not relabel the earlier light checkpoint as final.

### 7. `explicit-fresh`

**Honor the explicit fresh-assessment request**, despite existing compatible coverage. The request is within budget and specifically authorizes `--full`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Proposed context:
```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full within the available review budget."
  ],
  "notes": "The unchanged snapshot already has complete compatible auto coverage and settled findings. This submission is a user-requested fresh assessment, not a response to changed code or new evidence.",
  "recent_work": []
}
```

Keep auto effort: `--full` requests freshness, not deep scrutiny.

### Collection and context handling

All commands above are proposals only. `qodo` denotes the resolved installed invocation; the stated compatibility, identity and help checks are already satisfied. `$CONTEXT_DIR` would be a private directory **outside all reviewed worktrees**, containing complete UTF-8 JSON files without a BOM. No implementation choices, code citations or passing test results should be invented to fill missing context.

For each accepted submission, retain its operation ID and collect that same operation:

```sh
qodo review status "$operation_id" --json
```

Respect polling delays; do not resubmit to check progress. Before any readiness claim, inspect complete coverage, omissions, context-delivery metadata and the full finding inventory—including earlier open findings. An accepted or pending operation is not a completed assessment.

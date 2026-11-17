No commands would run here. I would use the already-verified installed `qodo` invocation. In these proposals, `$REVIEW_CONTEXT_DIR` is an approved directory **outside the reviewed worktrees**, containing separate UTF-8 JSON context files.

### 1. `milestone`: submit an auto checkpoint now

The completed, testable API slice is a useful review milestone. Review its full current scope without temporary path restrictions. Default to **auto**, not fast or deep.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT_DIR/milestone.json" --async --json
```

Context:
```json
{
  "decisions": [],
  "notes": "The API implementation slice is complete and the worktree is clean after its task commit. The user reports testing, but the commands and outcomes are unknown. Independent integration work remains. Specific implementation decisions and their rationale were not supplied.",
  "recent_work": [
    "Completed the substantive API implementation slice awaiting its first review."
  ]
}
```

Retain the returned operation ID, continue useful independent integration work, and collect the result at a natural pause. If code changes meanwhile, assess findings against the current code; this checkpoint does not cover subsequent changes.

### 2. `dirty-final`: review from the verified clean worktree

Ordinary collection in the original worktree would include unrelated changes. There is no supported committed-only option, so I would run this **inside the available, verified task-only clean worktree at the intended commit**:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT_DIR/dirty-final.json" --async --json
```

Use the full committed candidate scope, without path restrictions. Leave the original index, staged and unstaged work, and private untracked scratch file untouched—no reset, stash, or temporary commits.

Context:
```json
{
  "decisions": [
    "The user requires final review of the committed PR candidate while preserving the original working files and index.",
    "The coding agent selected the verified task-only clean worktree to exclude unrelated work."
  ],
  "notes": "This worktree contains the intended committed candidate. Unrelated staged edits, unstaged work and the private scratch file remain outside this collection. Implementation details, prior-review change history and test outcomes were not supplied.",
  "recent_work": []
}
```

Final-review status alone does not justify `--deep` or `--full`.

### 3. `already-covered`: reuse coverage and hand over

**No new submission or context file.** The exact intended snapshot, base, full scope and relevant policy already have compatible completed auto coverage; inventory and coverage are complete, required findings are settled, and tests passed.

I would report **ready locally**, referencing that existing assessment. Another unchanged run would add no justified coverage. This does not independently establish hosted review, CI, merge or release readiness.

### 4. `trivial`: continue without review

**No review command.** A behavior-neutral internal-comment typo does not warrant an automatic checkpoint. Continue the task.

### 5. `report-only`: review the requested working scope without changes

Use auto effort and collect the requested safe uncommitted working scope. Do not create a commit or reinterpret this as committed PR-candidate review.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT_DIR/report-only.json" --async --json
```

Context:
```json
{
  "decisions": [
    "The user requested review of uncommitted code without editing or committing."
  ],
  "notes": "The requested working scope is safe to collect. This is report-only, not PR preparation. Functional requirements, implementation choices and verification results were not supplied.",
  "recent_work": [
    "The requested uncommitted changes await their first review."
  ]
}
```

After collection, independently assess and report the findings. Do not edit, commit, persist dismissals, or solicit permission to convert the task into implementation.

### 6. `light-to-final`: submit an ordinary auto final assessment

**Reason for another assessment:** required ordinary final coverage is missing. The completed full-scope `--fast` checkpoint is useful evidence, but light coverage alone is insufficient for ordinary final handoff—even though nothing changed.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT_DIR/light-to-final.json" --async --json
```

Keep the same base and full intended scope. Omit `--fast`, `--deep` and `--full`. Let the Engine determine eligible continuation or reuse, then verify the actual final coverage.

Context:
```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. No completed auto final assessment exists. Test outcomes and finding dispositions were not supplied.",
  "recent_work": []
}
```

### 7. `explicit-fresh`: honor the fresh-assessment request

**Reason for another assessment:** the user explicitly requested a fresh assessment within budget.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Preserve the same full scope and default auto effort. `--full` requests fresh assessment; it does not mean deep effort.

Context:
```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full."
  ],
  "notes": "The unchanged current snapshot already has complete compatible auto coverage and settled findings. No new evidence appeared. The fresh assessment is within the user's review budget. Test results were not supplied.",
  "recent_work": []
}
```

### Collection for every new submission

Retain each operation ID with its submitted base, snapshot identity, scope and context. Collect that same operation rather than starting another review:

```sh
qodo review status "$OPERATION_ID" --json
```

Respect returned polling delays and retention. Before claiming readiness, verify matching snapshot identity, complete coverage and inventory, exclusions, warnings, context delivery, and both new and earlier open findings. Report resolved and dismissed findings separately. Acceptance or zero new findings alone does not establish readiness.

These are proposals only; I would not run a review here. Compatibility, identity and flag discovery are already satisfied.

For the commands below:
- `qodo` means the verified installed invocation.
- `CONTEXT_DIR` would identify a unique directory outside all reviewed worktrees. Each context file would contain the proposed JSON below.
- Every submission uses the verified merge-base literally.

### 1. `milestone`

**Submit one auto-effort checkpoint now**, then continue the independent integration work. This is a useful, tested implementation slice—not an every-edit review. No reason justifies forcing fast or deep.

Scope: the task changes in the clean task worktree, without invented path restrictions.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

Context:

```json
{
  "decisions": [],
  "notes": "A coherent API implementation slice is complete and has been tested. Test commands and outcomes were not supplied, so passing tests are not established. Independent integration work remains. No implementation-specific requirements, guards or design rationale were supplied.",
  "recent_work": [
    "Implemented the coherent API slice now awaiting its first review."
  ]
}
```

Retain the accepted operation and submitted snapshot. Collect its result at a natural pause; if integration work changes the code meanwhile, reassess findings against current code. This checkpoint does not automatically cover subsequent work.

### 2. `dirty-final`

**Review from the available, verified task-only clean worktree at the intended commit.** Ordinary capture in the original worktree would include unrelated changes, even after a task-only commit.

Preserve the original files and index completely: no staging, stashing, resetting or committing. Do not invent an unsupported committed-only flag.

Scope: the entire committed candidate relative to the verified base, with no temporary path restrictions.

Run from that clean worktree:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user requested final review of the committed PR candidate and preservation of all original working files and the index.",
    "The coding agent selected the verified task-only clean worktree because ordinary capture in the original worktree includes unrelated changes and committed-only collection is unavailable."
  ],
  "notes": "Review the full committed candidate from the isolated clean worktree. Unrelated staged edits, unrelated unstaged work and private untracked scratch content remain outside this collection. Test outcomes and implementation-specific requirements were not supplied.",
  "recent_work": [
    "The committed PR candidate is awaiting final assessment; its implementation details were not supplied."
  ]
}
```

Use ordinary auto effort—not deep or `--full` merely because this is final review. Verify returned coverage matches the intended candidate before claiming it was assessed.

### 3. `already-covered`

**Hand over the work without another assessment.** The exact snapshot, base, full scope and relevant policy already have complete compatible auto coverage; required findings are settled and tests passed.

Reuse the completed assessment and its existing reference. No new submission or context file is needed.

Outcome: **Ready locally.** This does not independently establish hosted review cleanliness, successful finding handoff, CI or merge readiness.

### 4. `trivial`

**Continue the task without a review.** An internal-comment typo with no behavior change does not warrant an automatic checkpoint.

No review command or review context is needed.

### 5. `report-only`

**Review the requested safe working scope without editing or committing.** Do not isolate away the requested uncommitted code or turn this into PR preparation.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user requested report-only review of uncommitted code, without edits or commits."
  ],
  "notes": "Assess the requested working scope, which is safe to collect. PR preparation is not requested. Implementation requirements, design decisions and test outcomes were not supplied.",
  "recent_work": [
    "The requested uncommitted changes await their first review; their behavior was not described in the supplied evidence."
  ]
}
```

Assess and report the findings, then stop. Do not edit, commit, store dismissals or solicit permission to convert this report-only task into implementation.

### 6. `light-to-final`

**Proceed with an ordinary auto final assessment.** The concrete reason is missing ordinary final coverage: an unchanged fast checkpoint alone is insufficient.

Keep the same verified base and full intended scope. Remove `--fast`; do not add `--deep` or automatically force `--full`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user requested ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for this full intended snapshot. No code or evidence changed afterward. There is no completed auto final assessment, and the review budget is not exhausted. Test outcomes were not supplied.",
  "recent_work": []
}
```

Let the Engine determine continuation eligibility. Inspect the actual effort, analysis mode and coverage; do not claim that reused light evidence establishes ordinary final coverage without supporting results.

### 7. `explicit-fresh`

**Honor the explicit fresh-assessment request using `--full`.** This is justified despite unchanged code because the user specifically requested it within budget.

Keep the existing base and full scope. `--full` requests fresh assessment, not deep effort.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Context:

```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full within the available review budget."
  ],
  "notes": "The unchanged current snapshot already has complete compatible auto coverage and settled findings. This submission honors the explicit fresh-assessment request. No new evidence or test outcomes were supplied.",
  "recent_work": []
}
```

### Collecting any submitted review

Retain the returned operation ID with its base, scope, snapshot and submitted context. Collect that operation rather than submitting again:

```sh
qodo review status "$operation_id" --extended --json
```

Respect returned polling delays. Acceptance is not completion. Read warnings, reviewer commentary, complete inventory, coverage and context-delivery metadata. Separate introduced and still-open findings from resolved and dismissed findings, and report any missing evidence. Review authority alone does not authorize edits, commits, dismissals, pushes or PR creation.

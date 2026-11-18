These are proposals only; no commands, reviews, commits or writes were performed.

Commands use the verified installed `qodo` invocation. `$CONTEXT_DIR` denotes task-owned storage outside all reviewed worktrees. Each context file would contain UTF-8 JSON without a BOM.

```sh
base=1111111111111111111111111111111111111111
```

### 1. `milestone`: submit an auto checkpoint now

The coherent, testable slice is a useful review boundary. Review the clean task commit’s intended changes, then continue independent integration work while the assessment runs. No additional commit is needed.

```sh
qodo review --base "$base" --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

Omit `--fast`, `--deep` and `--full`: an ordinary milestone defaults to auto.

```json
{
  "decisions": [],
  "notes": "A coherent API implementation slice is complete and the worktree is clean after its task commit. The slice was tested, but test commands and results were not supplied; passing tests are not established. Independent integration work remains and is not part of this submitted snapshot. Implementation choices and their rationale were not supplied.",
  "recent_work": [
    "Completed the API implementation slice awaiting its first review."
  ]
}
```

Retain the submitted snapshot identity before continuing work. Later integration changes will need their own coverage before final handoff.

### 2. `dirty-final`: review from the verified clean checkout

Ordinary capture in the original worktree would include unrelated and private content. Path filtering cannot separate staged edits in the same file, and the CLI has no committed-only option.

Run from the **available, verified task-only clean worktree at the intended commit**, with no path restrictions:

```sh
qodo review --base "$base" --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

Preserve the original files and index exactly. Do not reset, stash, commit or collect their unrelated contents.

```json
{
  "decisions": [
    "The user requests final review of the committed PR candidate while preserving the original working files and index.",
    "The coding agent selects the verified clean task-only checkout because ordinary capture in the original worktree includes unrelated work and the CLI has no committed-only collection option."
  ],
  "notes": "Review the full intended committed candidate against the supplied base. Unrelated staged edits, unstaged work and the private untracked scratch file in the original worktree are outside this collection. Test results and detailed implementation decisions were not supplied.",
  "recent_work": [
    "The committed PR candidate awaits final assessment; its detailed change history relative to any earlier review was not supplied."
  ]
}
```

Final-review status alone does not justify `--deep` or `--full`.

### 3. `already-covered`: reuse coverage and hand off

**Do not submit another assessment.** The exact intended snapshot, base, full scope and relevant policy already have compatible completed auto coverage; inventory is complete, required findings are settled and tests passed.

Report **ready locally**, referencing the existing assessment and validation evidence. No new submission context is needed. Do not extend that conclusion to hosted review, finding synchronization, CI, merge or release without separate evidence.

### 4. `trivial`: continue without automatic review

Do not launch a review for the internal-comment typo. No behavior changed, no review was requested, and this is not a completed-work handoff.

### 5. `report-only`: review the requested uncommitted scope

Collect the safe requested working scope without editing or committing. Do not convert this into committed-candidate review or PR preparation.

```sh
qodo review --base "$base" --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

Retain any requested path restrictions; none are specified here.

```json
{
  "decisions": [
    "The user explicitly requests review without edits or commits and does not request PR preparation."
  ],
  "notes": "Review the requested uncommitted working scope, which is safe to collect. There is no existing assessment for this scope. Implementation details and verification results were not supplied. This is a working-snapshot assessment, not certification of a committed PR candidate.",
  "recent_work": [
    "The requested uncommitted changes await review; their detailed behavior was not supplied."
  ]
}
```

Independently assess and report Qodo’s findings, then stop. Do not apply fixes, store dismissals or solicit permission to turn this report-only request into implementation.

### 6. `light-to-final`: submit ordinary auto final review

**Reason for another assessment:** the completed light checkpoint does not establish ordinary final coverage. This remains a valid reason even though nothing changed.

Use the same base and full intended scope:

```sh
qodo review --base "$base" --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

Do not carry forward `--fast`, escalate to `--deep`, or automatically force `--full`.

```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for this full intended snapshot. No code or evidence changed afterward. No completed auto final assessment exists, and the user budget is not exhausted. This submission addresses missing ordinary final coverage. Test results were not supplied.",
  "recent_work": []
}
```

Let the Engine determine continuation or fallback. Verify that the returned evidence establishes the required final coverage; mere reuse of the light checkpoint is not enough.

### 7. `explicit-fresh`: honor the fresh-assessment request

**Reason for another assessment:** the user explicitly requested a fresh assessment within budget.

```sh
qodo review --base "$base" --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Keep the same base and full scope. `--full` requests freshness, not deeper effort; effort remains auto.

```json
{
  "decisions": [
    "The user explicitly requests a fresh full assessment with --full, within the review budget."
  ],
  "notes": "The unchanged current snapshot already has complete compatible auto coverage and settled findings. No new evidence appeared. A fresh assessment is requested by the user rather than required by changed code. Test results were not supplied.",
  "recent_work": []
}
```

### Collect every submitted assessment

Retain each accepted operation ID with its base, commit/tree, scope and submitted context. Poll that operation rather than resubmitting:

```sh
qodo review status "$operation_id" --json
```

Respect returned polling delays and retention. Acceptance is not completion.

Before declaring readiness, verify available operation/snapshot identities, inspect exclusions and warnings, read `review_agent_comment`, and assess the complete inventory—including both introduced and still-open findings. Report resolved and dismissed findings separately. Missing coverage, inventory or identity evidence remains a disclosed gap; zero new findings alone does not establish readiness.

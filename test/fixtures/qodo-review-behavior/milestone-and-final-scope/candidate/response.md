Proposed actions only—nothing run or written. I would reuse the verified CLI, identity and help information. Commands below use `qodo` for the resolved installed invocation.

For these examples, context files would live outside every reviewed worktree:

```sh
REVIEW_BASE=1111111111111111111111111111111111111111
REVIEW_CONTEXT_DIR=/outside/review-context
```

### 1. `milestone`

**Submit an auto checkpoint now.** This is a coherent, tested, unreviewed slice, and feedback can guide the remaining integration work. No quick/deep request or concrete high-impact risk justifies changing effort.

Run from the clean task worktree, covering all changes in the completed slice:

```sh
qodo review --base "$REVIEW_BASE" --context-file "$REVIEW_CONTEXT_DIR/milestone.json" --async --json
```

Proposed context:

```json
{
  "decisions": [],
  "notes": "The coherent API implementation slice is complete and has been tested. Test commands and outcomes were not supplied, so passing tests are not established. The worktree is clean after the task commit. Independent integration work remains; this is a midwork checkpoint, not final coverage of that future work. Implementation-specific decisions and rationale were not provided.",
  "recent_work": [
    "Completed the API implementation slice awaiting its first review."
  ]
}
```

Continue useful independent integration work while the operation runs. Recheck findings against any subsequently changed code.

### 2. `dirty-final`

**Review from the available, verified task-only clean worktree at the intended commit.** Ordinary capture in the original worktree would review unrelated content and would not certify the committed candidate.

Leave the original files and index untouched: no reset, stash, staging changes or additional commits. A path filter cannot separate unrelated edits within the same file. Do not invent a committed-only flag.

Run in the isolated clean worktree, with the **full intended candidate scope** and no path restrictions:

```sh
qodo review --base "$REVIEW_BASE" --context-file "$REVIEW_CONTEXT_DIR/dirty-final.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user requests final review of the committed PR candidate and requires preservation of all original working files and the index.",
    "I would use the verified task-only clean worktree because ordinary capture in the original worktree includes unrelated edits."
  ],
  "notes": "Review the full intended committed candidate from the isolated clean worktree. Unrelated staged edits, unstaged work and the private untracked scratch file remain in the original worktree and are not review inputs. Candidate behavior, implementation rationale and test outcomes were not supplied.",
  "recent_work": [
    "The committed PR candidate is awaiting final review; its detailed changes were not supplied."
  ]
}
```

Verify returned base, commit/tree, exclusions and coverage against that candidate before claiming final assessment. Test verification remains unknown.

### 3. `already-covered`

**Do not submit another assessment.** The exact snapshot, base, full scope and relevant policy already have compatible completed auto coverage. Inventory and coverage are complete, required findings are settled, and tests passed.

Hand over the existing result as **Ready locally**, retaining its review reference and scope evidence. No new command or context submission is needed. This does not independently establish hosted review, CI or merge readiness.

### 4. `trivial`

**Continue the task without an automatic review.** A comment typo with no behavior change does not warrant a checkpoint.

No review command, context submission or extra commit is needed.

### 5. `report-only`

**Review the requested uncommitted working scope without editing or committing.** Collect that working snapshot directly; do not turn it into a committed-candidate or PR-preparation task.

```sh
qodo review --base "$REVIEW_BASE" --context-file "$REVIEW_CONTEXT_DIR/report-only.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user explicitly requests review only: no edits, commits or PR preparation."
  ],
  "notes": "The requested uncommitted working scope is safe to collect and has no existing review. Expected behavior, implementation decisions and test results were not supplied; these remain unknown.",
  "recent_work": [
    "The requested uncommitted changes are awaiting their first review; detailed behavior was not supplied."
  ]
}
```

Assess the findings against the code, report impact and recommended action, then stop. Do not apply fixes, persist dismissals or solicit permission to expand this report-only task into implementation.

### 6. `light-to-final`

**Submit ordinary auto final review.** The concrete reason is **missing ordinary final coverage**: a purposeful fast checkpoint alone does not satisfy the requested final review, even when code is unchanged.

Keep the same base and full intended scope. Omit `--fast`, `--deep` and `--full`; final-review status alone does not justify deep or forced full execution.

```sh
qodo review --base "$REVIEW_BASE" --context-file "$REVIEW_CONTEXT_DIR/light-to-final.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for this full intended snapshot. No code or evidence changed afterward, but no completed auto final assessment exists. This submission addresses missing ordinary final coverage. Test outcomes were not supplied.",
  "recent_work": []
}
```

Let the Engine determine continuation eligibility and report its actual mode and coverage. Do not claim final coverage merely because the request was accepted—or if the returned evidence only establishes the earlier light checkpoint.

### 7. `explicit-fresh`

**Honor the explicit fresh-assessment request with `--full`.** This is within budget and is an authorized reason to reassess unchanged work. `--full` requests fresh assessment, not deep effort.

```sh
qodo review --base "$REVIEW_BASE" --context-file "$REVIEW_CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Use the same full scope and auto effort. Proposed context:

```json
{
  "decisions": [
    "The user explicitly requests a fresh assessment with --full, within the review budget."
  ],
  "notes": "The current snapshot already has complete compatible auto coverage and settled findings. Nothing changed; this submission is requested fresh scrutiny, not a fixes-only continuation. Test outcomes were not supplied.",
  "recent_work": []
}
```

### Collecting any new submission

Retain its returned operation ID together with the submitted base, commit/tree, scope and context. Populate `operation_id` from that response, then collect the same operation:

```sh
qodo review status "$operation_id" --json
```

Respect polling delays; do not submit another review to check progress. If more stored evidence is needed:

```sh
qodo review status "$operation_id" --extended --json
```

Read the complete inventory, coverage, warnings and reviewer comment. Separate new findings, earlier open findings and settled findings. Acceptance is not completion, and zero new findings alone does not establish readiness. Report missing checks, exclusions, context-delivery gaps and persistence uncertainty separately.

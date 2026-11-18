**Proposals only. No reviews, edits, commits, files or service writes were executed.** I accept the supplied compatibility, identity and base verification.

Below, `qodo` means the verified installed invocation. Proposed context files would be UTF-8 without a BOM, outside every reviewed worktree:

```sh
CONTEXT_DIR=/outside
```

### 1. `milestone`

Submit one **auto** checkpoint now: the slice is coherent and feedback can guide remaining integration. Review the current task changes without arbitrary path restrictions. No `--fast`, `--deep` or `--full`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

Proposed context:

```json
{
  "decisions": [],
  "notes": "A coherent API implementation slice is finished. The worktree is clean after the task commit. Testing was reported, but test commands and pass/fail results were not supplied. Independent integration work remains. Implementation choices, their rationale and specific code locations were not supplied.",
  "recent_work": [
    "Completed the API implementation slice awaiting its first review."
  ]
}
```

Continue useful independent integration work while this single checkpoint runs. Collect at a natural pause; reconcile findings against any subsequent changes.

### 2. `dirty-final`

Run from the **supplied verified task-only clean worktree at the intended commit**, not the original dirty worktree. Review the full candidate scope.

There is no supported committed-only option. Path filtering cannot separate unrelated staged edits in the same file. Do not stash, reset, commit or otherwise alter the original files or index; do not collect the private scratch file.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user requested final review of the committed PR candidate while preserving all original working files and the index.",
    "The coding agent selected the supplied verified clean task-only worktree because ordinary capture in the original worktree would include unrelated changes."
  ],
  "notes": "Review the full committed candidate from the isolated clean worktree. Unrelated staged edits, unstaged work and the private untracked scratch file remain untouched in the original worktree and are outside this review. Test results and implementation rationale were not supplied.",
  "recent_work": [
    "The committed task candidate awaits final assessment; its specific implementation details were not supplied."
  ]
}
```

Verify returned base, commit/tree, scope and omissions before attributing coverage to the PR candidate.

### 3. `already-covered`

**Reuse the completed assessment and hand over; submit nothing.**

The supplied facts establish **Ready locally**: matching snapshot/base/full scope/policy, complete inventory and coverage, settled required findings, and passed tests. Another unchanged assessment has no concrete purpose.

Do not infer successful local-to-PR finding transfer, hosted Qodo status, CI, merge or deployment from this local readiness.

### 4. `trivial`

**Skip automatic review and continue the task.** A behavior-neutral internal-comment typo does not warrant a checkpoint. No command or context submission.

### 5. `report-only`

Review the requested safe **uncommitted working scope**, using auto effort. Do not edit, commit, prepare a PR, dismiss findings or solicit permission to implement fixes.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user requested review of uncommitted code without editing or committing; PR preparation is not requested."
  ],
  "notes": "The requested working scope is safe to collect and has no existing review. Implementation requirements, specific behavior changes and test results were not supplied. This is assessment-only.",
  "recent_work": [
    "The user's current uncommitted changes await their first review; their implementation details were not supplied."
  ]
}
```

Assess and report findings, then stop. Missing test evidence remains unknown even if no findings are returned.

### 6. `light-to-final`

**Submit ordinary auto final review.** The concrete reason is missing ordinary final coverage: a completed light checkpoint alone does not satisfy this handoff request, even for unchanged code.

Keep the same base and full intended scope. Do not automatically add `--full` or escalate to deep.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff.",
    "The coding agent selected default auto effort because the existing purposeful fast checkpoint alone is insufficient final coverage."
  ],
  "notes": "A fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. No completed auto final assessment exists, and the user budget is not exhausted. Test outcomes and finding dispositions were not supplied.",
  "recent_work": []
}
```

Let the Engine determine continuation or fallback. Check actual returned coverage; do not claim ordinary final coverage if only light evidence remains established.

### 7. `explicit-fresh`

**Honor the explicit fresh-assessment request with `--full`, retaining auto effort.** This is authorized and within budget despite existing compatible coverage. `--full` requests freshness, not deeper effort.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Proposed context:

```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full despite existing complete compatible auto coverage."
  ],
  "notes": "The snapshot is unchanged, prior compatible auto coverage is complete, and required findings are settled. The fresh request is within budget. Test results were not supplied.",
  "recent_work": []
}
```

### Collection and pending evidence

For each proposed submission, retain the returned operation ID with its base, snapshot, scope and context. Collect that operation—not another submission:

```sh
qodo review status "$operation_id" --extended --json
```

Here, `operation_id` must come from the acceptance response. Respect polling delays and retention. `--extended` retrieves detail; it does not rerun or deepen assessment.

All proposed new assessments remain **pending**. Acceptance would not establish completion. Before reporting an outcome, inspect:

- Complete finding inventory: introduced and still-open findings, separately from resolved/dismissed.
- Coverage and inventory completeness, exclusions, warnings and `review_agent_comment`.
- Matching reviewed snapshot/base/scope and actual analysis mode.
- Context-delivery limitations and any persistence failures.

Credit Qodo for concerns it actually surfaces; independently assess each against code and context. No finding-status write or implementation is authorized by these proposals.

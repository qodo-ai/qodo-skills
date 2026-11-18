No reviews or commands run. These are proposed actions for the seven independent cases.

For commands below, `qodo` means the verified installed invocation. `$REVIEW_CONTEXT` would point to a case-specific UTF-8 JSON file outside the reviewed changes, containing `decisions`, `notes`, and `recent_work`. I would preserve unknown facts rather than invent implementation details or test results.

### 1. `milestone` — submit an auto checkpoint

This is a useful review moment: a coherent, tested slice is ready, and feedback can guide remaining work. A milestone does not automatically require `--fast`.

Run from the clean task worktree, covering the completed slice against the verified base:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- **`decisions`:** Actual API implementation choices and their known ownership/rationale; none are specified in this scenario.
- **`notes`:** The slice is finished and tested, but test commands and outcomes are unspecified. Independent integration work remains.
- **`recent_work`:** The API implementation slice awaiting its first review.

Continue independent integration work while this operation runs. Its assessment covers the submitted snapshot, not subsequent integration edits. Keep only one automatic checkpoint active.

### 2. `dirty-final` — review the clean candidate worktree

Use the available, verified task-only clean worktree at the intended commit. Do **not** collect from the original dirty worktree: path filtering cannot separate unrelated staged edits within the same file.

Run from that clean worktree, with full intended path scope:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- **`decisions`:** The user requests final review of the committed PR candidate while preserving the original files and index.
- **`notes`:** Identify the intended commit/tree and clean collection location. Unrelated staged, unstaged, and private untracked work is excluded by isolation. Test results are unspecified.
- **`recent_work`:** Describe the candidate’s actual task changes; prior-review history is unspecified.

No stash, reset, additional commit, invented committed-only flag, or inclusion of private scratch contents. Final-review status alone does not justify `--deep` or `--full`.

### 3. `already-covered` — reuse coverage and hand over

**No new submission or context file is needed.** The exact snapshot, base, full scope, and relevant policy already have compatible completed auto coverage, complete inventory, settled required findings, and passing tests.

Report **ready locally**, referencing that assessment. Do not buy another unchanged review or add `--full` merely because this is handoff. This does not establish hosted PR review, CI, or merge readiness.

### 4. `trivial` — skip automatic review

**No review command or context submission.** A behavior-neutral internal-comment typo does not warrant an automatic checkpoint while work continues.

### 5. `report-only` — review working changes without modifying them

Review the requested safe working scope as-is, retaining intended uncommitted changes rather than creating a commit:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- **`decisions`:** The user explicitly authorizes review only, with no edits or commits.
- **`notes`:** Describe the requested working scope and relevant behavior/guards from the session. Test outcomes are unspecified. PR preparation is not requested.
- **`recent_work`:** Describe the uncommitted changes awaiting review.

Identify coverage by the submitted working-tree snapshot, not HEAD alone. Assess and report findings; do not edit, commit, write dismissals, prepare a PR, or solicit implementation permission.

### 6. `light-to-final` — obtain ordinary final coverage

Proceed despite unchanged code. The concrete reason is **missing ordinary final coverage**: the completed `--fast` checkpoint alone is insufficient.

Submit full intended scope with default auto effort:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- **`decisions`:** The user now requests ordinary final review.
- **`notes`:** The earlier full-snapshot checkpoint used `--fast`; code and evidence are unchanged. No completed auto final assessment exists. Test and finding dispositions are otherwise unspecified.
- **`recent_work`:** `[]` — no changes since the checkpoint.

Do not retain `--fast`, escalate to `--deep`, or add `--full` automatically. Let the Engine determine continuation eligibility, then verify that returned coverage satisfies ordinary final review rather than merely citing the earlier light checkpoint.

### 7. `explicit-fresh` — honor the requested fresh assessment

The explicit request, within budget, justifies another assessment even though compatible coverage already exists:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --full --async --json
```

Keep the same base and full intended scope. `--full` requests a fresh assessment, not deep effort.

Context:
- **`decisions`:** The user explicitly requests a fresh assessment with `--full`.
- **`notes`:** Existing compatible auto coverage is complete and required findings are settled; the snapshot and evidence are unchanged. Test outcomes are unspecified here.
- **`recent_work`:** `[]`.

### Collect and assess every submitted operation

Retain each returned operation ID with its submitted base, snapshot, scope, and context. Poll that operation—not a new submission—respecting returned delays:

```sh
qodo review status "$OPERATION_ID" --extended --json
```

Read Qodo’s complete findings, `review_agent_comment`, warnings, inventory completeness, coverage, exclusions, and context-delivery metadata. Separate introduced and earlier open findings from resolved/dismissed findings. Recheck findings against newer code where work continued.

Acceptance or zero new findings alone does not establish readiness. Report missing coverage, unresolved obligations, verification gaps, and persistence or local-to-PR limitations separately.

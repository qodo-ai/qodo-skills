All commands below are proposals only. `qodo` means the verified installed invocation; `$REVIEW_CONTEXT` means a case-specific UTF-8 JSON context file outside the reviewed worktree. Compatibility, identity and help checks are already satisfied.

### 1. `milestone`

Submit an **auto-effort asynchronous checkpoint now**. The slice is coherent, tested and unreviewed; remaining independent work makes this a useful feedback point. A checkpoint does not automatically mean `--fast`.

Review the current task snapshot without a path restriction:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- `decisions`: Actual implementation choices and their known owners/reasons; none are specified here.
- `notes`: The API slice is task-committed and the worktree is clean. Tests were run, but their outcome is not supplied. Independent integration work remains.
- `recent_work`: `["Implemented the coherent API slice awaiting its first review."]`

Continue independent integration work while this runs. Retain the reviewed snapshot identity and reassess findings against current code when collecting the result. This checkpoint will not cover subsequent changes automatically.

### 2. `dirty-final`

Run from the **verified task-only clean worktree at the intended commit**, not the original dirty worktree. Review all intended candidate paths.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Use auto effort: final-review status alone does not justify `--deep` or `--full`.

Context:
- `decisions`: The user requests review of the committed PR candidate while preserving the original files and index.
- `notes`: Collection is from the verified clean candidate worktree. Unrelated staged, unstaged and private untracked files remain untouched in the original worktree. Candidate-specific requirements, decisions and check evidence belong here; test outcomes are unspecified.
- `recent_work`: Describe the actual candidate changes; their implementation details are not supplied here.

Do not invent a committed-only flag, use path filtering to separate edits within the same file, or stash/reset/commit unrelated work. Isolation is what makes this collection match the candidate.

### 3. `already-covered`

**Reuse the completed assessment and hand over the work.** No review command or new context submission is needed.

The exact snapshot, base, full scope and relevant policy are covered; the complete inventory is settled and tests passed. Report **ready locally**. Do not turn that into a claim about hosted review, CI, merge or deployment.

### 4. `trivial`

**Do not submit an automatic review.** Continue the task. A behavior-neutral internal-comment typo does not warrant a review by itself.

No command or context submission is needed.

### 5. `report-only`

Review the requested safe **uncommitted working scope**, without committing or editing:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Context:
- `decisions`: The user explicitly requests review only, with no edits or commits and no PR preparation.
- `notes`: The requested working scope is safe to collect. Include available requirements, guards and check evidence without inventing missing details or test results.
- `recent_work`: `["Uncommitted code awaiting its first review; implementation details are not supplied in this scenario."]`

Assess and report findings with supporting code references. Do not apply fixes, store dismissals, or ask to convert this report-only request into implementation.

### 6. `light-to-final`

**Proceed with ordinary auto final review.** The concrete reason is missing ordinary final coverage: the completed `--fast` checkpoint alone is insufficient, even though it covered every intended path and nothing changed.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --async --json
```

Keep the same base and full intended path scope. Omit `--fast`, `--deep` and `--full`; final-review status alone does not require a forced fresh assessment.

Context:
- `decisions`: Preserve prior actual session decisions and record the user’s ordinary final-review request.
- `notes`: The prior full-scope checkpoint used fast effort. Code and evidence are unchanged. Ordinary final coverage remains required; do not invent new test results.
- `recent_work`: `[]`

Let the Engine determine continuation/reuse eligibility and inspect its actual coverage. Do not treat reuse of light evidence alone as proof that ordinary final coverage was established.

### 7. `explicit-fresh`

Honor the explicit, within-budget request for a fresh assessment:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$REVIEW_CONTEXT" --full --async --json
```

Use full intended path scope and **auto effort**. `--full` requests fresh assessment; it does not imply `--deep`.

Context:
- `decisions`: The user explicitly requests fresh assessment with `--full`.
- `notes`: Compatible coverage already exists and findings are settled. Nothing changed; the new submission is justified by the user’s request, not by missing coverage.
- `recent_work`: `[]`

Preserve the existing substantive session context rather than replacing it with only the fresh-review request.

### Collecting any new submission

Retain its returned operation ID with the base, snapshot, scope and context, then collect that same operation:

```sh
qodo review status "$operation_id" --json
```

Respect returned polling delays. Acceptance is not completion. Inspect warnings, context delivery, coverage and the complete finding inventory—including earlier open findings—before claiming readiness. Do not start another assessment merely to check progress.

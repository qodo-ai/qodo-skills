**Proposals only; no reviews or other commands executed.**

For all submissions below:
- Reuse the verified CLI compatibility, identity and base; no redundant setup.
- `$BASE` is `1111111111111111111111111111111111111111`.
- Each `$CTX_*` names a complete UTF-8 context file **outside the reviewed checkout**. Include no private scratch content or invented implementation facts.
- Ordinary auto effort means omitting both `--fast` and `--deep`.

### 1. `milestone`

**Review now:** the tested, coherent slice is a useful checkpoint, and feedback can inform remaining integration work.

From the current clean task checkout, without temporary path restrictions:

```sh
qodo review --base "$BASE" --context-file "$CTX_MILESTONE" --async --json
```

Context:
- `decisions`: Include actual recorded implementation choices and ownership; none are supplied by this fixture, so invent none.
- `notes`: “The coherent API slice is implemented and its relevant tests passed. Independent integration work remains; this is not completed-work handoff. Exact test commands and implementation details are not supplied in this fixture.”
- `recent_work`: `["Completed the API implementation slice awaiting its first assessment."]`

Retain the operation ID and submitted base, commit/tree, scope and context. Continue independent integration work while it runs. Collect at a natural pause:

```sh
qodo review status <operation-id> --json
```

The checkpoint covers its submitted snapshot—not integration changes made afterward.

### 2. `dirty-final`

**Use the available verified, task-only clean worktree at the intended commit.** The installed collector has no committed-only option, and a task commit does not exclude subsequent unrelated edits.

Run from that clean worktree:

```sh
qodo review --base "$BASE" --context-file "$CTX_FINAL" --async --json
```

Include every intended candidate path; do not add checkpoint-only restrictions.

Context:
- `decisions`: `["The user requested review of the committed PR candidate only, preserving the original files and index."]`
- `notes`: “Collection uses the verified clean task-only worktree at the intended candidate commit. The original checkout contains unrelated staged and unstaged changes plus private untracked scratch content; none is included. Test results are not supplied.”
- `recent_work`: Describe the candidate’s actual substantive changes; their details are not supplied here.

Do **not** reset, stash, alter the index, create another commit, or collect from the dirty checkout. Verify returned snapshot and coverage against the candidate. A completed assessment alone does not establish readiness without relevant checks and settled required findings.

### 3. `already-covered`

**Reuse the completed assessment and hand over; submit nothing.**

The fixture establishes exact snapshot/base/full-scope compatibility, complete inventory and coverage, settled required findings, and passing tests. No fresh evidence or user request justifies another assessment.

Report: **Ready locally**, citing the existing assessment and checks. Retain its operation/checkpoint and finding references. No new context submission is needed.

This does not establish hosted PR review, successful finding persistence, CI, merge or deployment. Verify those separately only when relevant and authorized.

### 4. `trivial`

**Continue coding without automatic review.**

An internal comment typo with no behavior change does not justify a checkpoint. No review command, commit or context file is needed now. Include the correction in later context if it matters to a substantive submission; do not invent a behavioral impact.

### 5. `report-only`

**Review the safe requested working scope without editing or committing.**

```sh
qodo review --base "$BASE" --context-file "$CTX_REPORT_ONLY" --async --json
```

Use the requested scope, retaining any explicit user path arguments. Do not invent narrower restrictions or prepare a PR.

Context:
- `decisions`: `["The user requested review of uncommitted code only, with no edits or commits."]`
- `notes`: “The requested working scope is safe for ordinary collection. This assessment includes uncommitted changes; no PR preparation is requested. Verification results and implementation constraints are not supplied.”
- `recent_work`: Describe the actual uncommitted changes without asserting unspecified behavior or fixes.

Collect and independently assess Qodo’s findings. Explain impact, supporting evidence, uncertainty and recommended action while preserving each finding’s ID, category and action level. **Stop after reporting.** Do not apply fixes, store dismissals, or ask to convert this into implementation.

Identify the reviewed working-tree snapshot; HEAD alone cannot identify uncommitted content. Do not describe it as a certified committed PR candidate.

### 6. `light-to-final`

**Submit ordinary auto review.** State the reason first: “The completed fast checkpoint does not provide the required ordinary final coverage.”

```sh
qodo review --base "$BASE" --context-file "$CTX_LIGHT_TO_FINAL" --async --json
```

Keep the same intended base and full path scope. Do not add `--deep` merely because this is final review. Do not add `--full` automatically: the user requested ordinary final review, not a fresh full assessment.

Context:
- Preserve actual decisions.
- `notes`: “A purposeful fast checkpoint completed for this exact full snapshot. No code or evidence changed afterward. Ordinary final assessment is now required; prior findings and their stored outcomes remain relevant.”
- `recent_work`: `["No code changes since the completed fast checkpoint."]`

Let the Engine determine continuation or reuse eligibility. Inspect the returned mode, effort and coverage; do not promise a new pass or presume that reuse of light evidence satisfies ordinary final requirements. If required final coverage remains missing, report that gap rather than claim readiness.

### 7. `explicit-fresh`

**Honor the fresh-assessment request within the stated budget.**

```sh
qodo review --base "$BASE" --context-file "$CTX_FRESH" --full --async --json
```

Retain the same base, snapshot and full scope. `--full` requests fresh assessment; it does **not** request deep effort.

Context:
- `decisions`: `["The user explicitly requested a fresh assessment with --full despite existing compatible auto coverage."]`
- `notes`: “Existing auto coverage is complete and required findings are settled. Nothing changed. The fresh request is within the user’s review budget.”
- `recent_work`: `["No code changes since the previous completed assessment."]`

Collect this operation rather than resubmit to check progress.

### Result handling for every new submission

Acceptance is not completion. Poll the retained operation, respecting returned delays and retention. Read warnings, `review_agent_comment`, complete finding inventory, coverage and available context-delivery metadata. Assess both introduced and earlier still-open findings; distinguish resolved and dismissed findings.

Use supported `status <operation-id> --extended --json` for retained detail—not another assessment. Missing metadata remains unknown. Report coverage, unresolved obligations, persistence and local-to-PR limitations separately. Do not infer model, timing, reviewer-consumption or successful-storage claims from absent evidence.

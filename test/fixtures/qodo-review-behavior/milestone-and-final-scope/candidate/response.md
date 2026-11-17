Proposals only: no reviews, files, commits, or service writes executed.

Compatibility, identity, help and base verification are already satisfied. Here, `qodo` means the resolved installed CLI. Proposed bindings:

```sh
BASE=1111111111111111111111111111111111111111
CTX_DIR=/outside
```

Context files would remain outside reviewed changes. Each would contain `decisions: []` because no implementation decisions or rationale were supplied, plus the case-specific `notes` and `recent_work` below.

### 1. `milestone`

Submit an **auto, asynchronous checkpoint now**, covering the complete committed API slice without path restrictions. Neither quick nor deep effort is justified.

```sh
qodo review --base "$BASE" --context-file "$CTX_DIR/milestone.json" --async --json
```

Context:
- **notes:** “The author completed and tested a coherent API implementation slice. Test commands and outcomes were not supplied; passing tests are not established. The worktree is clean after the task commit. Independent integration work remains.”
- **recent_work:** `["Completed the substantive API implementation slice; this slice has not previously been reviewed."]`

Continue useful independent integration work while this runs. Its result covers the captured snapshot—not subsequent changes.

### 2. `dirty-final`

Run from the **available, verified task-only clean worktree at the intended commit**, not the original dirty worktree. Review every intended candidate path.

```sh
qodo review --base "$BASE" --context-file "$CTX_DIR/dirty-final.json" --async --json
```

Context:
- **notes:** “Review the committed PR candidate from the verified clean task-only worktree. The original worktree contains unrelated staged and unstaged edits and a private untracked scratch file; none belongs in this review. Test outcomes and implementation details were not supplied.”
- **recent_work:** `["Committed task changes forming the PR candidate; the prior-review delta was not supplied."]`

Do not reset, stash, alter the index, commit unrelated edits, or invent a committed-only flag. Final status alone does not justify `--deep` or `--full`.

### 3. `already-covered`

**Reuse the completed assessment and hand off; submit nothing.**

The supplied facts establish local readiness: exact snapshot, base, full scope and policy covered; complete inventory and coverage; required findings settled; tests passed.

Do not infer hosted Qodo-clean status, successful finding handoff, CI success or deployment readiness from local readiness.

### 4. `trivial`

**Continue without review.** This behavior-neutral comment typo does not warrant an automatic assessment. No command or context submission.

### 5. `report-only`

Review the requested safe **uncommitted working scope**, without commits, edits or PR preparation.

```sh
qodo review --base "$BASE" --context-file "$CTX_DIR/report-only.json" --async --json
```

Context:
- **notes:** “The user requests review only of the current uncommitted code. The requested working scope is safe to collect. Editing, committing and PR preparation are outside the request. Implementation details and test results were not supplied.”
- **recent_work:** `["Uncommitted changes awaiting their first review; specific behavior changes were not supplied."]`

Independently assess and report findings, then stop. Do not apply fixes, store dismissals, or solicit implementation permission.

### 6. `light-to-final`

**Proceed with ordinary auto final review.** Concrete reason: the completed light checkpoint does not establish ordinary final coverage, even though the snapshot is unchanged.

```sh
qodo review --base "$BASE" --context-file "$CTX_DIR/light-to-final.json" --async --json
```

Use the same exact base and full intended scope. Omit `--fast`, `--deep` and `--full`; let the Engine determine eligible continuation or fallback.

Context:
- **notes:** “A purposeful fast checkpoint completed for this full intended snapshot. No code or evidence changed afterward. Ordinary final assessment is now requested and remains missing. Earlier finding dispositions and test outcomes were not supplied.”
- **recent_work:** `[]`

Do not describe this as a fixes-only round or manufacture intervening changes.

### 7. `explicit-fresh`

Honor the explicit, within-budget request for a **fresh full assessment at auto effort**.

```sh
qodo review --base "$BASE" --context-file "$CTX_DIR/explicit-fresh.json" --full --async --json
```

Preserve the existing base and full scope.

Context:
- **notes:** “The unchanged current snapshot already has complete compatible auto coverage and settled findings. The user explicitly requests a fresh full assessment within budget. Test outcomes were not supplied.”
- **recent_work:** `[]`

`--full` requests freshness, not deep effort. Existing coverage does not override this explicit request.

### Collection and pending evidence

For every accepted submission, retain its actual operation ID, base, commit/tree, scope and submitted context. Poll that same operation, respecting returned delays:

```sh
qodo review status "$operation_id" --extended --json
```

Read warnings, reviewer commentary, context-delivery metadata, coverage and the complete finding inventory—including earlier open findings. Reconcile any changes made while review was running.

No submissions occurred here, so there are no operation IDs or new assessment results. Cases requiring submissions remain pending; acceptance alone would not establish completion, passing tests, successful persistence or local readiness.

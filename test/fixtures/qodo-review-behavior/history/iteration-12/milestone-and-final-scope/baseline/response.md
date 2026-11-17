These are proposals only; I have not run reviews or changed files. Compatibility and identity are already established.

Below, `qodo` means the trusted installed invocation. `$CONTEXT_DIR` would contain complete context files **outside all reviewed checkouts**. Each file would have `decisions`, `notes`, and `recent_work`; I would preserve known implementation decisions and leave unknown details explicit rather than invent them.

### 1. `milestone`

Submit one **auto**, asynchronous checkpoint now. The coherent, tested slice is a useful review boundary; being midwork does not automatically justify `--fast`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

- **Scope:** Full task changes through the current clean task commit, without temporary path restrictions.
- **Context:** API implementation slice completed and tested; test commands and outcomes are unspecified, so I would not claim they passed. Independent integration work remains.
- **`recent_work`:** `["Completed the coherent API implementation slice awaiting its first review."]`

Retain the operation ID and submitted snapshot, continue independent integration work, and collect at a natural pause. This checkpoint cannot certify integration changes made afterward.

### 2. `dirty-final`

Review from the **verified clean, task-only worktree at the intended commit**, not the original dirty checkout.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

- **Scope:** Every intended PR-candidate path relative to the verified base.
- **Context:** The user requested committed-candidate review and preservation of the original files and index. Collection uses the verified clean worktree; unrelated staged edits, unstaged work, and private scratch content are excluded. Test results are unspecified.
- **`recent_work`:** Describe the candidate’s actual changes since its previous review; that history is not supplied here.

No invented committed-only flag, file-level filtering of the mixed file, reset, stash, or additional commit. Ordinary capture in the original checkout would review the wrong scope.

### 3. `already-covered`

**Do not submit another review.** Reuse the completed compatible auto assessment: the exact intended snapshot, base, full scope, and policy are covered; inventory is complete, required findings are settled, and tests passed.

Report **ready locally**, with the existing review reference. This does not establish hosted PR-review status, CI, or merge readiness.

### 4. `trivial`

**Skip automatic review** and continue the task. A behavior-neutral internal-comment typo does not warrant a checkpoint on these facts. No review command or context submission is needed.

### 5. `report-only`

Review the requested safe working scope directly, without editing or committing.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

- **Scope:** The requested working changes, including uncommitted code.
- **Context:** The user explicitly requested report-only review: no edits, commits, or PR preparation. Requirements, implementation decisions, and test outcomes not supplied remain unknown.
- **`recent_work`:** Describe the actual uncommitted implementation changes; do not invent their content.

Assess and report findings, then stop. Do not apply fixes, store dismissals, or solicit implementation permission. The reviewed dirty snapshot is not a committed PR candidate.

### 6. `light-to-final`

**Proceed with ordinary auto final review.** The concrete reason is missing ordinary final coverage: the completed `--fast` checkpoint alone is insufficient, even though it covered the full unchanged snapshot.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

- **Scope:** Full intended change, with no temporary path restrictions.
- **Context:** A full-scope fast checkpoint completed; neither code nor evidence changed afterward. The user now requests ordinary final coverage. Test outcomes and finding dispositions are not otherwise specified.
- **`recent_work`:** `[]`

Omit `--fast`, `--deep`, and `--full`. Let the Engine qualify continuation or reuse, then inspect its actual effort and coverage; do not relabel the earlier light checkpoint as sufficient final coverage.

### 7. `explicit-fresh`

Honor the explicit, in-budget fresh-assessment request.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

- **Scope:** The same complete intended snapshot and base.
- **Context:** Compatible auto coverage already exists with settled findings, but the user explicitly requested a fresh assessment. Nothing changed; test outcomes are unspecified.
- **`recent_work`:** `[]`

`--full` requests fresh assessment, **not deep effort**. Keep effort auto.

### Collection and handoff

For each accepted submission, collect its returned operation ID rather than submit again:

```sh
qodo review status <returned-operation-id> --json
```

Respect returned polling delays. For additional stored detail, use supported `--extended` on that same status request.

Read Qodo’s complete result, warnings, reviewer comment, coverage, and both new and earlier-open findings. Acceptance is not completion, and zero new findings is not readiness. Report missing coverage or verification explicitly; make no fixes or finding-status writes beyond the applicable authorization.

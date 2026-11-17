**Proposals only—nothing executed or written.** These are independent cases. Compatibility, identity and base verification are already satisfied.

For the commands below, `qodo` means the verified installed invocation. Bind the known base explicitly:

```sh
REVIEW_BASE=1111111111111111111111111111111111111111
```

Each context filename below represents a proposed UTF-8 JSON file **outside all reviewed worktrees**, not a file already created.

### 1. `milestone`

Submit now: the coherent, tested slice is a useful checkpoint. Use **auto**, not automatically `--fast` or `--deep`.

```sh
qodo review --base "$REVIEW_BASE" --context-file /outside-worktrees/milestone.json --async --json
```

**Scope:** All current task changes against the verified base, from the clean task commit. No invented path restrictions.

**Context:**
```json
{
  "decisions": [],
  "notes": "This checkpoint covers a coherent API implementation slice. Independent integration work remains. The slice was tested, but test names and outcomes were not supplied; passing results are not established. Detailed API requirements and implementation choices were not supplied.",
  "recent_work": [
    "Completed and committed the previously unreviewed API implementation slice."
  ]
}
```

Retain the accepted operation and submitted snapshot, then continue useful independent integration work. Collect feedback at a natural pause and recheck findings against any intervening changes. This checkpoint does not certify later integration work.

### 2. `dirty-final`

Use the **already verified, task-only clean worktree at the intended commit**. The installed collector has no committed-only option.

Run there:

```sh
qodo review --base "$REVIEW_BASE" --context-file /outside-worktrees/dirty-final.json --async --json
```

**Scope:** The complete committed PR candidate against the verified base, with no temporary path restrictions. Ordinary capture in this clean worktree excludes the unrelated original edits and private scratch file through isolation.

Do not reset, stash, commit, or otherwise modify the original working files or index.

**Context:**
```json
{
  "decisions": [
    "The user requested final review of the committed PR candidate while preserving the original working files and index.",
    "The agent selected the verified task-only clean worktree because the installed collector has no committed-only option."
  ],
  "notes": "The isolated worktree is verified at the intended commit. The original worktree contains unrelated staged, unstaged and untracked material, which is outside this review. Test results and implementation details were not supplied.",
  "recent_work": [
    "The committed task changes form the PR candidate; a previous-review delta was not supplied."
  ]
}
```

Use auto. Final-review status alone justifies neither deep effort nor `--full`.

### 3. `already-covered`

**Do not submit another assessment.** Reuse the completed compatible auto coverage: the exact intended snapshot, base, full scope and policy match; inventory and coverage are complete; required findings are settled; tests passed.

Hand off as **ready locally**, identifying the existing review and covered snapshot. No new context submission is needed. This does not independently establish hosted-review, CI or merge readiness.

### 4. `trivial`

**Do not automatically review.** Continue the task. An internal-comment typo with no behavior change does not warrant a checkpoint by itself.

No command or context submission.

### 5. `report-only`

Review the requested safe **uncommitted working scope**, without edits or commits:

```sh
qodo review --base "$REVIEW_BASE" --context-file /outside-worktrees/report-only.json --async --json
```

Use auto; do not isolate away the requested working changes or prepare a PR.

**Context:**
```json
{
  "decisions": [
    "The user requested review of uncommitted code without editing or committing."
  ],
  "notes": "Review the requested working scope, which is safe to collect. This is report-only; PR preparation is not requested. Implementation details and test results were not supplied.",
  "recent_work": [
    "Uncommitted changes in the requested working scope await their first review."
  ]
}
```

Assess the findings against the code and report practical impact, evidence and recommendations. Then stop—no implementation, stored dismissals, or solicitation to expand the task into fixes.

### 6. `light-to-final`

**Proceed with ordinary auto final review.** The concrete reason is missing required final coverage: an unchanged full-scope `--fast` checkpoint alone is not ordinary final coverage.

```sh
qodo review --base "$REVIEW_BASE" --context-file /outside-worktrees/light-to-final.json --async --json
```

**Scope:** The complete intended snapshot. Omit `--fast`, `--deep` and `--full`. Let the Engine determine continuation, reuse or fallback; do not presume the fast checkpoint satisfies the requested final assessment.

**Context:**
```json
{
  "decisions": [
    "The user requested ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. No completed auto final assessment exists. Test outcomes and finding dispositions were not supplied.",
  "recent_work": []
}
```

### 7. `explicit-fresh`

Honor the explicit, within-budget request. A fresh assessment is justified **by the request**, despite unchanged compatible coverage.

```sh
qodo review --base "$REVIEW_BASE" --context-file /outside-worktrees/explicit-fresh.json --full --async --json
```

**Scope:** The same full intended snapshot and verified base. Keep auto effort: `--full` requests freshness, not deep effort.

**Context:**
```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full within the review budget."
  ],
  "notes": "The unchanged current snapshot already has complete compatible auto coverage and settled findings. No new code or evidence prompted this submission. Test outcomes were not supplied.",
  "recent_work": []
}
```

### Collection for every proposed submission

Retain the returned operation ID with its base, snapshot, scope and context, then collect that same operation:

```sh
qodo review status <returned-operation-id> --json
```

Respect polling delays; do not resubmit to check progress. Validate available result identities, omissions, coverage, context delivery and the complete finding inventory. Acceptance is not completion, and zero new findings alone does not establish readiness. Any unavailable verification remains explicit.

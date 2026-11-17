I would submit reviews for **1, 2, 5, 6 and 7**, reuse existing coverage for **3**, and skip review for **4**. Nothing would be run here.

For ordinary submissions below, use the verified installed invocation and a case-specific UTF-8 context file outside the reviewed worktrees:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT" --async --json
```

`CONTEXT` denotes that case’s prepared file. Omitting `--fast` and `--deep` selects **auto**; auto does not promise a fixed tier or spending cap.

### 1. `milestone`

**Submit an auto checkpoint now.** The coherent, tested API slice is a useful review point; neither quick nor deep effort was requested.

- **Scope:** The complete task change against the supplied base, from the clean task worktree. No arbitrary path restriction.
- **While pending:** Continue independent integration work. Retain the submitted snapshot and operation ID; the result will not certify subsequent changes.

Context:
```json
{
  "decisions": [],
  "notes": "The coherent API implementation slice is finished and was tested. Test commands and outcomes were not supplied, so passing checks are not established. Independent integration work remains. Implementation requirements, guards and decision rationale were not supplied.",
  "recent_work": ["Completed the API implementation slice awaiting its first review."]
}
```

### 2. `dirty-final`

**Run the ordinary command from the verified task-only clean worktree at the intended commit.**

The installed CLI has no committed-only collection option. Ordinary capture in the original worktree would include unrelated changes, including edits within the same file. Path filtering cannot safely separate those edits.

- **Scope:** The full committed PR candidate against the supplied base.
- **Preservation:** Leave the original files and index untouched. No stash, reset, extra commit, or collection of the private scratch file.

Context:
```json
{
  "decisions": [
    "The user requested review of the committed PR candidate while preserving the original files and index.",
    "The coding agent selected the verified task-only clean worktree because committed-only collection is unavailable."
  ],
  "notes": "Review the full intended committed candidate. Unrelated staged, unstaged and private untracked work in the original worktree is outside scope and is not being collected. Implementation details, prior-review changes and check results were not supplied.",
  "recent_work": []
}
```

Verify the returned snapshot and coverage match the intended commit before treating this as candidate coverage.

### 3. `already-covered`

**Hand over as ready locally; submit nothing.**

The exact intended snapshot, base, full scope and relevant policy already have compatible completed auto coverage, complete inventory, settled required findings and passing tests. Nothing justifies another assessment.

No new context file is needed. Reference the existing assessment and checks. Do not extend this conclusion to hosted review, CI, merge or release readiness.

### 4. `trivial`

**Continue the task without an automatic review.**

A comment-only typo correction does not warrant a checkpoint. No command or review context is needed now.

### 5. `report-only`

**Submit the ordinary auto command for the requested uncommitted scope.**

- **Scope:** The safe requested working changes against the supplied base.
- **Authority:** No edits, commits, PR preparation or stored finding-status changes.

Context:
```json
{
  "decisions": [
    "The user requested review of uncommitted code without editing or committing."
  ],
  "notes": "This is report-only review. The requested working scope is safe to collect. No existing assessment is available. Implementation details and check results were not supplied.",
  "recent_work": ["Uncommitted changes await their first requested review; their specific behavior was not described."]
}
```

After collection, independently assess the findings and report them, then stop. Do not solicit permission to turn this into implementation. Working-scope coverage is not certification of a future committed PR candidate.

### 6. `light-to-final`

**Submit an ordinary auto final assessment.**

The concrete reason is **missing ordinary final coverage**: the completed `--fast` checkpoint alone does not satisfy this handoff request, despite unchanged code.

- Use the ordinary command, with neither depth flag.
- Keep the same base and full intended scope.
- Do **not** add `--full` merely because this is final review.
- Let the Engine qualify continuation and report its actual `full`, `incremental` or `reused` outcome; verify that required final coverage is established.

Context:
```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. No completed ordinary auto final assessment exists. Check results and finding dispositions were not supplied.",
  "recent_work": []
}
```

### 7. `explicit-fresh`

**Honor the explicit fresh-assessment request within the stated budget:**

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT" --full --async --json
```

Keep the same full scope and **auto effort**. `--full` requests a fresh assessment; it does not mean deep effort.

Context:
```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full within the review budget."
  ],
  "notes": "The current snapshot already has complete compatible auto coverage and settled findings. Nothing changed and no new evidence appeared. The new assessment is requested explicitly, not needed because prior coverage expired. Check results were not supplied.",
  "recent_work": []
}
```

### Collecting submitted reviews

Retain each returned operation ID with its base, snapshot, scope and context. Poll that operation rather than submitting again:

```sh
qodo review status "$OPERATION_ID" --json
```

Respect returned polling delays and retention. Acceptance is not completion. Validate result identity, coverage, omissions, context delivery and the complete finding inventory—including earlier open findings—before reporting an outcome. Claim **ready locally** only when the intended snapshot has required completed coverage, required findings are settled, and relevant checks passed.

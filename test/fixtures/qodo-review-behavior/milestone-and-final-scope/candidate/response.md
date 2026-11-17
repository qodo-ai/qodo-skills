## Shared setup

These are proposed actions only; I would run nothing in this evaluation.

Use the supplied compatible CLI, verified identity and advertised flags. Bind the exact base:

```sh
base=1111111111111111111111111111111111111111
```

For each new submission, bind `$ctx` to a fresh UTF-8 JSON context file outside the reviewed repository. Include `decisions`, `notes` and `recent_work`; never include private scratch contents. Omit `--fast` and `--deep` for auto effort.

Retain each accepted operation ID and its submitted snapshot, base, scope and context. Collect with:

```sh
qodo review status "$operation_id" --json
```

An accepted submission is not a completed review. Respect returned polling delays and collect the existing operation rather than submit again.

## 1. `milestone`

**Submit one auto checkpoint now.** The coherent, tested slice is unreviewed, and feedback can guide remaining integration work. No additional commit is needed.

Run in the current clean worktree, without path restrictions:

```sh
qodo review --base "$base" --context-file "$ctx" --async --json
```

Proposed context:

```json
{
  "decisions": [],
  "notes": "A coherent API implementation slice is committed and the worktree is clean. The author reports that it was tested; test commands and pass/fail results were not supplied. Independent integration work remains. No additional implementation decisions or rationale were supplied.",
  "recent_work": [
    "Completed the coherent API implementation slice awaiting its first review."
  ]
}
```

Continue useful independent integration work while the checkpoint runs. At a natural pause, collect it and reassess findings against any subsequently changed code. This checkpoint cannot certify newer integration changes.

## 2. `dirty-final`

**Use the available verified task-only clean worktree at the intended commit.** Ordinary collection in the original worktree would contaminate the assessment, including same-file staged edits and private untracked material. A task-only commit alone would not prevent that.

Leave the original worktree and index untouched: no reset, stash, staging, committing or scratch-file removal. Run in the isolated clean worktree:

```sh
qodo review --base "$base" --context-file "$ctx" --async --json
```

Use the full candidate scope with no path arguments. Do not invent a committed-only flag.

Context would state:

- **Decisions:** The user requested review of the committed PR candidate and preservation of the original files and index. The agent selected the verified clean worktree because installed collection lacks a committed-only mode.
- **Notes:** Identify the actual candidate commit and verified clean tree from existing task state. Explain that unrelated staged, unstaged and private untracked work remains outside this checkout. Test results are unspecified.
- **Recent work:** The committed candidate is awaiting final assessment; isolation introduced no code changes.

Verify that returned base, commit/tree and coverage match this candidate. Local assessment does not establish hosted PR handoff, successful finding persistence or passing tests.

## 3. `already-covered`

**Do not submit another review.** Reuse the completed compatible auto assessment.

Reconcile its recorded commit/tree, exact base and unrestricted scope with the intended handoff. The fixture already establishes complete inventory and coverage, settled required findings and passing tests.

Report: **Ready locally using existing completed coverage; no additional assessment needed.**

Do not imply that hosted PR review, CI, publication or other downstream gates succeeded.

## 4. `trivial`

**Continue the task without an automatic review.** This is a behavior-neutral internal-comment typo, not a substantive checkpoint or completed-work handoff.

No Qodo command or review context is needed. Do not manufacture a checkpoint because an edit occurred.

## 5. `report-only`

**Review the requested working scope directly, without editing or committing.** The fixture establishes that collection is safe. Use auto effort:

```sh
qodo review --base "$base" --context-file "$ctx" --async --json
```

Collect the full requested working scope; no narrower path restriction was supplied.

Proposed context:

```json
{
  "decisions": [
    "The user explicitly requested review of uncommitted code without edits or commits; PR preparation is not requested."
  ],
  "notes": "The requested working scope is safe to collect. This assessment covers the submitted working snapshot, not a committed PR candidate. Test execution and results were not supplied.",
  "recent_work": [
    "Uncommitted changes are awaiting their first review; implementation details were not supplied."
  ]
}
```

After collecting, independently assess and report all material findings. Do not fix code, commit, write dismissals or solicit permission to convert this report-only request into implementation. Unknown tests prevent a claim that relevant checks passed.

## 6. `light-to-final`

**Proceed with one ordinary auto final assessment.**

The concrete reason is missing required final coverage: an unchanged purposeful `--fast` checkpoint alone is not ordinary final coverage. Reuse does not eliminate this requirement.

Keep the same base and full intended path scope:

```sh
qodo review --base "$base" --context-file "$ctx" --async --json
```

Do not retain `--fast`, escalate to `--deep` merely because this is final, or add `--full` automatically.

Context would record:

- **Decisions:** The user now requests ordinary final review before handoff.
- **Notes:** The prior full-path checkpoint requested fast effort; no code or evidence changed afterward. Preserve its actual findings and verification evidence.
- **Recent work:** An empty array—no implementation work occurred since that checkpoint.

Let the Engine determine continuation eligibility. Inspect the returned effort, analysis mode and coverage rather than promise fresh execution or sufficient reuse in advance. If returned evidence still does not establish ordinary final coverage, report the gap rather than readiness.

## 7. `explicit-fresh`

**Honor the explicit fresh-assessment request.** Compatible existing coverage would normally be reused, but the user specifically requested `--full` within budget.

```sh
qodo review --base "$base" --context-file "$ctx" --full --async --json
```

Keep the same full intended scope and auto effort. `--full` requests a fresh assessment; it does not mean deep effort.

Context would record the user’s request, unchanged snapshot and existing settled coverage. Use `recent_work: []`; do not invent fixes or new evidence. Collect and verify the actual result before claiming the requested fresh assessment completed.

## Result evidence

For every submitted review, inspect warnings, `review_agent_comment`, inventory completeness, coverage completeness, exclusions and context-delivery metadata. Assess both introduced and still-open findings; report resolved and dismissed findings separately. Preserve original IDs and reported levels.

Zero new findings alone is not readiness. Missing verification, incomplete coverage or unresolved required findings must remain visible. No model, timing, spending or persistence outcome is assumed.

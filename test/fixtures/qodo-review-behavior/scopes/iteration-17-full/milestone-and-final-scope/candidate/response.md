**No reviews or commands were run.** These are independent scenarios. All submissions use the verified base literally and the resolved installed `qodo` invocation. Context-file paths below are illustrative files outside the reviewed checkout.

Auto effort means omitting both `--fast` and `--deep`. Final-review status alone does not justify deep or `--full`.

### 1. `milestone`

Submit one **auto, asynchronous checkpoint** covering the coherent implementation slice from the clean task commit. No artificial path restriction is needed.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/outside-checkout/milestone.json" --async --json
```

Context:

```json
{
  "decisions": [],
  "notes": "A coherent API implementation slice is finished and was tested. Test commands and results were not supplied, so passing tests are not established. Independent integration work remains outside this submitted snapshot. Detailed implementation decisions and guards were not supplied.",
  "recent_work": [
    "Implemented the coherent API slice awaiting its first review."
  ]
}
```

Continue useful independent integration work while this checkpoint runs. Collect it at a natural pause; do not start another automatic checkpoint concurrently. If code changes meanwhile, reassess findings against current code and distinguish the reviewed snapshot from newer work.

### 2. `dirty-final`

Use the **already verified, task-only clean worktree at the intended commit**. Run ordinary auto review there, covering the entire committed candidate.

Do not collect from the original dirty checkout: path filtering cannot separate unrelated staged edits in the same file. Do not reset, stash, commit, or otherwise alter its files or index. The CLI has no committed-only option, so do not invent one.

From the clean worktree:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/outside-checkout/dirty-final.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user requested final review of the committed PR candidate and preservation of all original working files and the index.",
    "The coding agent selected the verified task-only clean worktree because ordinary capture in the original checkout includes unrelated work and committed-only collection is unavailable."
  ],
  "notes": "Review the full committed candidate in the isolated clean worktree. Unrelated staged edits, unstaged work and the private untracked scratch file remain untouched in the original checkout and are not review inputs. Implementation details and validation results were not supplied.",
  "recent_work": [
    "The committed task candidate awaits final assessment; its detailed implementation and previous-review delta were not supplied."
  ]
}
```

Verify returned coverage matches that candidate, base and full intended scope before claiming final coverage.

### 3. `already-covered`

**Reuse the completed assessment; do not submit again.** Nothing changed, and compatible auto coverage already includes the exact tree, base, full scope and relevant policy.

The supplied evidence supports **Ready locally**: required findings are settled and tests passed. Retain the existing review reference for handoff. This does not independently establish hosted review cleanliness, finding synchronization, CI success, or merge readiness.

No new command or context submission is needed.

### 4. `trivial`

Continue the task without an automatic review. A behavior-neutral internal-comment typo does not warrant a checkpoint merely because an edit occurred.

No review command or context submission is needed.

### 5. `report-only`

Review the **requested safe uncommitted working scope**, using auto effort. Do not edit or create a commit.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/outside-checkout/report-only.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user requested review of uncommitted code without edits or commits."
  ],
  "notes": "The requested working scope is safe for ordinary collection. This is report-only, not PR preparation. Detailed behavior, design rationale and verification results were not supplied.",
  "recent_work": [
    "Uncommitted code awaits its first review; implementation details were not supplied."
  ]
}
```

Assess and report every material finding, including uncertainty and recommendations, then stop. Do not apply fixes, store dismissals, or solicit permission to turn this into implementation. Coverage of this working snapshot does not certify a committed PR candidate.

### 6. `light-to-final`

**Proceed with ordinary auto final review.** The concrete reason is missing required final coverage: a purposeful fast checkpoint alone is not ordinary final coverage, even when it covered the full unchanged snapshot.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/outside-checkout/light-to-final.json" --async --json
```

Context:

```json
{
  "decisions": [
    "The user now requests ordinary final review before handoff."
  ],
  "notes": "A purposeful fast checkpoint completed for the full intended snapshot. No code or evidence changed afterward. There is no completed auto final assessment and no exhausted user budget. Other validation results were not supplied.",
  "recent_work": []
}
```

Keep the verified base and full intended scope. Do not add `--full` merely because this is final review; let the Engine determine reuse eligibility and report its actual execution mode and coverage.

### 7. `explicit-fresh`

Honor the explicit, within-budget request for a **fresh `--full` assessment**, retaining auto effort and full intended scope.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/outside-checkout/explicit-fresh.json" --full --async --json
```

Context:

```json
{
  "decisions": [
    "The user explicitly requested a fresh assessment with --full despite existing compatible auto coverage."
  ],
  "notes": "The unchanged snapshot already has complete compatible auto coverage and settled findings. The fresh assessment is explicitly requested and within budget. No new code or evidence is asserted.",
  "recent_work": []
}
```

### Collection and assessment

For each accepted submission, retain its returned operation ID together with the exact snapshot, base, scope and context. Collect that operation—not a replacement review:

```sh
qodo review status "<returned-operation-id>" --json
```

Respect returned polling delays and retention. Acceptance is not completion. Before interpreting results, verify available identities and integrity, inspect omissions and context-delivery evidence, and assess the complete finding inventory—including earlier open findings. Report unavailable verification honestly; claim local readiness only when required coverage, findings and relevant checks support it.

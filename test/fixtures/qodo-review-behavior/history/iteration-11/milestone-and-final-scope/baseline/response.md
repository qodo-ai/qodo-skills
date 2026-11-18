**Proposals only; no commands or reviews have been run.** I would reuse the supplied compatibility, identity, help and verified-base evidence. Below, `qodo` means the resolved installed executable. Context files would be outside all reviewed worktrees, encoded as UTF-8 without a BOM.

### 1. `milestone` — submit an auto checkpoint now

This is a coherent, testable slice whose review can inform remaining work. Use the clean task commit and all intended paths. A milestone alone does not justify `--fast` or `--deep`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/milestone.json" --async --json
```

Context:
- `decisions`: No implementation choices or rationale were supplied; do not invent them.
- `notes`: The API slice is finished and was tested. Test commands and outcomes are unspecified, so do not claim they passed. Independent integration work remains.
- `recent_work`: `["Completed a coherent API implementation slice; independent integration work remains."]`

Continue independent integration work while the review runs. Retain the submitted snapshot identity and reassess findings against any subsequently changed code.

### 2. `dirty-final` — review the verified clean task worktree

Run from the **available task-only clean worktree at the intended commit**, not the original dirty checkout. Include every intended path.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/dirty-final.json" --async --json
```

There is no supported committed-only option. Path filtering would not separate task changes from unrelated staged changes in the same file. Leave the original files, index and private scratch file untouched—no reset, stash or additional commit.

Context:
- `decisions`: `["The coding agent selected the verified clean task worktree to isolate the committed candidate without modifying unrelated work."]`
- `notes`: Final assessment of the committed PR candidate, with full intended scope. Unrelated original-checkout changes are excluded through isolation. Test outcomes are unspecified.
- `recent_work`: `["The committed PR candidate is awaiting final assessment; detailed code changes were not supplied."]`

Final-review status alone does not justify deep effort or `--full`.

### 3. `already-covered` — reuse coverage and hand over

**No new review command.** The exact snapshot, base, full scope and relevant policy already have complete compatible auto coverage, settled required findings and passing tests.

Report **ready locally**, referencing the existing assessment. This does not establish hosted PR review, CI, merge or deployment status.

### 4. `trivial` — continue without an automatic review

**No command or context submission.** An internal comment typo with no behavior change does not warrant an unsolicited review checkpoint.

### 5. `report-only` — review the requested working snapshot

Collect the safe requested uncommitted scope without creating a commit or preparing a PR.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/report-only.json" --async --json
```

Context:
- `decisions`: `["The user requested review only, with no edits or commits."]`
- `notes`: Assess the requested uncommitted working scope. No PR preparation was requested. Implementation details and verification results were not supplied.
- `recent_work`: `["Uncommitted code in the requested working scope awaits its first review."]`

Assess and report findings, including uncertainties and recommendations, then stop. Do not edit, commit, dismiss stored findings or solicit permission to turn this into implementation.

### 6. `light-to-final` — request ordinary auto final coverage

Another assessment has a concrete reason: **the completed light checkpoint does not alone provide ordinary final coverage**, even though it covered the full unchanged snapshot.

Keep the same base and full intended scope; omit both effort flags:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/light-to-final.json" --async --json
```

Context:
- `decisions`: No new implementation decisions.
- `notes`: A purposeful fast checkpoint completed for this exact full snapshot. No code or new evidence changed afterward. Ordinary final coverage is now requested; no completed auto final assessment exists.
- `recent_work`: `[]`

Do not automatically add `--full`: this is neither an explicit fresh-assessment request nor a failed/incomplete earlier assessment. Let the Engine qualify continuation, and verify the returned coverage and actual mode. Do not merely relabel the previous light checkpoint as final.

### 7. `explicit-fresh` — honor the fresh full request

The explicit request supplies the reason to reassess unchanged work.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_DIR/explicit-fresh.json" --full --async --json
```

Context:
- `decisions`: `["The user explicitly requested a fresh assessment with --full within the available review budget."]`
- `notes`: The unchanged snapshot already has complete compatible auto coverage and settled findings. No new code or evidence is being asserted.
- `recent_work`: `[]`

`--full` requests fresh assessment, **not deeper effort**; effort remains auto.

### Collection and reporting

For each accepted submission, retain its operation ID, exact base, submitted commit/tree, scope and context. Collect that same operation:

```sh
qodo review status "$operation_id" --json
```

Use the returned operation ID and polling delay; acceptance is not completion. For additional retained detail, use `status` with `--extended`, not another submission.

Before declaring readiness, inspect warnings, `review_agent_comment`, context-delivery gaps, inventory completeness and coverage completeness. Assess both new and earlier-open findings; report resolved and dismissed findings separately. New submissions remain **awaiting assessment**, not “clean,” until their results and required checks establish otherwise.

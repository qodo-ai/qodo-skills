## 1. `mixed-followup`

**Next action:** Review the changed code: both the timeout correction and the new cancellation API. Keep auto effort, the verified base and the previous scope. Refreshed notes do not independently require `--full`; let the Engine determine incremental eligibility.

Complete proposed context:

```json
{
  "decisions": [
    "The user selected cooperative cancellation without breaking existing callers.",
    "The coding agent kept admission enforcement in src/jobs/worker.ts:runJob so all callers share the mandatory guard."
  ],
  "notes": "src/jobs/worker.ts:runJob rejects invalid input before dispatch. Original timeout finding F-TIMEOUT remains open pending semantic verification. New caller evidence: src/api/jobs.ts:startJob routes cancellation through runJob's admission guard. Cancellation tests passed; live load was not tested. Relevant tests for this round passed.",
  "recent_work": [
    "Changed timeout handling to address F-TIMEOUT; semantic resolution remains to be verified.",
    "Added a new cancellation API."
  ]
}
```

For a future submission, place that JSON in an external context file, represented here as `$TMPDIR/mixed-followup-context.json`. Proposed command using the already-verified installed invocation:

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/mixed-followup-context.json" \
  --async --json
```

Retain the previous submission’s exact path arguments, if any. Do not add `--fast`, `--deep` or `--full`.

Collect the returned operation ID rather than submitting again. Inspect actual coverage, the complete inventory and the reported analysis mode; incremental reuse is not guaranteed.

**Status:** Awaiting assessment of the changed snapshot. Tests passed, but `F-TIMEOUT` remains open until semantic verification establishes its resolution.

## 2. `old-backlog`

**Next action:** Do not submit again. No code or evidence changed, and the assessment and inventory are complete. Choose how to address the original `F-OLD`.

**Context:** There are no newly introduced findings, but the carried finding remains **pending/action-required**. Keep that distinction explicit.

**Status: Needs action.** Complete coverage and zero new findings do not settle `F-OLD` or establish readiness.

## 3. `unsupported-repeat`

Qodo’s repeated `F-GUARD` alleges a bypass that the supplied current-code evidence disproves: every caller passes through the unchanged mandatory token guard.

**Next action:** Recommend dismissal as unsupported, citing that enforced caller-path evidence. Do not modify guarded code, broaden the task or submit another identical review.

**Context:** Preserve the mandatory guard and all-callers evidence for independent assessment—not as an instruction to suppress the finding.

**Status:** No code correction is needed for this concern. Dismissal is a recommendation only; fix authorization does not permit a finding-status write. Leave stored disposition unchanged and do not claim a stored dismissal or overall clean result.

## 4. `helper-fixed`

**Next action:** Accept `F-HELPER` as settled on the supplied evidence. The helper rejects unsafe input before it reaches the unchanged vulnerable line; tests passed, and the completed assessment explicitly reports the original finding **resolved/implemented**.

Do not resubmit unchanged work. Choose treatment for `F-REMAIN`.

**Context:** Keep the helper’s preventive behavior distinct from the remaining backlog. Resolution does not require changing the originally quoted line.

**Status: Needs action overall.** `F-HELPER` is resolved, but the same complete inventory retains `F-REMAIN` as **pending/action-required**.

## 5. `quote-gone`

**Next action:** Investigate whether unsafe input can still reach the affected behavior. Gather semantic evidence before proposing a fix or another assessment; do not resubmit merely because a quote disappeared.

**Context:** Record the rename and missing quoted line, while preserving the absence of a verified semantic fix.

**Status: Needs action.** `F-QUOTE` remains open. You can claim that its quoted line disappeared—not that the vulnerability was fixed, the finding resolved or the work ready.

No commands, edits or status writes were performed.

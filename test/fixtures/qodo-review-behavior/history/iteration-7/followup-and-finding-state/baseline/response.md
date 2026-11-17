Proposals only; no commands, edits, submissions, or finding-status writes were executed.

## 1. `mixed-followup`

**Next action:** Review the changed code: both the timeout correction and new cancellation API. This is not automatically a fixes-only round.

Proposed context file, outside the reviewed worktree:

```json
{
  "decisions": [
    "The user added a cancellation API alongside the timeout correction; the rationale for the API addition was not supplied."
  ],
  "notes": "The comparison base and requested scope are unchanged. Relevant tests passed. Session notes were refreshed with new caller evidence. Exact caller locations and test names were not supplied. The earlier timeout finding retains its original open ID; the author's correction does not itself establish a resolved verdict.",
  "recent_work": [
    "Corrected the timeout issue identified by the previous review.",
    "Added a new cancellation API, introducing behavior beyond the timeout fix."
  ]
}
```

Proposed command, using the already-verified invocation:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/mixed-followup-context.json \
  --async --json
```

Retain any existing explicit path arguments unchanged. Omit `--fast`, `--deep`, and `--full`: refreshed notes and an open finding do not independently require a full assessment. Let the Engine determine continuation eligibility and report its actual analysis mode.

**Status:** Follow-up proposed, not submitted. Current changes await completed assessment. After acceptance, retain the returned operation ID and collect that operation—not another submission. Verify complete coverage, inventory, context-delivery metadata, and the original finding’s disposition before claiming readiness.

## 2. `old-backlog`

**Next action:** Do not submit again. Present **F-OLD** as an earlier pending/action-required obligation and await the user’s decision about addressing it. No changed code or meaningful new evidence justifies another assessment.

**Context:** Both completeness flags are true, but zero introduced findings does not settle the retained backlog.

**Status: Needs action.** The assessment completed; the work is not ready while F-OLD remains required and undecided.

## 3. `unsupported-repeat`

**Next action:** Recommend treating **F-GUARD** as a false positive. Its alleged bypass is contradicted by the supplied evidence: every caller traverses the unchanged mandatory token guard.

Do not alter already-guarded code, broaden the task, or purchase another identical assessment.

**Context:** Preserve the original finding reference and the mandatory-guard evidence. Code-fix authority does not authorize stored dismissal.

**Status:** No code correction is warranted for this concern. The dismissal is only a recommendation; no stored disposition changed. Do not claim the finding was dismissed or that the overall review is clean.

## 4. `helper-fixed`

**Next action:** Accept the current result’s **F-HELPER resolved/implemented** verdict. Do not resubmit unchanged work.

**Context:** The helper now rejects unsafe input before it reaches the original line. A semantic fix need not modify the quoted line. Current tests passed, and both coverage and inventory are complete.

**Status: Ready locally on the supplied evidence.** This does not independently establish successful checkpoint persistence, finding handoff, hosted review, or CI readiness.

## 5. `quote-gone`

**Next action:** Keep **F-QUOTE open**. Propose tracing the renamed unsafe path and checking whether unsafe input can still reach it, with targeted verification. A disappeared quotation alone is not meaningful fix evidence.

**Context:** Only the rename and quotation disappearance are established. Neither semantic resolution nor elimination of the unsafe path is verified.

**Status: Needs action.** Claim only that the quoted line disappeared—not that the vulnerability was fixed, the finding resolved, or the work is ready. Do not manually change finding status or buy another assessment merely to chase the missing quote.

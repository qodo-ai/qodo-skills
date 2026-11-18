### 1. `mixed-followup`

**Next action:** Review the changed work: both the timeout correction and the new cancellation API. Use **auto**, retain the exact base and scope, and do not add `--full`. Refreshed notes and mixed work do not themselves invalidate reuse; the Engine decides eligibility.

Proposed context, preserving the existing detailed caller evidence rather than replacing it:

```json
{
  "decisions": [],
  "notes": "The previous review completed with complete coverage and inventory. The comparison base and requested scope are unchanged. Relevant tests passed. Notes were refreshed with new caller evidence; concrete caller citations were not supplied in this scenario. The timeout finding retains its original open ID, so the author's correction does not yet establish a reviewed resolution.",
  "recent_work": [
    "Implemented a correction for the previously reported timeout finding.",
    "Added a new cancellation API; this follow-up includes new behavior, not only fixes."
  ]
}
```

No design-decision ownership or rationale was supplied, so none is invented.

Proposed command only:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "$REVIEW_CONTEXT" \
  --async --json \
  "${previous_scope[@]}"
```

Here, `qodo` is the verified installed invocation; `REVIEW_CONTEXT` names the complete context file outside the reviewed tree; `previous_scope` contains the exact prior path arguments, empty only if previously unrestricted.

Collect the returned operation rather than resubmitting. Inspect both completeness flags, the complete finding inventory, warnings and reviewer comment. Report the actual `full`, `incremental` or `reused` outcome without promising reuse.

**Status:** Changed work awaits assessment; previous coverage does not certify the new snapshot.

### 2. `old-backlog`

**Next action:** Do not submit again. Nothing changed, and the assessment and inventory are complete.

**Context:** No new findings does not settle the earlier backlog. Preserve **F-OLD — pending/action-required**. Its details were not supplied, so a specific correction cannot be recommended.

**Status: Needs action.** The work is not ready while F-OLD requires a decision. Another unchanged assessment would not resolve that decision.

### 3. `unsupported-repeat`

**Assessment:** Qodo’s F-GUARD alleges that callers can bypass the token check. The supplied evidence disproves that triggering condition: every caller passes through the unchanged mandatory guard.

**Next action:** Recommend dismissal as unsupported, citing that guard evidence. Do not change correctly guarded code, broaden the task, or purchase another identical assessment.

**Context:** Necessary code-fix authorization does **not** authorize finding-status writes. Therefore, do not store a dismissal or claim one succeeded.

**Status:** F-GUARD is unsupported on the supplied evidence, with no code correction needed. Its stored disposition remains unchanged; the recommendation is not a dismissal or an overall clean result.

### 4. `helper-fixed`

**Assessment:** A semantic fix need not change the originally quoted line. The corrected helper prevents unsafe input from reaching it, tests passed, and the completed result explicitly reports **F-HELPER — resolved/implemented**, with complete coverage and inventory.

**Next action:** Accept that resolution. Do not re-fix the unchanged line or submit another assessment without changed code, meaningful new evidence, or a fresh-review request.

**Status:** F-HELPER is settled. Overall **Ready locally** additionally requires that the complete inventory contain no other required obligations; this finding’s resolution alone does not establish that.

### 5. `quote-gone`

**Assessment:** A disappeared quotation after a rename proves neither a semantic correction nor removal of the unsafe path.

**Next action:** Preserve **F-QUOTE — open**. Investigate the renamed execution path and applicable guards before claiming a fix. Do not manually mark it resolved or resubmit unchanged work merely to chase a different result.

**Context:** The quotation disappeared, but semantic resolution remains unverified.

**Status: Needs action.** No fix or readiness claim is supported.

These local outcomes do not independently establish checkpoint persistence, PR handoff, hosted-review cleanliness, or CI success.

These are independent cases. No commands were run, files changed, or finding statuses written.

### 1. `mixed-followup`

**Next action:** Submit one follow-up because both a timeout correction and a new cancellation API need assessment. Keep auto effort, the same base, and the same scope. Do not add `--full` merely because notes changed. The Engine determines incremental eligibility and reports actual reuse or fallback; this is not automatically a fixes-only round.

**Proposed context:**
```json
{
  "decisions": [],
  "notes": "The previous review completed with complete coverage and inventory. The comparison base and requested scope are unchanged. Relevant tests passed. Notes were refreshed with new caller evidence, but its contents and code locations were not supplied in this scenario. The author reports correcting the timeout issue; its original finding ID remains open, so the author claim alone does not establish resolution. No service result reports invalidated reuse. No additional decision ownership or rationale was supplied.",
  "recent_work": [
    "Corrected the timeout behavior identified by the earlier finding; semantic resolution remains to be verified.",
    "Added a new cancellation API. This follow-up includes new behavior, not just finding fixes."
  ]
}
```

Proposed command, using an external context file containing that JSON:
```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-mixed-followup-context.json" \
  --async --json
```

Here, `qodo` means the already-verified installed invocation. This command assumes repository-wide scope; retain the exact original path arguments if the earlier scope was restricted.

Retain the returned operation ID and collect that operation with `qodo review status <returned-operation-id> --json`, rather than resubmitting.

**Current status:** Changed work awaits assessment. Neither timeout-finding resolution nor overall readiness is established yet.

### 2. `old-backlog`

**Next action:** Do not submit again. Nothing changed, the assessment and inventory are complete, and an unchanged rerun would not resolve the outstanding decision.

**Context:** “No introduced findings” is separate from the earlier backlog. Original finding **F-OLD** remains pending/action-required.

**Final status: Needs action—not ready.** Report F-OLD as an unresolved obligation, not a new finding. A decision on how to address it remains necessary.

### 3. `unsupported-repeat`

**Next action:** Stop the identical review loop. Make no code change or optional refactor.

**Assessment:** Qodo alleges a token-check bypass, but the supplied current evidence establishes that every caller passes through the unchanged mandatory guard. That enforcement contradicts the reported triggering condition. Recommend dismissing **F-GUARD** as unsupported, with that guard evidence as the rationale.

**Context:** Preserve the caller/guard evidence; no correction was necessary. Fix authorization does not authorize finding-status writes.

**Final status:** Unsupported concern; no code action needed. No stored dismissal was authorized or performed. Do not claim F-GUARD was implemented, its stored disposition changed, or overall readiness established.

### 4. `helper-fixed`

**Next action:** Reuse the current completed assessment. No further review is justified by these facts.

**Context:** The helper now rejects unsafe input before it reaches the unchanged vulnerable line. Tests passed, and the completed result explicitly reports original finding **F-HELPER** as **resolved/implemented**, with complete coverage and inventory.

**Final status:** F-HELPER is settled. An unchanged quoted line does not negate an effective upstream correction. Overall **Ready locally** still requires the full inventory to contain no other required obligations; resolution of this finding alone does not establish that.

### 5. `quote-gone`

**Next action:** Keep **F-QUOTE** open. Investigate whether the renamed code still permits the unsafe path; do not edit code or manually mark it resolved here.

**Context:** The quote disappeared after a rename. There is neither verified semantic-fix evidence nor a resolution verdict. Text disappearance is not proof that the behavior was corrected.

**Final status: Needs action.** Claim only that the quoted line changed or disappeared. Do not claim F-QUOTE was fixed, resolved, or that the work is ready.

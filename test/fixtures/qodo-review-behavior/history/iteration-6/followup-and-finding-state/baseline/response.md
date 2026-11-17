## 1. `mixed-followup`

**Submit one auto follow-up: changed code needs assessment.** Keep the verified base and original scope. Do not add `--full`, `--fast`, or `--deep`. New notes and a second round do not independently invalidate reuse; the Engine determines eligibility and actual analysis mode.

Proposed context, saved outside reviewed changes:

```json
{
  "decisions": [
    "The follow-up retains the original comparison base and requested scope.",
    "The cancellation API's design owner and rationale were not supplied."
  ],
  "notes": "Relevant tests passed. Session notes were refreshed with new caller evidence. The fixture supplies no caller locations or test names, so none are invented here. The applied timeout correction does not itself establish a verified resolution of the earlier finding.",
  "recent_work": [
    "Applied a timeout correction targeting the earlier finding.",
    "Added a new cancellation API. This follow-up includes new behavior, not only finding fixes."
  ]
}
```

Proposed command:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /absolute/path/outside-reviewed-diff/review-context.json \
  --async --json
```

Replace the context path with the actual prepared file. Append exactly the original path arguments if the earlier submission was path-restricted.

Collect the accepted operation, rather than resubmitting:

```sh
qodo review status <returned-operation-id> --json
```

**Status:** Changed work awaits completed assessment. Preserve the earlier finding’s original ID and inspect its returned lifecycle state alongside new findings, coverage, warnings, and `review_agent_comment`. Acceptance alone establishes no readiness or resolution.

## 2. `old-backlog`

**Do not submit again.** Nothing changed, no meaningful new evidence was supplied, and no fresh assessment was requested. Another unchanged review would not decide F-OLD.

Qodo introduced no new findings, but **F-OLD remains pending/action-required**. Report it as earlier open backlog—not newly discovered—and preserve its original ID and reported classification. Its description, category, and code location are not supplied, so a concrete fix or dismissal rationale cannot be invented.

Present the unresolved finding for a decision. If implementation authority is ambiguous, ask once which action to take, without preselecting a fix. Do not silently edit or change stored status.

**Status: Needs action.** Complete coverage and inventory do not settle an outstanding required finding. No additional command or submission context is warranted yet.

## 3. `unsupported-repeat`

**Stop this review loop; make no code change and buy no identical assessment.**

Qodo’s F-GUARD alleges a bypass, but the supplied current-code evidence establishes that **every caller traverses the unchanged mandatory token guard**. On these facts, the alleged omission is unreachable. Recommend **false-positive dismissal**, explaining that enforcement occurs in the mandatory shared guard rather than separately at each caller.

Preserve F-GUARD’s original ID and reported category/action level; those classifications are not supplied here, so do not fabricate them.

Necessary-fix authorization does **not** authorize stored finding-status changes. Therefore:

- Do not invoke dismissal tools.
- Do not weaken or duplicate the guard to satisfy the finding.
- Do not introduce unrelated refactoring.
- Report the evidence-backed assessment separately from stored state.

If a later submission has an independent justification, include the guard enforcement evidence in its notes; do not submit solely to repeat this explanation.

**Status:** F-GUARD requires no supported code correction on the supplied evidence. Its stored disposition remains unchanged; it has not been dismissed or resolved. Overall local readiness is not established by this scenario alone.

## 4. `helper-fixed`

**Accept the verified semantic resolution and stop.** No further submission or manual status change is needed.

The helper now rejects unsafe input before it reaches the original vulnerable line. The line remaining unchanged does not negate that correction. Unlike an author-only assertion, the current completed result explicitly reports **F-HELPER resolved/implemented**, with complete coverage and inventory; current tests passed.

Report F-HELPER under its original ID as settled, explaining the upstream rejection. Do not modify the sink unnecessarily or reopen the concern merely because its original quotation still exists.

**Status: Ready locally for the supplied scope.** There is no changed work or new evidence requiring another assessment. This does not separately establish successful checkpoint persistence, PR finding handoff, hosted Qodo-clean status, CI, or merge readiness.

## 5. `quote-gone`

**Do not claim a fix.** The supported statement is: “The quoted line disappeared during a rename; F-QUOTE remains open, and semantic resolution is unverified.”

A missing quotation establishes neither that unsafe behavior disappeared nor that the finding was implemented, resolved, or dismissed.

Proposed next investigation:

1. Locate the renamed code and follow the affected input through callers, helpers, and the unsafe operation.
2. Determine whether the triggering condition remains reachable.
3. Check or add a focused regression test only within authorized implementation scope.
4. Preserve F-QUOTE’s original ID throughout; do not manually mark it fixed because its quotation vanished.

For any justified follow-up, `recent_work` must describe **a rename**, not a verified security correction. Notes should state that unsafe-path elimination remains unverified. Once a substantive correction or meaningful new evidence warrants assessment, use auto with the verified base and retained scope; do not force `--full` merely because F-QUOTE remains open.

**Status: Needs action.** Neither semantic resolution nor local readiness is established. No assessment should be purchased solely to chase the disappeared quote.

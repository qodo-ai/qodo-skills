### 1. `mixed-followup`

**Submit again because code changed:** this includes both a timeout correction and a new cancellation API, not fixes alone.

Preserve existing decisions and the refreshed caller evidence. Merge in this context; do not invent missing code locations:

```json
{
  "decisions": [
    "The user added a cancellation API alongside the timeout correction; further design rationale was not supplied."
  ],
  "notes": "The previous review completed with complete coverage and inventory. The comparison base and requested scope are unchanged. Relevant tests passed. Preserve the refreshed caller evidence. The earlier timeout finding retains its original open ID; the reported correction is not yet a verified resolution.",
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added a new cancellation API; this follow-up includes new behavior."
  ]
}
```

Proposed command, after preparing the merged context outside the reviewed diff:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-mixed-followup-context.json" \
  --async --json
```

Use the already verified invocation and retain any previous explicit path arguments. Omit `--fast`, `--deep` and `--full`. Refreshed notes alone do not require full review; let the Engine determine eligibility and report its actual analysis mode.

Collect the returned operation ID rather than submitting again. Assess both introduced and retained findings.

**Status:** Changed snapshot awaiting assessment; prior coverage does not certify it.

### 2. `old-backlog`

**Do not resubmit.** Nothing changed, both completeness flags are true, and no fresh assessment was requested.

Retain **F-OLD — pending/action-required** as earlier backlog, not a new finding. Present it for a decision without preselecting a remedy. No new findings does not settle this obligation.

**Status: Needs action; not ready locally.**

### 3. `unsupported-repeat`

Qodo’s repeated **F-GUARD** concern is contradicted by the supplied evidence: every caller passes through the unchanged mandatory token guard.

Recommend dismissal on that evidence. Do not modify guarded code, broaden the task or purchase another identical assessment. Code-fix authorization does **not** authorize a stored dismissal.

Preserve the original finding ID and explain the guard evidence in the assessment.

**Status:** Unsupported concern; no code fix needed. Stored disposition remains unchanged—do not claim dismissal, resolution or overall readiness.

### 4. `helper-fixed`

**Do not resubmit for this concern.** The helper now rejects unsafe input before the unchanged vulnerable line. The completed assessment explicitly reports **F-HELPER — resolved/implemented**, and relevant tests passed.

An unchanged quoted line does not invalidate a verified semantic fix. Retain the helper’s prevention behavior and test results as supporting context.

**Status:** F-HELPER is settled. Overall readiness still requires checking the full inventory for other required obligations; completeness flags and this resolution alone do not establish that. No hosted-review or downstream handoff claim follows.

### 5. `quote-gone`

A disappeared quotation after a rename is **not** proof that the unsafe behavior disappeared.

Keep **F-QUOTE open**. Describe the recent work as a rename, not a verified fix. Investigate whether unsafe input can still reach the affected behavior and obtain supporting semantic evidence before claiming resolution. Another unchanged assessment is not a substitute for that investigation.

**Status: Needs action.** Neither “fixed,” “resolved” nor “ready” is supported by the supplied evidence.

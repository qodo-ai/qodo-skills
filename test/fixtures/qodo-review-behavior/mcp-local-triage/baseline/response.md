Proposed actions only; nothing has been executed or saved.

### 1. `metadata-only`

Submit one batch through `pr-review-dismiss`, using the documented host metadata transport:

```json
{
  "name": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-A", "F-B"],
    "local_review_id": "L-ORIGINAL",
    "reason": "false_positive",
    "explanation": "The mandatory caller guard rejects this input."
  },
  "_meta": {
    "io.qodo/idempotency-key": "triage-L-ORIGINAL-FA-FB-false-positive-001"
  }
}
```

`_meta` is request metadata, not a tool argument. Do not add an unsupported `idempotency_key` argument.

Before submission, retain the exact request and key in task state. Any permitted retry must reuse both unchanged.

Inspect tool errors and each finding’s returned outcome, then read back **F-A and F-B individually**. Verify their stored status, reason and explanation against the original local-review identity. Report prior dismissals, conflicts or synchronization failures separately; a batch receipt alone does not establish success.

### 2. `no-replay-transport`

**Blocked: replay-safe dismissal is unavailable.** Do not submit an unprotected write or invent a schema argument.

The next action is to report the missing transport capability. Proceed only when a supported replay-key transport becomes available. No new dismissal has been recorded for either finding; the authorization and supporting evidence do not remove this transport requirement.

### 3. `prior-outcomes`

- **F-A:** The prior dismissal remains: reason `deferred`, explanation **“Awaiting a separate migration.”** The requested `false_positive` reason was **not** saved.
- **F-B:** `conflict` is not a successful dismissal. No requested transition is confirmed.

Readback successfully verified these outcomes; neither requested new dismissal succeeded. Preserve and report them without overwriting prior decisions or automatically submitting another assessment. A clean review cannot be claimed from this evidence.

### 4. `saved-sync-pending`

**F-C’s new `false_positive` dismissal succeeded and is verified as stored.** The requested reason and explanation were saved. `reconciled: false` means only downstream synchronization remains incomplete.

The permitted next action is to replay the **exact retained F-C request with the same replay key** for synchronization. Do not generate a new key or change the payload. Inspect the retry result and verify the stored disposition and synchronization outcome afterward.

Until confirmed, report **dismissal saved; synchronization pending**—not dismissal failed, fully synchronized, or review clean.

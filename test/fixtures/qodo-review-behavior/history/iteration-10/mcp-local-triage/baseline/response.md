Proposals only; no dismissal requests or state changes performed.

### 1. `metadata-only`

The supplied code and test evidence supports the authorized dismissal. Both findings share the same review, reason and explanation, so propose one MCP `pr-review-dismiss` request:

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
    "io.qodo/idempotency-key": "local-triage-L-ORIGINAL-FA-FB-001"
  }
}
```

Send `_meta` through the host’s documented request-metadata transport, not as a tool argument. Retain the exact request and key together; any permitted replay must reuse both unchanged.

Inspect transport/tool errors and each finding’s outcome, then read back F-A and F-B. Verify their original identities and stored reason/explanation individually. Claim a newly saved dismissal only where confirmed; distinguish prior dismissals, conflicts and pending synchronization.

### 2. `no-replay-transport`

**Blocked: replay-safe status writes are unavailable.** Do not submit an unprotected request or invent an `idempotency_key` argument.

The next prerequisite is a supported replay-key transport, such as documented host metadata support. With no trusted CLI alternative, stop here. Neither authorized dismissal has been submitted or saved by this proposed action.

### 3. `prior-outcomes`

- **F-A:** The prior dismissal remains: reason `deferred`, explanation **“Awaiting a separate migration.”** `already_dismissed` did not save the requested `false_positive` disposition.
- **F-B:** `conflict` is not a successful dismissal. No requested change is established.

Readback successfully verified those outcomes; neither newly requested dismissal succeeded. Do not claim the new reason was saved or that the review is clean. Stop without overwriting the prior decision, retrying automatically or starting an unchanged assessment.

### 4. `saved-sync-pending`

**F-C’s new dismissal was saved.** The returned `status: dismissed`, matching stored reason/explanation and confirming readback establish that transition.

`reconciled: false` means downstream synchronization remains incomplete—not that storage failed.

The next permitted action is one synchronization retry using the **same retained request and key**, unchanged. Inspect the replay response and read back the outcome again. Report synchronization as complete only when confirmed; otherwise report the saved dismissal and outstanding synchronization separately. This retry is not a new dismissal or a new review.

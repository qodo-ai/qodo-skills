**Proposals only. No commands, calls, writes, or finding-state changes were performed.**

### 1. `metadata-only`

F-A and F-B share the original review, reason, and explanation, so propose one batch:

```json
{
  "method": "tools/call",
  "params": {
    "name": "pr-review-dismiss",
    "arguments": {
      "finding_ids": ["F-A", "F-B"],
      "local_review_id": "L-ORIGINAL",
      "reason": "false_positive",
      "explanation": "The mandatory caller guard rejects this input."
    },
    "_meta": {
      "io.qodo/idempotency-key": "6e964130-65c4-49ea-8d3e-9f66fef28f5b"
    }
  }
}
```

The key is request metadata, **not** an unsupported tool argument. Retain the exact request, key, and returned receipt/result.

- If the response is lost, replay the exact request with the **same key**. This synchronous tool has no operation handle to poll.
- Inspect errors and each finding’s returned outcome.
- Read back both stored dispositions through the supported read capability. Verify their original IDs, review association, reason, and explanation.
- Report prior decisions, conflicts, and synchronization status separately. Without readback, do not claim verified storage.

### 2. `no-replay-transport`

**Dismissal is blocked by missing replay-safe write capability.**

Do not submit an unprotected write or invent an `idempotency_key` argument. The next step is to obtain a trusted host/tool path that supports replay protection.

Neither requested dismissal has been submitted or saved by this proposed action. Authorization and supporting evidence do not remove the transport requirement.

### 3. `prior-outcomes`

- **F-A:** The existing dismissal remains `deferred`, with explanation **“Awaiting a separate migration.”** Readback verified that prior decision; it did not establish a new `false_positive` dismissal.
- **F-B:** `conflict`; no successful requested update was verified.

Neither requested new disposition succeeded. Do not overwrite the prior decision, automatically repeat the batch, or start another assessment on these facts alone. **Neither the new reason nor a clean review can be claimed.**

### 4. `saved-sync-pending`

**F-C’s requested dismissal was saved and verified. Only downstream synchronization remains incomplete.**

The original operation completed. Replaying its original key would return the cached result without invoking the synchronization handler again.

For the **one authorized new synchronization attempt**, propose:

- Tool: `pr-review-dismiss`.
- Business arguments: exactly the retained original arguments—F-C, `L-CURRENT`, `false_positive`, and the exact retained authorized explanation.
- Metadata: `_meta["io.qodo/idempotency-key"]` set to a **fresh, distinct key**, retained for this synchronization attempt.

Preserve the original request/key/receipt alongside the new attempt’s request/key/receipt. This is a synchronization retry, not authorization to change the stored decision.

Inspect the new outcome and read back the disposition and synchronization status. If its response becomes uncertain, recover using **that attempt’s same key**. If synchronization remains incomplete, report it; do not initiate further new attempts automatically.

### 5. `uncertain-write`

**The dismissal outcome is unknown.**

First collect the existing operation using its retained receipt. If replay is needed, send the **exact retained original request with its original key**.

A new key is **not justified**: there is no terminal result or readback establishing what happened, so a fresh invocation is not yet an authorized synchronization retry.

After recovery, inspect the terminal result and read back stored state. Until then, claim neither successful dismissal nor confirmed failure.

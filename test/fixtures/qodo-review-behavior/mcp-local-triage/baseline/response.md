**Proposals only—no commands, service calls, or finding-state changes performed.**

### 1. `metadata-only`

Proposed MCP `tools/call` parameters:

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
    "io.qodo/idempotency-key": "triage-L-ORIGINAL-FA-FB-01"
  }
}
```

The replay key belongs in request metadata, **not** in the tool arguments.

Retain the exact request and key before submission, then retain the response. If the response is lost, replay only that exact request with the same key. This synchronous call has no pollable operation handle.

Inspect errors and each finding’s returned outcome, then read back both stored dispositions. Verify the requested reason and explanation individually. Report any reconciliation failure separately from whether the dismissal was saved.

### 2. `no-replay-transport`

**The write is blocked.** Neither supported replay-key channel is available, and there is no trusted CLI fallback.

Do not submit an unprotected dismissal or invent an argument. The next prerequisite is a trusted host/tool path supporting replay protection. The requested dismissals remain unperformed.

### 3. `prior-outcomes`

- **F-A:** The prior dismissal remains `deferred`, with explanation “Awaiting a separate migration.” `already_dismissed` does not mean the requested `false_positive` reason replaced it.
- **F-B:** `conflict` is not a successful dismissal.

Readback confirms these outcomes. Neither requested new disposition can be claimed as saved. This evidence also does not establish a clean review or justify another assessment.

### 4. `saved-sync-pending`

**F-C’s requested dismissal was saved and verified.** Only downstream synchronization remains incomplete; `reconciled: false` does not undo the stored transition.

Because the original operation completed, replaying its original key would return the cached result without invoking synchronization again.

For the user-authorized **one new synchronization attempt**:

- Call `pr-review-dismiss` with the retained business arguments unchanged: F-C, `L-CURRENT`, `false_positive`, and the exact original explanation.
- Send a **new, distinct replay key** through `_meta["io.qodo/idempotency-key"]`.
- Retain the original request/key/receipt and the new attempt’s request/key/receipt.
- Verify the response and read back the disposition and synchronization outcome. A matching `already_dismissed` outcome preserves the existing decision; claim synchronization success only with confirming evidence.

If that attempt remains unreconciled, report the remaining synchronization issue without another automatic attempt.

### 5. `uncertain-write`

Collect the retained operation first. If recovery requires replay, resend the **exact original request with its original replay key**.

**A new key is not justified:** execution and storage are still uncertain. A new key would start a new handler invocation rather than recover the original attempt.

After obtaining a terminal result, verify each stored outcome through readback. Until then, report the dismissal outcome as unknown—not saved, failed, or synchronized.

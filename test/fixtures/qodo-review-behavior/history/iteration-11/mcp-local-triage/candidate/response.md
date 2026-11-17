Proposals only: no Qodo service calls or finding-status writes have been performed.

### 1. `metadata-only`

Submit one batch because both findings share the original local review, reason and explanation. Proposed MCP `tools/call` parameters:

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
    "io.qodo/idempotency-key": "K-metadata-only"
  }
}
```

`K-metadata-only` represents a fresh transport key chosen once and retained before submission. It is request metadata, **not** an unsupported `idempotency_key` business argument.

Retain the exact request, key and returned operation receipt. Collect the result and read back **both** findings, checking their original IDs, local-review association, stored reason and explanation. Report each actual outcome; a conflict is not success, and a differing prior dismissal is not the requested new decision. Report downstream synchronization separately.

If the response is lost, recover the original operation or replay the exact request with the same key.

### 2. `no-replay-transport`

**Do not submit the write.** Neither supported replay-key mechanism is available.

Report the missing replay-safe write capability. Proceed only through an authorized host or schema that supports the documented protection; do not invent an argument or send an unprotected request. Both requested dismissals remain unperformed.

### 3. `prior-outcomes`

The batch returned verified outcomes, but neither establishes a newly saved `false_positive` dismissal:

- **F-A:** `already_dismissed`. Its prior reason remains `deferred`, with explanation **“Awaiting a separate migration.”** The requested replacement reason was not saved.
- **F-B:** `conflict`. The requested transition did not succeed; no further stored disposition is established by the supplied evidence.

Readback verification succeeded. No new requested decision can be claimed, and these outcomes do **not** establish a clean review. Do not overwrite the prior decision or retry the conflict without additional authority and evidence.

### 4. `saved-sync-pending`

**F-C’s dismissal was saved and verified.** `reconciled: false` means downstream synchronization remains incomplete—not that storage failed.

Replaying the completed original operation with its original key would only return its cached result; it would not attempt synchronization again.

For the separately authorized **one** synchronization attempt, propose a new `pr-review-dismiss` operation with:

- `finding_ids`: `["F-C"]`
- `local_review_id`: `"L-CURRENT"`
- `reason`: `"false_positive"`
- `explanation`: the exact retained original explanation
- Request metadata `_meta["io.qodo/idempotency-key"]`: a **new retained key**, distinct from the original

Keep all business arguments unchanged. Retain both requests, keys and operation receipts. Collect the new result and read back the stored disposition again. Claim synchronization only if the new outcome confirms it; otherwise report the remaining failure or uncertainty. Do not automatically make another attempt.

### 5. `uncertain-write`

**The original write’s outcome is unknown, not confirmed failed.**

Collect the retained original operation. If replay is needed, send the **exact original request with its original transport key**. Then inspect the terminal result and read back the stored disposition before claiming success.

A new key is **not justified** while the original outcome remains unknown. Recovering that invocation is not authorization for a separate synchronization attempt.

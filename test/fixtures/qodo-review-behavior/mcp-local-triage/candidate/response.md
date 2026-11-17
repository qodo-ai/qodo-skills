Proposals only; no service calls or state changes performed.

### 1. `metadata-only`

Submit one batch because both findings share the review, reason and explanation. Proposed MCP `tools/call` parameters:

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
    "io.qodo/idempotency-key": "<fresh unique invocation key>"
  }
}
```

Choose the key once before submission and retain the exact request, key and response. `_meta` is request metadata, not a tool argument; do not invent an `idempotency_key` argument.

Inspect both per-finding outcomes and read back each stored disposition. Confirm the finding/review identities and requested reason/explanation before reporting success. Report downstream synchronization separately from saved status.

If the response is lost, replay the exact retained request with the same key. This synchronous tool supplies no pollable handle; do not invent one.

### 2. `no-replay-transport`

**Blocked: replay-safe writes are unavailable.** Do not submit an unprotected dismissal or invent a schema field.

The next step is to obtain a supported metadata-capable host or an advertised replay-key argument. There is no trusted CLI fallback here. Neither F-A nor F-B’s requested dismissal has been performed.

### 3. `prior-outcomes`

The batch returned, and readback verified:

- **F-A:** already dismissed as `deferred`, with explanation **“Awaiting a separate migration.”** That prior decision remains; the requested `false_positive` reason was not saved.
- **F-B:** `conflict`. This is not a successful dismissal.

Outcome verification succeeded, but neither requested new transition is confirmed. Do not overwrite the prior decision or retry the conflict automatically. Neither the new requested reason nor a clean review can be claimed from this evidence.

### 4. `saved-sync-pending`

**F-C’s dismissal was saved.** The returned `status: dismissed` and readback confirm the requested reason/explanation. `reconciled: false` means downstream synchronization remains incomplete—not that saving failed.

The user authorized one new synchronization attempt:

- Invoke `pr-review-dismiss` with the **exact retained business arguments**: F-C, `L-CURRENT`, `false_positive`, and the original explanation.
- Use a **new, unique transport key** through `_meta["io.qodo/idempotency-key"]`, retaining it before submission.
- Preserve both original and new requests, keys and receipts.

Replaying the completed original key would only return its stored response; it would not retry synchronization. The new invocation reaches the idempotent endpoint, preserves the stored decision and attempts synchronization again.

Inspect the new result and read back F-C. Report synchronization as completed only if the new evidence establishes that. An `already_dismissed` result is not a second saved transition. Do not invent polling support or make further new-key attempts beyond the authorized one.

### 5. `uncertain-write`

**The write outcome is unknown.** A lost response proves neither success nor failure.

Collect the original operation using its retained receipt. Alternatively, use the supported recovery path to replay the **exact original request with its original key**. Inspect the terminal result and verify the stored disposition before claiming success.

A new key is **not justified** while the original outcome is unknown. It would initiate another handler invocation rather than recover the uncertain one. Any later synchronization attempt requires verified storage and separate authorization, as in case 4.

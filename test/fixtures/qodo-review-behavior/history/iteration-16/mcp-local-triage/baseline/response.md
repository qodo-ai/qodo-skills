**Proposals only. No requests have been sent or finding state changed.**

### 1. `metadata-only`

Batch F-A and F-B because their original review, authorized reason and explanation match.

Proposed MCP `tools/call` parameters (`K1` represents one unique key generated and retained before submission):

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
    "io.qodo/idempotency-key": "K1"
  }
}
```

The key belongs in request metadata, **not** an unsupported `idempotency_key` argument.

Retain the exact request and key before sending, then retain its response. If the response is lost, replay only that exact request with **the same key**. There is no pollable handle; do not invent one or use a new key.

Inspect every per-finding outcome and read back both stored dispositions through supported retrieval. Verify the original finding/review identities, reason and exact explanation. Report synchronization separately:

- `dismissed` with matching readback confirms the requested save.
- `already_dismissed` preserves a prior decision; compare its stored values.
- `conflict` or `not_found` is not success.
- `reconciled: false` means downstream synchronization remains incomplete, not that a confirmed save disappeared.

### 2. `no-replay-transport`

**Blocked: replay-safe writes are unavailable.**

Do not submit the dismissal without protection, invent an argument, or substitute an unavailable CLI. The next action is to establish a supported replay-key transport or schema before submission.

Both requested false-positive dismissals remain unperformed. The verified caller guard supports the recommendation but does not establish saved state.

### 3. `prior-outcomes`

Readback succeeded, but **neither requested new false-positive disposition is confirmed**:

| Finding | Verified outcome |
|---|---|
| F-A | Already dismissed as `deferred`, with explanation “Awaiting a separate migration.” That prior decision remains unchanged. |
| F-B | `conflict`; the requested dismissal did not succeed. |

Do not claim that F-A’s new reason was saved, overwrite its prior decision, or treat F-B’s conflict as a dismissal.

Report the preserved decision and unsuccessful transition. No new assessment or complete coverage evidence was supplied, so a clean review cannot be claimed.

### 4. `saved-sync-pending`

**F-C’s requested dismissal was saved and verified. Downstream synchronization remains incomplete.**

The original operation is completed. Replaying its original key would return the cached result without invoking synchronization again.

For the user-authorized **one new synchronization attempt**, propose another `pr-review-dismiss` call with unchanged business arguments:

- `finding_ids`: `["F-C"]`
- `local_review_id`: `"L-CURRENT"`
- `reason`: `"false_positive"`
- `explanation`: the exact retained authorized explanation

Use a **fresh transport key**, `K_SYNC`, in `_meta["io.qodo/idempotency-key"]`. This is a separately authorized synchronization attempt, not uncertain-response recovery or permission to change the decision.

Retain both requests, their distinct keys and receipts. Inspect the new result and read back the disposition. Claim synchronization completion only with affirmative evidence. If it remains incomplete, report that and stop after the one permitted attempt. If this attempt’s response is lost, recover using **K_SYNC**, not another fresh key.

### 5. `uncertain-write`

**The write outcome is unknown.**

First collect the existing operation using its retained receipt. Alternatively, recover by replaying the exact retained request with its **original key**. Preserve its business arguments and metadata; do not submit a parallel attempt.

A new key is **not justified** while admission or completion is uncertain: it could invoke the handler again rather than recover the original response.

After collection or same-key replay, inspect the terminal outcome and read back stored state. Until then, claim neither a successful dismissal nor a failed save. Any later synchronization attempt requires confirmed completion and covering authorization.

None of these status-write outcomes alone establishes complete review coverage or overall readiness.

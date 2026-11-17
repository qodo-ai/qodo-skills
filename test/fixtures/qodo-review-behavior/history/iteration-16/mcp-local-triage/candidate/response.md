All actions below are proposals only. No services were invoked or finding states changed.

### 1. `metadata-only`

Batch F-A and F-B because their original review, authorized reason and explanation match.

Proposed MCP `tools/call` parameters, using a fresh key allocated once:

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
    "io.qodo/idempotency-key": "8b43ccf6-777b-4b6a-a7d8-626bd939e93c"
  }
}
```

Do not add an unsupported `idempotency_key` argument.

- Retain the exact request and key before submission, then retain the synchronous response.
- Verify each finding’s returned outcome and read back its stored reason and explanation. Report any unavailable verification; do not invent a readback endpoint.
- Claim a newly saved dismissal only when supported by the outcomes. `already_dismissed` preserves the prior decision; `conflict` is not success.
- If the response is lost, replay the **exact request with the same key**. Do not rotate the key.
- There is no pollable operation handle. Do not invent one or poll.

### 2. `no-replay-transport`

**The write is blocked.** Neither schema arguments nor host metadata can carry replay protection, and no trusted CLI is available.

Do not submit an unprotected dismissal or invent an argument. The next action is to obtain a supported replay-safe transport capability. Both requested dismissals remain unperformed by this workflow; explicit dismissal authority does not remove the transport safety requirement.

### 3. `prior-outcomes`

Readback verification succeeded, but neither requested `false_positive` transition succeeded:

| Finding | Confirmed outcome | What can be claimed |
|---|---|---|
| F-A | `already_dismissed`; reason `deferred`; explanation “Awaiting a separate migration.” | The prior dismissal remains. The requested reason and explanation were **not** saved. |
| F-B | `conflict` | No successful requested transition is established. |

Report the discrepancy and conflict, then stop. Do not overwrite the prior decision or initiate another assessment without covering authority. These outcomes do **not** establish a clean review.

### 4. `saved-sync-pending`

**F-C’s dismissal succeeded.** `status: dismissed` and readback confirm the requested disposition is stored. `reconciled: false` means downstream synchronization remains incomplete—not that storage failed.

The original operation is completed. Replaying its original key would return its stored result without attempting synchronization again.

For the separately authorized **one new synchronization attempt**, propose another `pr-review-dismiss` invocation with:

- `finding_ids`: `["F-C"]`
- `local_review_id`: `"L-CURRENT"`
- `reason`: `"false_positive"`
- `explanation`: the **exact retained original explanation**
- `_meta["io.qodo/idempotency-key"]`: a **new unique key**, distinct from the original key

Keep all business arguments unchanged. Retain both requests, both keys and their responses. Do not invent a polling handle.

Inspect the new result and verify each stored outcome again. Claim synchronization only if confirmed. If synchronization remains incomplete, report that separately and stop after the permitted attempt. An uncertain response to this new invocation must be recovered using **its own retained key**, not another fresh key.

### 5. `uncertain-write`

The original F-C outcome is **unknown**. Neither successful storage nor failed storage can be claimed.

Collect the original operation using its retained receipt. Alternatively, recover through exact replay of the retained request with its **original key**. Preserve all business arguments.

Verify the recovered terminal outcome and stored disposition before reporting success or synchronization status. **A new key is not justified:** this is recovery of an uncertain invocation, not a separately authorized synchronization attempt after verified storage.

Finding-status operations alone do not establish assessment coverage or overall review readiness.

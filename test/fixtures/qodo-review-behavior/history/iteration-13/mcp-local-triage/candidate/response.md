All actions below are proposals only. No requests or state changes were made.

### 1. `metadata-only`

F-A and F-B can share one batch: both belong to L-ORIGINAL and have the same authorized reason and explanation.

Proposed MCP request:
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
      "io.qodo/idempotency-key": "triage-L-ORIGINAL-FA-FB-01"
    }
  }
}
```

Reserve that unique key before submission and retain the exact request, key and returned result. Do **not** add an unsupported `idempotency_key` tool argument.

Inspect the synchronous response for errors and each finding’s outcome. Read back both stored dispositions, verifying the finding IDs, local-review association, reason and explanation before claiming success. Report synchronization separately.

There is no pollable handle. If the response is lost, replay only the exact retained request with the same key; do not invent polling or rotate the key.

### 2. `no-replay-transport`

The write is blocked: neither the schema nor the host provides replay protection, and no trusted CLI is available.

Do not submit an unprotected dismissal. Report that recording F-A and F-B remains unperformed. A supported replay-key transport is required; authorization and verified evidence alone do not remove that requirement.

### 3. `prior-outcomes`

- **F-A:** Its existing dismissal remains `deferred`, with explanation “Awaiting a separate migration.” `already_dismissed` is not a newly saved `false_positive` decision.
- **F-B:** `conflict` is not success; the requested transition was not established.
- Readback verified these outcomes, but neither requested new disposition can be claimed as saved.

Do not overwrite the prior decision or automatically retry the conflict. Neither a clean review nor overall readiness is established by these results.

### 4. `saved-sync-pending`

F-C’s requested dismissal **was saved and verified**. `reconciled: false` means downstream synchronization remains incomplete—not that storage failed.

The user permits one new synchronization attempt. Propose a new `pr-review-dismiss` invocation with the unchanged business arguments:

- `finding_ids: ["F-C"]`
- `local_review_id: "L-CURRENT"`
- `reason: "false_positive"`
- The exact retained original explanation.

Send it using a **new, unique, retained** `_meta["io.qodo/idempotency-key"]`. Preserve both requests, keys and results.

Replaying the completed original key would only return its stored result; it would not retry synchronization. Inspect the new response and read back the disposition again. Claim synchronization only if the new evidence confirms it. Do not invent a polling handle or exceed the one authorized attempt.

### 5. `uncertain-write`

F-C’s write outcome is unknown. Do not claim that it succeeded, failed or merely awaits synchronization.

First collect the original operation using its retained supported receipt. Alternatively, recover through an exact replay of the retained request with its **original key**. Verify the resulting outcome and read back stored state.

A new key is **not justified** while the original outcome remains unknown. It would initiate another handler invocation rather than recover the uncertain one.

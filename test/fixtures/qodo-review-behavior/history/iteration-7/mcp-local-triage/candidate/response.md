Proposals only. No commands, service calls, file changes or finding-status writes were executed.

### 1. `metadata-only`

Proposed MCP `tools/call` parameters for the authorized Qodo dismissal batch:

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
    "io.qodo/idempotency-key": "d8d05bd1-654b-4d04-85da-a63e34015550"
  }
}
```

- Both findings share the original local-review ID, reason and explanation, so one batch is appropriate.
- Send the replay key as request metadata—not an unsupported `idempotency_key` argument.
- Retain the key and exact request in parent task state across resumes and any permitted replay. Uncertain acceptance must not cause a new key or altered batch.
- Inspect errors and each finding’s returned outcome, then read back **both** stored dispositions through the supported read capability. Verify their original identities, stored reason and exact explanation.
- A conflict or failed reconciliation is not success. If `reconciled: false` is returned, synchronization requires an exact-request retry with the same key, subject to retry restrictions.

**Pending evidence:** submission response, per-finding readbacks and reconciliation outcomes. No successful dismissal can yet be claimed.

### 2. `no-replay-transport`

**Stop before submission:** this host lacks replay-safe write capability.

Require a supported replay-key argument or metadata-capable MCP host before proposing execution. Do not omit replay protection, invent an argument or substitute an unavailable CLI.

The evidence supports recommending both false-positive dismissals, but neither requested stored dismissal has been performed or verified.

### 3. `prior-outcomes`

On the supplied response and confirmed readback:

| Finding | Confirmed outcome | What it establishes |
|---|---|---|
| F-A | `already_dismissed`; reason `deferred`; explanation “Awaiting a separate migration.” | The prior dismissal remains. The newly requested reason and explanation were **not** saved. |
| F-B | `conflict` | No successful new dismissal is established. Its broader disposition is not supplied. |

Readback verification succeeded; the requested false-positive batch did **not** succeed. Do not overwrite the prior decision or automatically resubmit the conflict.

Neither the new requested reason nor a clean review can be claimed. No complete current inventory, coverage or passing-check evidence is supplied, and these outcomes alone do not justify another assessment.

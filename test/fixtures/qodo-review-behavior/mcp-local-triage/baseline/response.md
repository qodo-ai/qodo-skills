## 1. `metadata-only`

Propose one `pr-review-dismiss` batch for the Qodo findings. Both share the original review, reason and explanation.

**Proposed MCP `tools/call` parameters:**
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
    "io.qodo/idempotency-key": "triage-40c2d726-180d-4b3f-a8df-2a6d88ba7d52"
  }
}
```

- Use the documented metadata transport; do not invent an `idempotency_key` argument.
- Retain this key, exact arguments and original finding/review mapping in existing task state. Any permitted replay of this logical action must use the same key and arguments.
- Check transport/tool errors and every per-finding outcome. Read back each stored disposition, verifying the finding identity, review identity, reason and explanation.
- Report conflicts, missing findings or incomplete reconciliation separately. `already_dismissed` is not proof that the requested reason was newly stored.

**Pending:** submission, returned outcomes and readback. Nothing has been written.

## 2. `no-replay-transport`

**The dismissal write is blocked.** Neither arguments nor metadata can carry the required replay key, and no trusted CLI is available.

Propose resuming through a trusted host that supports the documented replay metadata. Do not submit without replay protection, invent a field, or switch to an untrusted launcher.

Both authorized dismissals remain **unperformed**; there is no write receipt or verification evidence.

## 3. `prior-outcomes`

| Finding | Verified outcome | Meaning |
|---|---|---|
| F-A | `already_dismissed`; reason `deferred`; explanation “Awaiting a separate migration.” | The prior dismissal remains. The requested `false_positive` disposition was not newly saved. |
| F-B | `conflict` | The requested dismissal did not succeed. No further stored disposition is established. |

The readback successfully verified these outcomes; it did **not** verify successful new dismissals.

Do not claim that the new reason was stored or that the review is clean. Full inventory, coverage and readiness evidence are not supplied. Preserve the conflict for investigation; do not overwrite the prior decision or launch another assessment merely to chase a clean result.

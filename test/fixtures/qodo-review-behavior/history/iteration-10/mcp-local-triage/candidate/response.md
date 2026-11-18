## 1. `metadata-only`

Propose one batch because both findings share the original local review, reason, and explanation.

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
      "io.qodo/idempotency-key": "77d6d862-f120-41c4-bfc7-54920a540354"
    }
  }
}
```

The replay key belongs in request metadata, **not** an unsupported `idempotency_key` argument.

Retain that key with the exact request and original finding-to-review mapping before submission. Any permitted replay must reuse the same request and key.

After submission:
- Check for a tool error and inspect each finding’s returned outcome.
- Read back **both** stored dispositions, verifying their identities, reason, and explanation.
- Report prior dispositions or conflicts separately; neither proves the requested transition occurred.
- Report saved status separately from downstream synchronization.

Nothing has been submitted or verified in this proposal.

## 2. `no-replay-transport`

**Do not submit the dismissal.** Neither the schema nor the host provides replay-key transport, so replay-safe status writing is unavailable.

Both requested `false_positive` dismissals remain unperformed despite valid authorization and supporting evidence. Resume only through a trusted interface supporting the required replay protection. Do not omit protection, invent an argument, or use an untrusted CLI.

## 3. `prior-outcomes`

Readback verified the outcomes, but **no new requested dismissal succeeded**:

| Finding | Verified outcome | Meaning |
|---|---|---|
| F-A | `already_dismissed`; reason `deferred`; explanation “Awaiting a separate migration.” | The prior disposition remains. The requested `false_positive` reason and new explanation were not saved. |
| F-B | `conflict` | The requested transition did not succeed. No other disposition can be inferred. |

Report these outcomes without overwriting the prior decision or claiming success for the batch. Neither the new requested reason nor a clean review can be claimed. No new assessment is justified merely to obtain a clean label.

## 4. `saved-sync-pending`

**F-C’s dismissal succeeded.** `status: dismissed` and readback confirm that the requested `false_positive` reason and explanation are stored.

`reconciled: false` means downstream synchronization remains incomplete—not that storage failed.

The next permitted action is to replay **F-C’s exact retained request with its same retained key**, using the authorized synchronization retry. Do not create a new dismissal identity or change the request. Inspect the retry result and verify the stored disposition and synchronization outcome.

Until synchronization is confirmed, report: **dismissal saved; downstream synchronization pending**. This finding’s disposition alone does not establish overall review readiness.

## 1. `metadata-only`

The authorized batch can use the documented metadata replay key. Proposed MCP `tools/call` parameters:

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
    "io.qodo/idempotency-key": "b9c330e8-9a4a-4c58-a8bc-48710d59b301"
  }
}
```

Both findings share the original local-review ID, reason and explanation, so one batch is appropriate. Do **not** add an unsupported `idempotency_key` argument.

Retain the exact request and key in recovery state before submission. Any permitted replay must reuse both unchanged.

After submission, check `isError` and every per-finding outcome, then read back both stored dispositions. Verify the stored reason and explanation individually. Report prior dispositions, conflicts and incomplete synchronization separately; submission alone does not prove persistence.

## 2. `no-replay-transport`

**Stop before submitting.** Neither the schema nor this host provides replay-safe write capability.

The next action is to obtain a supported host metadata transport or a schema with a documented replay-key argument. There is no trusted CLI fallback. Do not invent an argument or submit an unprotected write.

Neither requested dismissal has been performed. Existing authorization and supporting evidence remain valid, but no finding-state change can be claimed.

## 3. `prior-outcomes`

The readback succeeded, but **neither newly requested `false_positive` transition succeeded**:

| Finding | Verified outcome |
|---|---|
| F-A | Already dismissed. The prior reason remains `deferred`, with explanation “Awaiting a separate migration.” |
| F-B | `conflict`; the requested dismissal did not succeed. No further stored disposition is established by the supplied evidence. |

F-A’s existing dismissal is confirmed—not newly recorded or replaced. Do not claim the requested reason was saved for either finding.

A clean review cannot be claimed from these outcomes. Preserve both results and stop; do not overwrite dispositions, retry automatically or buy another assessment to chase a clean result.

## 4. `saved-sync-pending`

**F-C’s dismissal succeeded and is stored.** Readback confirms the requested `false_positive` reason and explanation. `reconciled: false` means downstream synchronization remains incomplete, not that the saved transition failed.

The next permitted action is one synchronization retry using the **exact retained request and the same replay key**, through its original supported transport. Do not create a new logical dismissal or key.

Inspect the retry result and verify the disposition again. Report storage and synchronization separately. If synchronization remains incomplete, report it as pending rather than entering an automatic retry loop. No new assessment or overall clean-review claim follows from this dismissal.

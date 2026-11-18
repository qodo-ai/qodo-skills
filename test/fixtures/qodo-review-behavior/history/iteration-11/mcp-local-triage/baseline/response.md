**Proposals only; no requests were sent or finding states changed.** Key names below represent unique keys generated once and retained.

### 1. `metadata-only`

Both findings share the original review, authorized reason and explanation, so propose one batch:

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
      "io.qodo/idempotency-key": "K-AB"
    }
  }
}
```

Do not add an unsupported `idempotency_key` argument.

Retain K-AB, the exact request, original finding/review mapping, operation receipt and returned outcomes. Recover an uncertain response through the original operation or exact same-key replay.

Check tool errors and each finding’s result, then read back both stored dispositions. Verify the actual reason and explanation match the request. Report prior dismissals, conflicts and synchronization failures individually; batch completion alone does not establish success.

### 2. `no-replay-transport`

**Blocked: do not submit an unprotected write.** Neither supported replay-key path is available, and there is no trusted CLI.

The next prerequisite is a trusted host/tool path with documented replay protection. Do not invent an argument or omit protection. Neither requested dismissal has been performed; the authorization and supporting evidence remain valid but unexecuted.

### 3. `prior-outcomes`

| Finding | Confirmed outcome |
|---|---|
| F-A | The prior dismissal remains: reason `deferred`, explanation “Awaiting a separate migration.” The requested `false_positive` reason was **not** saved. |
| F-B | `conflict`; the requested transition did **not** succeed. |

The call returned outcomes, and readback verified them. That does not mean the requested batch succeeded.

Do not overwrite the prior decision, treat the conflict as success, or claim a clean review. No new assessment, code change or broader authority supports further action.

### 4. `saved-sync-pending`

**F-C’s requested dismissal was saved and verified.** `reconciled: false` means downstream synchronization remains incomplete—not that the dismissal failed.

The user permits one new synchronization attempt:

- Call `pr-review-dismiss` with the **exact retained business arguments**: F-C, `L-CURRENT`, `false_positive`, and the original explanation.
- Supply a **new unique metadata key**, K-C-SYNC, through `_meta["io.qodo/idempotency-key"]`.
- Preserve the original request/key/receipt separately, and retain this new request/key/receipt.

Replaying the completed operation with its original key would only return its original result; it would not invoke the handler again. The new key allows the authorized synchronization attempt. The endpoint preserves the stored decision while retrying synchronization.

Inspect the new result and read back F-C. Confirm the disposition is unchanged and report whether reconciliation completed. If it remains incomplete, stop after this permitted attempt; do not silently retry again or claim full synchronization.

### 5. `uncertain-write`

**The write outcome is unknown.** Losing the response proves neither success nor failure.

First collect the retained original operation. If recovery requires replay, send the **exact original request with its original key**, then verify the returned outcome and stored disposition.

A new key is **not justified** while admission or completion remains uncertain. Unlike case 4, there is no confirmed completed operation and verified saved disposition establishing a separate synchronization action. Do not claim the dismissal was saved, failed, or made the review clean.

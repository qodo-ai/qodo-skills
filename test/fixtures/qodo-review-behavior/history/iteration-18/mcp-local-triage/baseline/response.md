I read the qodo-review skill and its `local-triage.md` reference, and checked the relevant parts of `mcp-review.md` and `cli-execution.md`. Everything below is a proposal only. I didn't run, call or write anything.

---

### 1. `metadata-only`: proposed keyed dismissal

**Checks before sending:** You explicitly authorized this. F-A and F-B have the same `local_review_id`, reason and explanation, so they can go in one batch. Current code and tests support the explanation. The schema has no `idempotency_key` argument, so the key goes only in the documented metadata field. No key is added to the arguments.

**Proposed request (sent once):**
```json
{
  "tool": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-A", "F-B"],
    "local_review_id": "L-ORIGINAL",
    "reason": "false_positive",
    "explanation": "The mandatory caller guard rejects this input."
  },
  "_meta": { "io.qodo/idempotency-key": "<KEY-1: one unique value, created once for this batch>" }
}
```

**Keeping the key:** Save KEY-1 and the exact arguments in task state before sending. This call returns no operation handle, so the saved request is the only way to recover. If the response is lost, resend exactly this request: same arguments, same `_meta` key. Don't create a new key, change the arguments or split the batch.

**Checking the outcome:** Read each finding's result separately. It counts as success only if the result is `status: dismissed`, the stored reason is `false_positive` and the stored explanation matches. Then read back the stored state for both findings. Report `reconciled` separately: `false` means the dismissal is saved but downstream sync isn't finished. `already_dismissed` with different stored values, `conflict` and `not_found` are not successes. A dismissal doesn't count as review coverage, and it doesn't settle any other finding.

### 2. `no-replay-transport`: blocked, nothing sent

**Next action:** Report that this host has no way to send a replay key. The schema has no key argument, the host can't send `_meta`, and there's no trusted CLI. I won't send an unprotected write, and I won't invent a key field.

**What remains undone:** F-A and F-B are still not dismissed in stored state. Your authorization and the supporting evidence still apply, but deciding to dismiss in conversation doesn't create a stored dismissal. To continue, you'd need one of these:
- a host that supports `_meta["io.qodo/idempotency-key"]`
- a server schema that advertises `idempotency_key`
- a trusted CLI

### 3. `prior-outcomes`: neither requested dismissal was saved

- **F-A:** Nothing new was saved. The earlier dismissal stays as it was: reason `deferred`, explanation "Awaiting a separate migration." I can't claim the requested `false_positive` reason or the new explanation. The finding is dismissed, but under the old decision.
- **F-B:** `conflict` means it was not dismissed. Nothing succeeded for F-B.
- **Claims:** Neither the new reason nor a clean review can be claimed. The overall status is **Needs action**. Changing F-A's reason would need a capability and authority that weren't given. F-B needs investigation: if the review reference is stale, run a new review and reassess before acting. Replaying the request wouldn't help either way. The same key returns the same result, and a new call can't override a stored decision.

### 4. `saved-sync-pending`: decision saved, sync still pending

**What happened:** The dismissal of F-C is saved, and readback confirms the requested `false_positive` reason and explanation are stored. Only downstream sync is unfinished (`reconciled: false`). This isn't a failed write, and the decision shouldn't change.

**Key handling:** Don't resend the original key to retry sync. That operation already completed, so the transport would return the stored result without running the handler again. Downstream sync wouldn't be attempted. Keep the original request, key and receipt as the record of that write.

**Proposed single sync attempt:** Send the same business arguments with **one new key**. This is justified only because a new handler run is needed to retry sync. The endpoint keeps the stored decision and retries sync.
```json
{
  "tool": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-C"],
    "local_review_id": "L-CURRENT",
    "reason": "false_positive",
    "explanation": "<the identical stored explanation>"
  },
  "_meta": { "io.qodo/idempotency-key": "<KEY-SYNC-1: new, saved before sending>" }
}
```
If this response is lost, resend only KEY-SYNC-1 exactly as it was. Expect `already_dismissed` with matching stored values, then check `reconciled` and read back again. If it's still `false`, stop and report sync as pending, because you allowed only one attempt.

### 5. `uncertain-write`: recover using the original request

**Next action:** First, use the saved receipt to fetch the original operation's result. If that can't return a final result, resend the exact saved request with the **original key**. If the original write did go through, the transport returns its result instead of running it again. Then read back F-C's stored state and check the reason, explanation and `reconciled`.

**A new key isn't justified.** We don't know yet whether the write happened. A new key would start a second handler run instead of recovering the first one. A new key only becomes relevant afterwards, if a confirmed `dismissed` result with `reconciled: false` calls for the separately authorized sync attempt in case 4.
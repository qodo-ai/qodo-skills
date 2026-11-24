I read the qodo-review Skill, its finding-status write policy, `references/local-triage.md` and the relevant part of `references/mcp-review.md`. These are proposals only. I ran no commands, called no services and wrote nothing.

---

### 1. `metadata-only`: proposed keyed dismissal

All the conditions are met: you explicitly authorized it, the original finding IDs map to their real `local_review_id`, both findings share one reason and one explanation, and the code confirms the explanation. So F-A and F-B can go in one batch. The schema has no `idempotency_key` argument, so the key travels in the host's documented metadata field. I would not add an extra argument to the schema.

```jsonc
// tool: pr-review-dismiss
{
  "arguments": {
    "finding_ids": ["F-A", "F-B"],
    "local_review_id": "L-ORIGINAL",
    "reason": "false_positive",
    "explanation": "The mandatory caller guard rejects this input."
  },
  "_meta": { "io.qodo/idempotency-key": "<K1: stable, generated once for this invocation>" }
}
```

**Keeping the key**
- Generate K1 once, before sending. Save the full request (arguments plus K1) in task state before sending it.
- If the response is lost, the only recovery is to replay this exact request with this exact K1. The call returns a synchronous result with no operation handle, so there is nothing to poll. A new key is not allowed for recovery.

**Checking the outcome**
- Look at the result for each finding separately. Confirm it shows `status: dismissed` with the stored `reason: false_positive` and the requested explanation.
- `already_dismissed` with a different stored reason or explanation, `conflict` or `not_found` do not count as success.
- `reconciled: false` would mean the status is saved but downstream sync is unfinished. I would report those two facts separately.
- Read back each stored outcome before claiming anything.

### 2. `no-replay-transport`: stop before writing

There is no `idempotency_key` argument, no metadata path and no trusted CLI. That means there is no replay-safe way to write, so I would not send an unprotected `pr-review-dismiss` call.

**Next step:** report the blocker, which is that this host has no replay-safe way to write a finding status. To proceed, you would need a host that can send `_meta["io.qodo/idempotency-key"]`, a schema with a key argument, or a trusted CLI.

**Not done:** nothing is stored for F-A or F-B. They stay in their current state in Qodo. My false-positive assessment, backed by the code and tests, exists only in this conversation and is not a stored dismissal.

### 3. `prior-outcomes`: no new write succeeded

- **F-A:** it is still dismissed, but under the earlier decision: reason `deferred`, explanation "Awaiting a separate migration." The requested `false_positive` reason and its explanation were **not** saved. Calling F-A "dismissed" is accurate. Calling it "dismissed as false positive" is not.
- **F-B:** `conflict` is not success. This request did not dismiss it.
- **What I can't claim:** a new successful write, the new reason, or a clean review. A clean review is ruled out anyway, because a dismissal never establishes review coverage. F-B is unresolved and F-A has a different disposition than you asked for.
- **Status: Needs action.** Changing F-A's stored decision or settling F-B's conflict needs a decision from you and new evidence or authority. With no new code, assessment or authority, I would report this and stop. I would not retry or work around the conflict.

### 4. `saved-sync-pending`: stored, sync unfinished

**What happened:** the transition is saved. F-C is `dismissed` with the requested `false_positive` reason and explanation, and the readback confirms it. Only downstream sync is unfinished (`reconciled: false`). This is not a failed write.

**Request and key:** replaying the original request with the original key won't help. The original operation completed, so a same-key replay just returns the stored result and never retries sync. Your one permitted retry therefore needs a **new invocation with a new key**, using the same business arguments:

```jsonc
// tool: pr-review-dismiss
{
  "arguments": {
    "finding_ids": ["F-C"],
    "local_review_id": "L-CURRENT",
    "reason": "false_positive",
    "explanation": "<identical to the original request>"
  },
  "_meta": { "io.qodo/idempotency-key": "<K2: new, generated once, retained before sending>" }
}
```

- Keep both requests, both keys (K1 and K2) and both results. Keep the original receipt too.
- The status endpoint is idempotent, so it keeps the stored decision and only retries sync.
- Check the new result for F-C, then read back again. Report sync as done only if the new result shows `reconciled: true`. If it still shows `false`, report the status as stored and sync as still unfinished, then stop. That was the only permitted attempt.
- If K2's response is lost, recover it only by replaying K2 exactly. Don't rotate to a third key.

### 5. `uncertain-write`: collect first, no new key

**Next step:** the transport returned a receipt the host can collect, so collect that original operation first. If collection isn't available or doesn't give a terminal result, replay the exact retained request with the **original key**. Either way, check the per-finding result and read back the stored state for F-C before claiming anything.

**A new key is not justified.** The outcome is unknown, and an unknown outcome does not justify changing the key. A new key would start a new handler run instead of recovering the original one. That would hide whether the first write happened, and it goes beyond what was authorized. A new key only becomes appropriate after storage is confirmed and a separate sync attempt is authorized, as in case 4.

If neither collection nor replay produces an outcome, I would report the recovery as unavailable and F-C's status as unknown. I would not claim it was stored or synced.
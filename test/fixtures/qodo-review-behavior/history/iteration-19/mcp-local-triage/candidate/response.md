I read the qodo-review skill, `references/local-triage.md`, and the replay rules in `references/mcp-review.md`. Everything below is a proposal only. I ran no commands, called no tools, wrote no files and changed no finding state.

---

### 1. `metadata-only`

**Proposed request.** One batch is enough, because both findings share the same review, reason and explanation.

```jsonc
// tools/call → pr-review-dismiss
{
  "name": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-A", "F-B"],
    "local_review_id": "L-ORIGINAL",
    "reason": "false_positive",
    "explanation": "The mandatory caller guard rejects this input."
  },
  "_meta": { "io.qodo/idempotency-key": "<K1: one new stable key for this invocation>" }
}
```

- The key goes only in `_meta`. The schema has no `idempotency_key` argument, so I wouldn't add one. The rule that two keys must match doesn't apply here because only one is sent.
- The IDs are the original finding IDs and their real `local_review_id`. No run ID or PR URL is used in its place.

**Key retention.**
- Create K1 and save it, together with the exact arguments, before sending.
- Keep K1 after the call returns. The tool returns a synchronous result with no operation handle, so there is nothing to poll.
- If the response is uncertain, the only recovery is to replay this exact request with K1. Don't change the arguments and don't create a new key.

**Outcome verification.**
- Check `isError`. Then check each finding's result separately.
- Treat the write as successful only when the result shows `dismissed` with stored reason `false_positive` and the requested explanation.
- `already_dismissed` means an earlier decision was kept. Compare its stored values with this request.
- `conflict` and `not_found` are not success.
- Report `reconciled` as its own fact, separate from whether the status was saved.
- Then read back the stored outcome for F-A and F-B before reporting either as dismissed.

### 2. `no-replay-transport`

**Next action:** don't submit. The schema has no key argument and the host can't send `_meta`, so there is no replay-safe way to write. Sending the call without protection is not allowed. Report the gap to the user. To proceed, one of these is needed:
- a host that can send request metadata,
- a schema that accepts an idempotency key, or
- a trusted CLI.

**What remains unperformed:**
- The F-A and F-B dismissals were not recorded and no readback was done.
- Both findings stay in their current state, even though the authorization and the code/test evidence are still valid.
- Skipping them in conversation does not count as a stored dismissal.

### 3. `prior-outcomes`

- **F-A:** no new write happened. An earlier dismissal is still in place, with reason `deferred` and explanation "Awaiting a separate migration." The requested `false_positive` reason and its explanation were **not** saved, and I can't claim them.
- **F-B:** `conflict`. This is not success, and this request did not dismiss F-B.
- **What succeeded:** only the batch call itself, which returned outcomes that readback confirmed. Neither finding received the requested disposition.
- **Claims:** I can't claim the new reason was saved, and I can't claim a clean review. Even successful dismissals would not establish review coverage. Here F-B is unresolved and F-A carries a different decision.
- **Next step:** no new evidence or authority was supplied, so report the result as "Needs action" and stop. There should be no retry, no attempt to overwrite F-A, and no reinterpretation of F-B's conflict. Whether to change F-A's reason or resolve F-B's conflict is the user's decision.

### 4. `saved-sync-pending`

**What happened:** the dismissal **was saved**. `status: dismissed`, the requested stored reason and explanation, and the readback all confirm it. **Downstream synchronization is incomplete** (`reconciled: false`). This is not a failed transition.

**Why the original key won't help:** replaying the completed request with its original key returns the stored result. It does not run the handler again, so it would not retry synchronization.

**Proposed request (one new invocation):**
- Use the same business arguments: `finding_ids: ["F-C"]`, `local_review_id: "L-CURRENT"`, reason `false_positive`, and the same explanation.
- Send `_meta["io.qodo/idempotency-key"]` with a **new key, K2**, saved before sending.
- Keep the original request, key and receipt alongside K2's request and result.

**Expected handling:**
- The endpoint should keep the stored decision and attempt synchronization again.
- Check the new result per finding (it will likely be `already_dismissed` or `dismissed` with the same stored values). Read back the stored outcome again and report `reconciled` separately.
- If `reconciled` is still `false`, report that synchronization is still incomplete and stop. The user permitted only one attempt.
- If K2's response is lost, recover by replaying the exact K2 request. Don't create a K3.

### 5. `uncertain-write`

**Next action:** collect the retained operation using its receipt. That handle came from the transport, so collecting it is supported.
- If the status call itself fails in transport, retry collection once, after the returned delay (or 15 seconds if none is given).
- If collection isn't available, replay the **exact** original request with the **original** key.
- After either path, check the per-finding result and read back the stored state.

**Is a new key justified? No.**
- An unknown outcome does not allow switching keys.
- A new key is only for a separately authorized synchronization attempt **after storage has been verified**, as in case 4. That condition isn't met here.

If collection and replay both fail to produce an outcome, report that recovery is unavailable and the F-C outcome is unknown. Don't claim the dismissal was stored or that synchronization happened.
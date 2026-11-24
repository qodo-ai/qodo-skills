I read the qodo-review Skill and its `local-triage.md` and `mcp-review.md` references. Nothing below has been run, written or changed. These are proposals only.

## 1. `metadata-only`: proposed keyed dismissal

**Request** (one batch: same review, same reason, same explanation):

```json
{
  "tool": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-A", "F-B"],
    "local_review_id": "L-ORIGINAL",
    "reason": "false_positive",
    "explanation": "The mandatory caller guard rejects this input."
  },
  "_meta": { "io.qodo/idempotency-key": "<new stable key, e.g. dismiss-L-ORIGINAL-fp-<uuid>>" }
}
```

- The key goes only in `_meta`. I wouldn't add an `idempotency_key` argument, because the schema doesn't have one.
- I'd use the original finding IDs and their actual `local_review_id`. I would never use a run ID or PR URL instead.

**Keeping the key:** Save the exact request and key in task state before sending. There's no operation handle and no polling, so if the response is lost, the only recovery is to replay the same request with the same key. Don't change any argument and don't make a new key.

**Checking the outcome:**
- Look at each finding's returned outcome separately.
- Confirm the stored `reason` and `explanation` match the request.
- Read back the stored state for both findings.
- Report storage and `reconciled` as separate facts.
- `already_dismissed` with different stored values, `conflict` or `not_found` don't count as success.

## 2. `no-replay-transport`: blocked

**Next action:** Report that the replay-safe write capability is missing, and stop. I wouldn't send an unprotected `pr-review-dismiss` call. There's no CLI to use instead, and I wouldn't invent a key field.

**Not done:** No dismissal is recorded for F-A or F-B, so their stored state is unchanged and they remain open. The evidence for false_positive still stands. To proceed, the host needs `_meta` metadata support, a schema with a replay-key argument, or a trusted CLI.

## 3. `prior-outcomes`: no new write succeeded

- **F-A:** The earlier dismissal is still in place: `deferred`, "Awaiting a separate migration." The requested `false_positive` reason and explanation were **not** saved. F-A is dismissed, but under the earlier decision, not the new one.
- **F-B:** `conflict` means it failed. F-B wasn't dismissed by this batch.
- **Claims:** Neither the new reason nor a clean review can be claimed. The outcome is **Needs action**:
  - F-B is unresolved.
  - Whether to replace F-A's earlier disposition is a human decision, and no authority to do that was supplied.
  - A dismissal never proves review coverage anyway.

## 4. `saved-sync-pending`: stored, sync incomplete

**What happened:** The F-C dismissal is **saved**. The status, reason and explanation are stored and confirmed by readback. Only the downstream sync is incomplete (`reconciled: false`). This is not a failed write.

**Proposed request:** One **new** invocation with the same business arguments and a **new** key:

```json
{
  "tool": "pr-review-dismiss",
  "arguments": {
    "finding_ids": ["F-C"],
    "local_review_id": "L-CURRENT",
    "reason": "false_positive",
    "explanation": "<identical to the original request>"
  },
  "_meta": { "io.qodo/idempotency-key": "<new key, distinct from the original>" }
}
```

**Key handling:**
- Don't reuse the original key. A same-key replay of a completed operation just returns the stored result and doesn't run the handler, so no sync would happen.
- With a new key, the call reaches the idempotent endpoint. That keeps the stored decision and tries the sync again.
- Keep both requests, both keys and both results. The original receipt also stays.

**Checking the result:**
- Expect `already_dismissed` with matching reason and explanation, and read the stored state back again.
- If `reconciled` is still false, the sync is still incomplete. That uses up the one permitted attempt, so stop and report it.

## 5. `uncertain-write`: recover the original, no new key

**Next action:** Use the retained operation receipt to collect the original operation. If collection isn't possible, replay the exact retained request with the **original** key. Then read back F-C's stored state.

**New key?** No. The outcome is unknown, and that doesn't justify changing the key. A new key could start a second handler call before we know whether the first one finished.

**Then:**
- If the recovered result is saved with `reconciled: false`, report it as in case 4. Another sync attempt would need separate permission, which this case doesn't give.
- If recovery isn't available, report the outcome as unknown. Don't claim it was dismissed or synced.
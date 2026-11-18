**Proposals only. No calls, writes, or finding-state changes were performed.** Each case is independent.

## 1. `metadata-only`

Proposed MCP `tools/call` parameters:

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
    "io.qodo/idempotency-key": "f2033acd-1934-4f55-8d16-2fd251416ced"
  }
}
```

Both findings can share this batch because their original local-review ID, authorized reason, and explanation match. The replay key belongs in documented request metadata—not in an unsupported `idempotency_key` argument.

Before sending, retain the exact request and key. Retain the returned receipt and every per-finding outcome afterward.

Verification:
- Check transport/tool errors and both finding outcomes.
- Read back each stored disposition using the supported read mechanism; verify finding identity, review association, reason, and explanation.
- Distinguish a newly saved dismissal from `already_dismissed`, conflicts, or missing findings.
- Report downstream reconciliation separately from storage.

If the response is lost, replay **only the exact retained request with the same key**. This tool returns synchronously without a pollable handle; do not invent a polling operation.

## 2. `no-replay-transport`

**Do not submit the dismissal.** Neither a schema argument nor host metadata can carry replay protection, and no trusted CLI is available.

The next action is to report the missing replay-safe write capability and request support for the documented metadata path or a schema-advertised replay-key argument. Do not send an unprotected request or invent a field.

Neither requested dismissal has been performed by this proposed action. Authorization and verified code evidence do not remove the transport requirement.

## 3. `prior-outcomes`

| Finding | Confirmed outcome | Meaning |
|---|---|---|
| F-A | `already_dismissed`; reason `deferred`; explanation “Awaiting a separate migration.” | The prior decision remains stored. The requested `false_positive` decision was **not** saved. |
| F-B | `conflict` | The requested transition did **not** succeed. |

The batch returned results and readback confirmed them, but **neither requested new transition succeeded**. Do not overwrite F-A’s prior decision or treat F-B’s conflict as success.

The new requested reason cannot be claimed. Neither a clean review nor overall readiness is established. No supplied code change or new assessment justifies another review merely to clear these outcomes.

## 4. `saved-sync-pending`

**F-C’s requested dismissal was successfully stored. Downstream synchronization remains incomplete.** The returned `status: dismissed` and confirming readback establish storage; `reconciled: false` does not negate it.

Replaying the completed original request with its original key would return the cached result, **not** retry synchronization.

The user explicitly permits one new synchronization attempt:

- Submit a **new invocation** of `pr-review-dismiss`.
- Copy the retained business arguments exactly: F-C, `L-CURRENT`, `false_positive`, and the original authorized explanation. The explanation text is not supplied here; do not reconstruct or replace it.
- Put a **new, distinct key** in `_meta["io.qodo/idempotency-key"]`.
- Retain both original and new requests, keys, receipts, and outcomes.

The idempotent endpoint can preserve the existing dismissal while attempting synchronization again. Inspect the new result and read back the disposition. Claim synchronization only with confirming evidence; otherwise report it as pending or unverified. Collect an operation only if a supported handle is actually returned.

## 5. `uncertain-write`

**The outcome is unknown. A new key is not justified.**

First collect the original operation using its retained receipt and supported collection mechanism. Alternatively, recover through an exact replay of the original request with its original key, unchanged business arguments, and unchanged metadata.

Verify that any collected result belongs to the retained operation, inspect the terminal outcome, and read back F-C’s stored disposition.

Until then, claim neither successful storage nor successful synchronization. Do not rotate the key or start a separate synchronization attempt: verified storage—the prerequisite for case 4’s new invocation—is absent.

Only `eligible` supports a completed local review. The incomplete collector blocks submission; the four invalid artifacts block trustworthy assessment.

All calls below are **proposals only**.

## Submission and collection

Use the authenticated MCP connection; no CLI, installation or login steps.

For the lost initial response, the permitted replay must retain `request_id: "mcp-cart-r1"` and the **exact supplied `params`**, including diff, base, scope and session context. Omit depth for auto. Do not add an `idempotency_key`.

Since the subsequent receipt already identifies a working operation, **do not replay the start now**. Poll every advertised two seconds, within retention:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

After terminal completion with a result available, collect:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two"
})
```

Keep `extended` omitted consistently. Check `isError` on every response.

Before interpreting JSON, verify:

- Every page belongs to the retained operation.
- Encoding, digest, total bytes and total chunks agree across pages.
- Both chunks are present, with contiguous offsets `0` and `90`, without gaps or overlap.
- Pagination ends with `next_cursor: null`.
- The joined, unchanged ASCII bytes match the advertised length and SHA-256.
- The result’s snapshot association matches the retained submission.

## Independent continuations

| Continuation | Proposed action and honest conclusion |
|---|---|
| **1. `eligible`** | Collect both pages and accept the supplied successful integrity check: two chunks, 148 bytes, matching digest and operation/snapshot association. Qodo reports an empty finding inventory, complete finding state and complete assessed coverage. Introduced, still-open, resolved and dismissed buckets are all empty. Together with the supplied focused-test pass, this supports **Ready locally for the retained snapshot**. No additional assessment is needed. |
| **2. `incomplete-collector`** | **Do not submit. Review blocked.** Enumeration is incomplete, included paths cannot be established, and base fetchability is unknown. The requested complete local scope is not safely collectable. Do not substitute an ad hoc diff, another checkout, narrower scope or installation. A suitable tested collector must establish these prerequisites first. |
| **3. `bad-digest`** | Reject the artifact: advertised SHA-256 begins `7d7ca66f`, while the checker calculates `6d7ca66f`. **Review blocked:** no trustworthy finding inventory or assessed-coverage conclusion. Do not interpret the apparent empty findings. |
| **4. `bad-byte-count`** | Reject the artifact: advertised length is 149 bytes; measured length is 148. A matching digest does not override this discrepancy. **Review blocked.** |
| **5. `wrong-operation`** | Reject the artifact for this request. Its pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the retained operation. Internal byte integrity does not establish request association. **Review blocked.** Do not adopt or poll the unrelated operation. |
| **6. `overlapping-pages`** | Reject the collection: page two reports offset `0`, not `90`. Successful concatenation hashing does not repair overlapping page metadata. **Review blocked.** Do not silently correct the offset or invent another ordering. |

For cases 3–6, collector eligibility remains established, but usable review evidence does not. Preserve the original operation as the recovery handle. If the Skill’s collection-retry gate permits a recovery, make **at most one collection-only recovery** against that operation, recollecting and revalidating every page. Otherwise—or if recovery fails—stop with the blocker. Never submit a replacement review.

Even in `eligible`, live-service testing, CI, approvals, hosted PR review, release and deployment remain unverified. The artifact also does not establish context consumption, checkpoint persistence or reusable coverage.

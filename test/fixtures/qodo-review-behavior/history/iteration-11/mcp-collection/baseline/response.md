## Proposed calls only

No service calls, commands, file changes or finding-status writes would be performed in this exercise. The authenticated MCP connection needs no CLI preflight.

### Preserve the original submission

After the lost start response, the permitted retry must reuse `request_id: "mcp-cart-r1"` and the **exact retained arguments**. It must not recollect the worktree or add an unsupported `idempotency_key`.

The proposed retry would have been `start-pre-pr-review` with:

```json
{
  "request_id": "mcp-cart-r1",
  "params": {
    "repo_full_name": "example/cart",
    "repo_host": "github.com",
    "base_sha": "1111111111111111111111111111111111111111",
    "commit_sha": "2222222222222222222222222222222222222222",
    "branch": "feature/cart-review",
    "diff": "diff --git a/src/cart.ts b/src/cart.ts\n--- a/src/cart.ts\n+++ b/src/cart.ts\n@@ -1 +1 @@\n-export const valid = n => n === 1;\n+export const valid = n => n > 0;\n",
    "session_context": {
      "decisions": ["The user selected positive cart counts."],
      "notes": "The mandatory caller rejects non-numeric input. Focused tests passed; no live service was tested.",
      "recent_work": ["Changed the cart-count predicate; this round changes behavior."]
    },
    "review_scope": {
      "stream_id": "f1bcba4fd84bd7e271baea841b4e35e31958043c22e9c3ebc077d803f1ac8417",
      "paths": [],
      "excluded_files": [],
      "skipped_files": [],
      "allowed_sensitive_files": [],
      "complete": true
    }
  }
}
```

Depth remains omitted, selecting auto.

**The subsequent receipt already establishes acceptance**, so do not repeat that start now. Retain operation `41c730de-840d-4b87-a95e-165b8b94f56a`. Its current `working` receipt means pending, not reviewed.

### Collect the accepted operation

Respect the advertised two-second polling interval:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

After a successful terminal-completed receipt with a result available:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "extended": false
})
```

Then follow the returned cursor:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two",
  "extended": false
})
```

Check `isError` on every response. Keep `extended` unchanged. Before interpreting JSON, verify:

- Every page belongs to the retained operation.
- Encoding, digest, byte count and chunk count agree across pages.
- Both chunks are present, with contiguous, non-overlapping offsets: `0`, then `90`.
- Pagination ends with `next_cursor: null`.
- Joined ASCII bytes match the advertised length and SHA-256.
- The resulting assessment matches the retained submitted snapshot.

These are short lifecycle calls, not MCP Tasks.

## Independent outcomes

### 1. `eligible` — ready locally on the supplied evidence

The tested collector establishes complete intended scope, safety exclusions, no omissions and a fetchable exact base. Both artifact pages pass identity, pagination and integrity checks: two chunks, 148 bytes and the matching advertised digest.

Only then interpret:

```json
{
  "findings": [],
  "finding_state": {
    "complete": true,
    "introduced": [],
    "still_open": [],
    "resolved": [],
    "dismissed": []
  },
  "meta": {
    "coverage": {
      "complete": true
    }
  }
}
```

**Report:** Qodo’s assessment completed for the matching submitted snapshot, with complete coverage and finding inventory and no findings. Focused tests passed. This supports local readiness for that snapshot—not a broader “clean” or release-ready claim.

No live service was tested. Reviewer consumption of the submitted context, checkpoint persistence/reusability, hosted PR review, CI, approval, release and deployment are not established by this artifact.

### 2. `incomplete-collector` — review blocked before submission

Do **not** propose a start call. Enumeration stopped early, included paths cannot be established, and base fetchability is unknown. The collector cannot substantiate the requested complete local-change scope.

**Report:** MCP-only local review cannot safely cover this worktree with the supplied collection. No completed assessment or full coverage can be claimed, and local readiness is not established.

A future submission requires eligible collection covering the requested scope and verification of the exact base. Do not substitute an ad hoc diff, another checkout, an invented collection mode or an installation.

### 3. `bad-digest` — review blocked by integrity failure

The advertised digest starts `7d7ca…`; the checker calculates `6d7ca…`. Reject the artifact **before interpreting its apparent findings or coverage**.

**Next action:** At most one permitted collection recovery of the retained operation, as described below. No new start.

### 4. `bad-byte-count` — review blocked by length mismatch

The advertised length is 149 bytes; the joined artifact measures 148. A matching digest does not waive the byte-count check. Reject the artifact before interpretation.

**Next action:** The same bounded collection recovery; no new start.

### 5. `wrong-operation` — review blocked by identity mismatch

Both pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the accepted operation. Internally valid bytes do not associate that other result with this submission.

Do not adopt the other operation, reinterpret it as an alias or claim its coverage.

**Next action:** Recollect only `41c730de-840d-4b87-a95e-165b8b94f56a` within the single permitted recovery.

### 6. `overlapping-pages` — review blocked by invalid page assembly

The second offset is `0`, but must be `90` to follow the first 90-byte chunk. Digest and total-length agreement do not resolve overlapping page metadata.

Do not silently correct the offset or invent an alternate order.

**Next action:** The same bounded collection recovery; no new start.

## Bounded recovery for cases 3–6

Propose one re-collection of the **existing accepted operation**, not another assessment. Respect any returned retry delay or prohibition; the Skill’s collection-retry fallback is 15 seconds when no recovery delay is supplied.

Start result collection without a cursor, retain `extended: false`, and follow the newly returned cursors. Validate the complete recovered page set independently; do not combine it with rejected pages.

Until recovery supplies valid evidence, all four cases remain **review blocked**, even if the operation reports completion. No corrected artifact is supplied here, so recovery success cannot be claimed.

If that recovery fails or remains invalid, stop with the operation ID and specific failure preserved. Do not resubmit, change accounts or deployments, install a CLI, or claim zero findings or local readiness.

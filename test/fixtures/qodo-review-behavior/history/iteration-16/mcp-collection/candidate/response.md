Only **`eligible`** supports verified, completed local-review coverage. **`incomplete-collector`** blocks submission; cases **3–6** block interpretation unless one collection recovery succeeds. All calls below are proposals only.

## Submission identity and collection

Use the authenticated MCP connection; no CLI probes, installation or login are needed. Omit depth for **auto**.

At the original uncertain-admission point, the permitted retry preserves the request ID and **exact retained arguments**:

**`start-pre-pr-review`**
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

Do not add an `idempotency_key`, recollect a different snapshot, or alter context or scope.

**The subsequent receipt already establishes acceptance**, so do not replay the start again. Retain operation `41c730de-840d-4b87-a95e-165b8b94f56a` and poll at the advertised two-second interval:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and the returned operation ID on every receipt. `working` is not a completed assessment.

After terminal completion with a result available:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two"
})
```

Keep `extended` omitted throughout. These are ordinary lifecycle calls, not MCP Tasks.

Before parsing, require matching operation IDs; stable encoding, digest, byte count and chunk count; contiguous offsets starting at zero; and pagination ending at null without cycles. Verify the complete artifact’s digest and byte count, then verify its snapshot/scope association.

## Independent continuations

### 1. `eligible` — ready locally for the submitted snapshot

The tested collector covers the complete intended local change, applies the required exclusions, reports no omissions and verifies base fetchability.

The supplied evidence establishes:

- Two contiguous chunks at offsets **0** and **90**, ending at **148 bytes**.
- Stable `json-ascii` encoding and matching advertised/computed SHA-256.
- Matching retained operation and submitted snapshot.
- Complete finding inventory and complete assessed coverage.

After verification, the artifact contains no findings: `introduced`, `still_open`, `resolved` and `dismissed` are all empty.

**Qodo returned a completed assessment with no findings and verified complete local coverage.** With the supplied passing focused tests, this supports **Ready locally** for that submitted snapshot.

Limitations remain explicit: no live service was tested; context consumption and checkpoint persistence/reuse are not evidenced. This does not establish hosted PR review, CI, approval, release or deployment readiness.

### 2. `incomplete-collector` — review blocked before submission

Propose **no start call**. Enumeration stopped, included paths are unknown, and base fetchability was not checked. The requested complete-local-change scope therefore cannot be safely submitted.

Do not change `complete` to true, invent a partial scope, substitute a checkout or install anything. A qualifying collector report establishing complete scope, omissions and base fetchability is needed before proceeding.

**Report:** No assessment was submitted; required coverage and local-review readiness are blocked.

### 3. `bad-digest` — result integrity blocked

Reject the artifact: advertised digest starts `7d7ca66f…`, while the checker calculates `6d7ca66f…`.

Do not interpret the apparent empty findings as a review outcome. Matching operation IDs, lengths and offsets do not repair a digest mismatch.

### 4. `bad-byte-count` — result integrity blocked

Reject the artifact: **149 bytes advertised versus 148 measured**.

A correct digest does not override inconsistent artifact metadata. No verified inventory or coverage conclusion is available.

### 5. `wrong-operation` — result association blocked

Reject both pages: they name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`.

Do not adopt or poll the other operation. Internally valid bytes do not establish that its result belongs to this submission.

### 6. `overlapping-pages` — page sequence blocked

Reject the collection: after the first 90-byte chunk, the second page must start at **90**, not **0**.

Do not silently correct the offset or accept the concatenation merely because its digest and length pass.

## One collection recovery for cases 3–6

For each independent invalid-result case, propose **one complete recollection** from the retained operation, beginning without a cursor:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Follow that recovery response’s returned cursors once each until null, keeping `extended` omitted. Use only the recovery’s pages—do not mix collections—and repeat every integrity and association check.

- **If recovery succeeds:** assess the verified artifact actually returned; apply the eligible conclusion only if its inventory and coverage support it.
- **If recovery remains invalid or unavailable:** stop with **Review blocked**, preserve operation `41c730de-840d-4b87-a95e-165b8b94f56a` and the precise failure, and report inventory, coverage and readiness as unverified.

Recovery collects the existing assessment. It does not authorize another review submission, finding-status writes or code changes.

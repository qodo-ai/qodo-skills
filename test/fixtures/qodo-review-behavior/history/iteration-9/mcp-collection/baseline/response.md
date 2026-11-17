## Proposed submission and collection

Use the authenticated MCP connection; no CLI, installation or separate identity check is needed. Omit depth to select auto.

When admission was uncertain, the permitted recovery was to replay **the same request ID and exact retained parameters**:

```text
start-pre-pr-review({
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
})
```

There is no separate `idempotency_key`. Do not recollect or modify the snapshot during uncertain-admission recovery.

**The supplied receipt already establishes acceptance**, so do not replay the start now. While it remains working, wait the advertised two seconds between calls:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Acceptance is not a completed review. Once terminal/completed with a result available, collect:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "extended": true
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two",
  "extended": true
})
```

Check `isError` on every response. Keep `extended` unchanged, follow returned cursors, and verify matching operation IDs and consistent artifact metadata. Join the chunks in byte-offset order; verify the complete byte count and digest **before parsing or assessing the JSON**. These are ordinary lifecycle calls, not MCP Tasks.

## 1. `eligible`

The tested collector satisfies the scope, exclusions, enumeration and fetchable-base gates.

The two pages cover offsets 0–89 and 90–147, terminate with a null cursor, and pass the supplied integrity check: 148 ASCII bytes, two chunks, and SHA-256:

```text
6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c
```

The verified artifact reports:

- Complete finding inventory and assessed coverage.
- No introduced or earlier still-open findings.
- No resolved or dismissed findings.

**Qodo’s assessment is complete for the submitted full local snapshot. With focused tests passed and no outstanding reported findings, that snapshot is ready locally on the supplied evidence.**

No live service was tested. This does not establish CI, approval, hosted PR review, release or deployment readiness. Reviewer consumption of the submitted context and checkpoint persistence/reusability are not evidenced by this artifact.

## 2. `incomplete-collector`

**Review blocked before submission.** Do not call `start-pre-pr-review`.

Enumeration stopped prematurely, included paths are unknown, and base fetchability is unverified. Consequently, neither an assessment nor complete coverage of the requested local change can be claimed.

Proceed only after a tested collector establishes the intended complete scope, reports omissions and verifies the exact base is fetchable. Do not substitute an ad hoc diff, another checkout or an unauthorized installation.

## 3. `bad-digest`

**Review result blocked by an integrity failure.** The advertised digest starts with `7d7c…`; the checker calculates `6d7c…`. Successful MCP envelopes and a completed operation do not make those bytes trustworthy.

Do not interpret the apparent empty findings or claim assessed coverage or local readiness from this artifact.

Use at most one collection-only recovery: re-fetch the entire artifact from the retained operation, starting without a cursor and following newly returned cursors, with `extended: true` throughout. Respect any returned retry delay; otherwise use 15 seconds. Recheck all metadata, offsets, length, digest and snapshot association.

If recovery validates, assess that recovered artifact. Otherwise stop and retain the operation ID and integrity diagnostic. **No new review submission.**

## 4. `bad-byte-count`

**Review result blocked by an integrity failure.** The advertised length is 149 bytes, but the joined artifact measures 148. A matching digest does not override the failed length check.

Do not parse the artifact for conclusions, silently correct its metadata or report zero findings as a valid assessment.

The same single collection-only recovery described above is available using the existing operation. If the recovered artifact validates completely, assess it; otherwise report review blocked and preserve the recovery handle. **No new review submission.**

**Only `eligible` supports local readiness.** The incomplete collector blocks submission; the other four cases block a trustworthy result. All calls below are proposals only.

## Submission identity and collection

For the eligible collector, the permitted uncertain-admission retry must repeat this exact request:

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

Depth remains omitted for auto. There is no separate `idempotency_key`, new snapshot, or changed context.

The subsequent receipt establishes an accepted, **pending** operation—not a completed assessment. Once that receipt exists, do not repeat the start call. Poll the retained operation at its advertised two-second interval, within retention:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` before interpreting every response. Once completed/terminal with a result available, collect:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "extended": false
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two",
  "extended": false
})
```

Follow returned cursors without changing `extended`. Before interpreting the JSON, verify operation identity, consistent metadata, complete chunk enumeration, contiguous byte offsets, joined byte count, and digest. These are short lifecycle calls, not MCP Tasks. No CLI setup or installation is needed.

## Independent outcomes

### 1. `eligible`

Both pages belong to the retained operation. Their offsets are contiguous at 0 and 90; two chunks supply 148 bytes, terminate without another cursor, and pass the advertised SHA-256 check. The snapshot association also matches the submission.

The verified artifact establishes:

- Complete finding inventory and assessed coverage.
- No findings, including no introduced or still-open obligations.
- No resolved or dismissed findings.

**Ready locally for the retained snapshot:** Qodo’s completed assessment reports no findings, and the supplied facts establish that focused tests passed. No live service was tested.

This does **not** establish CI success, approval, hosted PR review/handoff, release, or deployment readiness. Context was submitted, but reviewer consumption and reusable checkpoint persistence are not evidenced by this artifact.

### 2. `incomplete-collector`

**Review blocked before submission.** Do not call `start-pre-pr-review`, including its uncertain-admission retry.

Enumeration is incomplete, included paths are unknown, and base fetchability is unverified. The collector therefore cannot establish coverage of the complete requested local change. No assessment or local-readiness claim is justified.

Proceeding requires an authorized collector that establishes complete intended scope, reports omissions, applies the required exclusions, and verifies the exact base is fetchable. Do not substitute another checkout, an ad hoc diff, or an installation.

### 3. `bad-digest`

**Review blocked: artifact integrity failed.** The advertised digest begins `7d7ca66f…`, while the checker calculates `6d7ca66f…`.

Do not interpret the apparent empty finding inventory or report complete assessed coverage. A completed operation is not enough when its artifact fails verification.

One permitted collection recovery may re-fetch the retained operation’s complete artifact. If verification still fails, stop without a new submission.

### 4. `bad-byte-count`

**Review blocked: artifact length failed verification.** The pages advertise 149 bytes; the checker measures 148.

A matching digest does not waive the byte-count requirement. Do not interpret findings or claim readiness. Use at most one permitted complete recollection of the retained operation; stop if the mismatch persists.

### 5. `wrong-operation`

**Review blocked: the artifact is not bound to this submission.** Both pages identify `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the accepted operation.

Internal digest and length consistency do not establish relevance. Do not switch to that other operation, relabel its pages, or use its findings.

One permitted recovery must request the original operation, `41c730de-840d-4b87-a95e-165b8b94f56a`. Without a correctly associated result, assessment, coverage, and readiness remain unverified.

### 6. `overlapping-pages`

**Review blocked: page continuity failed.** After the first 90-byte chunk, the next offset must be 90; the supplied second page instead reports 0.

A valid concatenated digest and length do not repair contradictory offsets. Do not silently correct the offset, reorder pages, or interpret their findings.

Use at most one permitted complete recollection of the original operation. If continuity remains invalid, stop.

## Recovery boundary

For each invalid-result continuation independently, the single collection recovery starts again with the first result call above and follows its returned cursors, keeping `extended: false` throughout. Revalidate the entire artifact before interpreting it.

If recovery succeeds, report only what the verified result supports. If it fails, retain the original operation ID as the recovery handle and report **Review blocked**. No new review submission, finding-status change, code edit, or broader readiness claim is authorized.

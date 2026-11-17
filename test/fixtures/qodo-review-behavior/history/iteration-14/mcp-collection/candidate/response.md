**`eligible` supports local handoff readiness. The other continuations are blocked unless collection is corrected or a permitted recovery returns fully verified results.** These are proposals only; nothing is executed or changed.

## Submission and collection

Use the authenticated MCP connection directly—no CLI probes, login, installation or MCP Tasks.

For the initially lost start response, the permitted replay preserves the logical request ID and **every original argument**:

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

Depth remains omitted for **auto**. Do not add an `idempotency_key`, change the request ID or recollect a different snapshot.

**The supplied successful working receipt already resolves admission uncertainty. Do not replay the start again now.** Retain operation `41c730de-840d-4b87-a95e-165b8b94f56a` and propose:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Poll at the advertised two-second interval while working. Check `isError` and the operation identity on every receipt. Acceptance and `working` status do not establish assessment completion.

After completed/terminal status with a result available:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two"
})
```

Keep `extended` omitted throughout. Follow returned cursors once until null. Before parsing, verify:

- Successful receipts naming the retained operation.
- Stable encoding, digest, total byte count and total chunk count.
- Exactly two chunks with contiguous offsets beginning at zero, without overlap, gaps or cursor cycles.
- Joined bytes matching the advertised length and SHA-256.
- Snapshot/scope association matching the retained submission.

## Independent continuations

### 1. `eligible` — Ready locally

The collector establishes complete intended worktree enumeration, applied safety exclusions, no omissions and a fetchable exact base.

The result passes verification: offsets `0` and `90`, two chunks totaling 148 ASCII bytes, and digest:

```text
6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c
```

The snapshot association also matches. The verified artifact reports complete finding inventory and assessment coverage, with no findings in any lifecycle bucket.

**Qodo’s completed assessment reports no new or earlier-open findings. With the supplied passing focused tests, the reviewed local snapshot is ready for handoff.** No additional assessment is justified merely to obtain another empty result.

Limitations remain separate: no live-service testing, hosted PR review, CI, approval, release or deployment evidence is supplied. The artifact also does not establish context consumption, checkpoint persistence or reusable coverage.

### 2. `incomplete-collector` — Review blocked before submission

Propose **no start call**. Enumeration stopped, included paths are unknown and base fetchability is unverified. This cannot cover the requested complete local change.

A corrected tested collector must establish complete intended enumeration, exclusions/omissions and fetchability of the exact base before submission. Do not silently narrow scope, mark collection complete, substitute an ad hoc diff, install tooling or use another checkout.

No completed assessment, complete coverage or local readiness can be reported.

### 3–6. Invalid results — Reject and preserve the accepted operation

| Continuation | Reason to reject |
|---|---|
| `bad-digest` | Advertised `7d7…` differs from the checker’s `6d7…`. Do not replace the advertised digest and accept the artifact. |
| `bad-byte-count` | Advertised 149 bytes differs from the measured 148. A matching digest does not cure incorrect length metadata. |
| `wrong-operation` | Both pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, with no binding to this submission. Internal integrity does not establish request identity. Do not adopt that operation. |
| `overlapping-pages` | The second offset is `0`, not `90`. Valid concatenated bytes do not cure overlapping pagination. Do not repair offsets or invent another ordering. |

For each independent invalid-result case, propose **at most one permitted collection recovery**: recollect the complete artifact from the first page using retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`, keep `extended` omitted, follow returned cursors and repeat every verification check.

Do not submit another review. If recovery passes, assess that verified result. If it fails or remains unverifiable, stop with **Review blocked**, preserving the operation handle and exact failure.

Until successful recovery, neither the apparent empty findings nor complete coverage claims are trustworthy. A terminal operation alone does not establish usable assessment evidence or handoff readiness.

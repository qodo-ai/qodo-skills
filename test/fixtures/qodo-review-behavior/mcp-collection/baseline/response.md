**Only `eligible` supports a completed local review.** The other continuations remain blocked unless a permitted collection recovery produces a fully verified artifact. These are proposed calls only.

## Submission and collection

The eligible collector satisfies the MCP requirements: the real worktree, complete intended scope, safety exclusions, omission report and fetchable exact base are established. No CLI probe, login, installation or substitute checkout is needed.

For the initially uncertain admission, replay only the original logical request:

```text
start-pre-pr-review({
  request_id: "mcp-cart-r1",
  params: {
    repo_full_name: "example/cart",
    repo_host: "github.com",
    base_sha: "1111111111111111111111111111111111111111",
    commit_sha: "2222222222222222222222222222222222222222",
    branch: "feature/cart-review",
    diff: "diff --git a/src/cart.ts b/src/cart.ts\n--- a/src/cart.ts\n+++ b/src/cart.ts\n@@ -1 +1 @@\n-export const valid = n => n === 1;\n+export const valid = n => n > 0;\n",
    session_context: {
      decisions: ["The user selected positive cart counts."],
      notes: "The mandatory caller rejects non-numeric input. Focused tests passed; no live service was tested.",
      recent_work: ["Changed the cart-count predicate; this round changes behavior."]
    },
    review_scope: {
      stream_id: "f1bcba4fd84bd7e271baea841b4e35e31958043c22e9c3ebc077d803f1ac8417",
      paths: [],
      excluded_files: [],
      skipped_files: [],
      allowed_sensitive_files: [],
      complete: true
    }
  }
})
```

Do not add `idempotency_key`, change the snapshot or omit context. Leave depth absent for **auto** effort.

**The supplied receipt already establishes acceptance, so do not replay start again now.** Poll the retained operation at its advertised two-second interval:

```text
get-managed-agent-operation({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and lifecycle fields. While it remains working, keep polling that operation—not a new submission. Once terminal/completed with a result available:

```text
get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a",
  extended: false
})

get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a",
  cursor: "page-two",
  extended: false
})
```

Keep `extended` unchanged. Before interpreting JSON, verify:

- Every page succeeds and names the retained operation.
- Encoding and artifact metadata agree across pages.
- There are exactly two chunks, with contiguous byte offsets `0` and `90`, without gaps or overlaps.
- Pagination ends with `next_cursor: null`.
- Joined ASCII bytes total `148` and match SHA-256  
  `6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c`.
- The result is associated with the retained submitted snapshot.

## Independent conclusions

| Continuation | Proposed action and honest conclusion |
|---|---|
| **1. `eligible`** | All supplied integrity and association checks pass. Parse the complete artifact: inventory and assessed coverage are complete; `findings`, `introduced`, `still_open`, `resolved` and `dismissed` are all empty. **Qodo returned a complete local assessment with no findings.** With the supplied passed focused tests, the reviewed snapshot is **ready locally** for the requested handoff. |
| **2. `incomplete-collector`** | **Stop before submission.** Enumeration is incomplete, included paths are unknown and base fetchability is unverified. MCP cannot safely establish coverage of the complete local change. Report **review blocked**; a qualifying collector report is required before proceeding. Do not invent a collection mode, substitute a checkout or install anything. |
| **3. `bad-digest`** | Reject the artifact: the advertised digest differs from the measured digest. Do not interpret its apparent empty inventory. Report **review blocked: artifact integrity failed** pending permitted recollection. |
| **4. `bad-byte-count`** | Reject the artifact: advertised `149` bytes versus measured `148`. A matching digest does not excuse the independent length failure. Report **review blocked: artifact length mismatch**. |
| **5. `wrong-operation`** | Reject the artifact: it names `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the retained operation. Valid bytes do not establish submission identity. Do not adopt or follow the foreign operation. Report **review blocked: result association unverified**. |
| **6. `overlapping-pages`** | Reject the artifact: the second page reports offset `0`, overlapping the first instead of continuing at `90`. Matching concatenated bytes do not validate page structure. Do not repair offsets or invent ordering. Report **review blocked: inconsistent pagination**. |

For cases 3–6, successful input collection remains established, but the **assessment inventory and coverage cannot be verified**. A completed operation receipt alone does not establish readiness.

## Bounded collection recovery

For each invalid-result continuation, use at most one permitted **collection-only** recovery against `41c730de-840d-4b87-a95e-165b8b94f56a`: recheck its receipt and retrieve a fresh, complete page chain from the beginning, retaining `extended: false`. Do not mix rejected and replacement chunks. Reapply every identity, pagination, digest, length and snapshot check.

Honor returned retry restrictions and delays. A status transport failure permits only the bounded collection retry—after its returned delay, or 15 seconds if none is supplied. No new review submission is authorized. If recovery fails or remains invalid, stop with the original operation ID and the precise blocker.

Even in `eligible`, live-service behavior, CI, approval, hosted finding handoff, checkpoint persistence, release and deployment are not established. Reviewer-context consumption and execution details are also unreported; do not infer them from the submitted context or empty findings.

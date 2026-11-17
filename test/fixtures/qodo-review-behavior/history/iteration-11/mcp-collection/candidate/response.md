**Proposals only; no calls were executed.** Only `eligible` supports a completed local-review claim. The other continuations are **Review blocked** on the supplied evidence.

## Submission recovery and collection

Use the authenticated MCP connection directly—no CLI preflight, installation or substitute checkout.

When the first start response was lost, the permitted retry was the **same logical request with exactly the retained arguments**:

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

Depth remains omitted for **auto**. There is no separate `idempotency_key`. Do not recollect a different snapshot or replace the request ID.

**The working receipt is now known, so do not call start again.** Retain operation `41c730de-840d-4b87-a95e-165b8b94f56a` and poll at the advertised two-second interval:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and the operation identity on every receipt. Working/nonterminal status is not an assessment.

Once completed, terminal and result-available, propose:

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

Keep `extended` unchanged. Follow each cursor once through null. Before parsing, require:

- Successful receipts identifying the retained operation.
- Stable encoding, digest, byte count and chunk count.
- Exactly two contiguous chunks: offsets **0**, then **90**, without gaps, overlaps or cursor cycles.
- Verified joined length and digest.
- Snapshot/scope association matching the retained submission.

These are short lifecycle calls, not MCP Tasks.

## Independent continuations

### 1. `eligible` — Ready locally

The tested collector establishes complete enumeration, required exclusions, no omissions and a fetchable exact base. The artifact passes operation identity, pagination, digest, **148-byte** length and snapshot-association checks.

Qodo reports complete coverage and a complete finding inventory, with no introduced, still-open, resolved or dismissed findings. With the supplied focused-test pass, **the retained submitted local snapshot is ready locally for handoff**.

This conclusion covers the collected working snapshot, not merely its HEAD SHA. Live-service behavior was not tested. No hosted PR review, CI, approval, merge, release or deployment readiness is established. Context consumption and checkpoint persistence/reusability have no supplied receipts and remain unverified.

### 2. `incomplete-collector` — Review blocked before submission

**Do not submit.** Enumeration stopped early, included paths are unknown and base fetchability is unverified. The collector cannot establish the requested complete local scope.

Report no completed assessment or verified review coverage. A suitable tested collector must establish complete scope, exclusions/omissions and fetchable base before submission. Do not substitute an ad hoc diff, narrow the requested scope silently, install anything or use another checkout.

### 3. `bad-digest` — Reject the artifact

The advertised digest begins `7d7ca66f`, but the checker calculates the eligible digest beginning `6d7ca66f`.

The integrity check fails. Do not interpret the apparent empty inventory or claim verified coverage/readiness.

### 4. `bad-byte-count` — Reject the artifact

Both pages advertise **149 bytes**, but the joined artifact measures **148 bytes**. A matching digest does not override the length mismatch.

The assessment cannot be accepted as verified; coverage and readiness remain unestablished.

### 5. `wrong-operation` — Reject the association

Both pages identify `92a3119c-a271-4e46-9e39-cd38d174feb7`, not retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`.

Internally valid bytes do not establish that this artifact reviews the submitted cart snapshot. Do not adopt or poll the unrelated operation. Coverage/readiness for the retained request remain unverified.

### 6. `overlapping-pages` — Reject the pagination

The second page starts at **0**, where **90** is required. This violates contiguous pagination even though concatenated bytes pass the digest and length checks.

Do not repair the offset, reorder pages or accept the parsed inventory. Verified assessment and coverage remain unavailable.

## Bounded recovery for cases 3–6

Use at most **one collection-only recovery** against retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`: recheck its receipt, then retrieve the artifact again from the first page using the same collection arguments and validate every page afresh.

Honor returned delays; a status-transport retry uses the returned delay, or **15 seconds** if none is supplied. Do not create another retry allowance for each symptom.

No recovery result is supplied here, so cases 3–6 remain **Review blocked**, not “no findings” or ready. If the single recovery fully verifies the artifact, reassess that verified result; otherwise stop and preserve the operation ID and exact failure. **No new review submission or finding-status write is authorized.**

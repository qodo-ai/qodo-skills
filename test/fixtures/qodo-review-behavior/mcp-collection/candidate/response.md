Only **`eligible`** supports a completed local assessment. The other continuations are **Review blocked**. All calls below are proposals only.

## Submission identity and collection

The eligible collector satisfies the MCP requirements: the real worktree was completely enumerated, safety exclusions were applied, no omissions were reported, and the exact base is fetchable.

After the lost start response, the permitted replay is:

```text
start-pre-pr-review({
  request_id: "mcp-cart-r1",
  params: retainedParams
})
```

Here, `retainedParams` means the **exact supplied object**, unchanged—including the diff, base, HEAD, branch, context and verified stream ID. Omit depth for auto. Do not add an `idempotency_key`, recollect the worktree or alter the request.

Once the supplied working receipt establishes operation `41c730de-840d-4b87-a95e-165b8b94f56a`, **do not call start again**.

Wait the advertised two seconds between status polls:

```text
get-managed-agent-operation({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and the operation ID on every receipt. Continue within retention until completion is terminal and a result is available. A working receipt is not a completed assessment.

Then collect:

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

Keep `extended` unchanged. Before parsing, verify:

- Every receipt has `isError: false` and the retained operation ID.
- Encoding, digest, total bytes and total chunks remain identical across pages.
- Cursors terminate without cycles; offsets are contiguous from zero.
- Collected chunk count, byte count and SHA-256 match the advertised values.
- Snapshot and scope association match the retained submission.

These are short lifecycle calls, not MCP Tasks.

## Independent continuations

### 1. `eligible` — Ready locally for the reviewed snapshot

Both pages belong to the retained operation. Their offsets are **0 and 90**, with **two chunks totaling 148 ASCII bytes**. The verified digest matches:

```text
6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c
```

After validation, the artifact establishes:

- Complete finding inventory and assessed coverage.
- No introduced or still-open findings.
- Empty resolved and dismissed buckets.
- Matching submitted snapshot and scope.

**Qodo’s completed local assessment reports no findings, with complete coverage of the submitted change; the supplied focused tests passed. This supports local handoff of that reviewed snapshot.**

No live service was tested. Context was supplied, but reviewer consumption is not evidenced. Effective effort, checkpoint persistence/reuse and local-to-PR finding handoff are not established. CI, approval, release and deployment remain separate, unevidenced gates.

### 2. `incomplete-collector` — Review blocked before submission

Do not submit. Enumeration stopped early, included paths are unknown, and base fetchability was not verified.

MCP cannot safely establish coverage of the complete requested local change. Do not substitute an ad hoc diff, another checkout or an installation. Proceeding would require an eligible collector report for the authorized worktree and scope.

### 3. `bad-digest` — Review blocked

Reject the artifact before interpreting findings. The advertised digest starts with `7d7ca66f`; the checker calculates the supplied `6d7ca66f…` digest.

Successful receipts and otherwise consistent pages do not overcome failed integrity verification.

### 4. `bad-byte-count` — Review blocked

Reject the artifact: **149 bytes advertised, 148 bytes collected**. A matching digest does not excuse inconsistent length metadata.

No verified inventory or coverage conclusion is available.

### 5. `wrong-operation` — Review blocked

Reject both pages. They identify:

```text
92a3119c-a271-4e46-9e39-cd38d174feb7
```

That is not the accepted operation. Internally valid bytes do not establish association with this submission. Do not adopt the other operation or interpret its findings as this review’s result.

### 6. `overlapping-pages` — Review blocked

Reject the artifact. After the first 90-byte chunk, the second offset must be **90**, not **0**.

A valid concatenated digest cannot repair overlapping page metadata. Do not silently correct offsets, reorder pages or accept the reconstructed JSON.

## Collection recovery

For cases 3–6, retain the original operation as the recovery handle:

```text
41c730de-840d-4b87-a95e-165b8b94f56a
```

If the Skill’s collection-retry gate permits the optional recovery, make **at most one** fresh collection attempt against that operation, starting without a cursor, following its returned cursors and keeping `extended: false`. Revalidate the entire artifact; do not mix pages from different attempts.

No successful recovery is supplied here, so these cases remain **Review blocked**. If recovery is not permitted or fails validation, stop. **No new review submission, finding changes or readiness claim is authorized.**

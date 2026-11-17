Proposals only; no service calls, commands or changes have been made.

## Submission identity and collection

The eligible collector satisfies the MCP collection requirements. Use the authenticated MCP connection without CLI preflight or installation. Leave depth omitted for **auto**.

For the lost start response, the permitted recovery is:

```text
start-pre-pr-review({
  request_id: "mcp-cart-r1",
  params: retainedParams
})
```

Here, `retainedParams` means the **exact supplied JSON object**, preserving its base, snapshot, diff, context and scope. Do not recollect the worktree or add an unsupported `idempotency_key`.

The supplied receipt already confirms acceptance, so **do not repeat that start now**. After the advertised two-second interval, propose:

```text
get-managed-agent-operation({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and continue polling that operation at its returned interval while pending. Once terminal/completed with a result available:

```text
get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a",
  extended: true
})

get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a",
  cursor: "page-two",
  extended: true
})
```

Keep `extended` unchanged. Before interpreting the assembled JSON, verify successful envelopes, the retained operation ID, consistent artifact metadata, two chunks, contiguous offsets, terminal cursor, byte count and digest. Then verify association with the retained submission.

## Independent continuations

### 1. `eligible` — ready locally for the supplied snapshot

All supplied integrity and snapshot-association checks pass: offsets 0 and 90, 148 joined ASCII bytes, two chunks and the advertised SHA-256.

Qodo’s completed assessment reports:

- Complete finding inventory and assessed coverage.
- No findings: `introduced`, `still_open`, `resolved` and `dismissed` are all empty.
- Focused tests passed; no live service was tested.

This supports **local readiness for that reviewed snapshot**, not newer changes. Context-consumption receipts, checkpoint persistence/reuse and hosted-review status are not supplied. CI, approval, release and deployment readiness remain unestablished.

### 2. `incomplete-collector` — review blocked before submission

Do **not** call `start-pre-pr-review`.

Enumeration is incomplete, included paths are unknown and base fetchability is unverified. The collector therefore cannot establish coverage of the requested complete local change.

No completed assessment or local readiness can be reported. A qualifying collector must establish the intended scope, exclusions/omissions and fetchable base before submission. Do not narrow the scope silently, substitute a checkout or install anything.

### 3–6. Invalid result collections — review blocked

| Continuation | Validation failure | Honest conclusion |
|---|---|---|
| `bad-digest` | Advertised digest starts `7d7c…`; measured digest starts `6d7c…`. | Artifact integrity failed. |
| `bad-byte-count` | Advertised 149 bytes; measured 148. | Artifact length validation failed, despite the matching digest. |
| `wrong-operation` | Both pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the retained operation. | Internally valid bytes do not establish association with this submission. |
| `overlapping-pages` | Second offset is 0 rather than 90. | Pagination is inconsistent, despite passing concatenated-byte checks. |

In each case, do not interpret the apparent empty findings as a valid assessment, certify coverage or report readiness. Do not repair offsets, replace advertised metadata or relabel another operation locally.

**One collection recovery per independent continuation is permitted:** retain operation `41c730de-840d-4b87-a95e-165b8b94f56a`, respect any returned retry delay, and re-fetch its complete artifact from the first page with the same `extended` setting. Validate the recovered page set independently; do not mix it with the invalid set.

If recovery fails or remains invalid, stop with **Review blocked**, preserving the operation ID and exact validation failure. No new review submission is authorized.

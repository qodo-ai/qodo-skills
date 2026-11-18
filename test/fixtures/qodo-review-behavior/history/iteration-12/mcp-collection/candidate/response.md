**Proposals only; no calls, commands, edits or status writes are executed.**

## Common MCP handling

Use the authenticated MCP connection and supplied schemas. Skip CLI preflight and installation. Preserve the exact supplied `params`, including context, base, diff and scope. Omit depth to retain **auto** effort.

While admission was uncertain, the permitted recovery was:

```text
start-pre-pr-review({
  request_id: "mcp-cart-r1",
  params: retainedParams
})
```

Here, `retainedParams` means the supplied object **unchanged**, not a newly collected snapshot. `request_id` is the logical retry key; do not add `idempotency_key`.

The subsequent receipt already establishes acceptance as operation `41c730de-840d-4b87-a95e-165b8b94f56a`. **Do not start it again.**

While it remains working, poll at the advertised two-second interval:

```text
get-managed-agent-operation({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and operation identity on each receipt. Once completed, terminal and result-available, propose:

```text
get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a"
})

get-managed-agent-result({
  operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a",
  cursor: "page-two"
})
```

Keep `extended` omitted consistently. These are short lifecycle calls, not MCP Tasks.

Before parsing, verify:

- Every receipt belongs to the retained operation.
- Encoding, digest, total bytes and chunk count remain stable.
- Cursors terminate without repetition.
- Offsets are contiguous from zero: here, `0`, then `90`.
- Exactly two chunks contain 148 joined ASCII bytes with the advertised SHA-256.
- Snapshot and scope association match the retained submission.

## Independent continuations

### 1. `eligible` — ready locally for the supplied snapshot

The tested collector establishes complete input enumeration, safety exclusions, no omissions and a fetchable exact base. The completed result passes identity, pagination, digest, byte-count and snapshot-association checks.

Qodo reports:

- Complete finding inventory and assessed coverage.
- No introduced or still-open findings.
- No resolved or dismissed findings.

Focused tests passed. On the supplied evidence, the reviewed local snapshot is **ready locally for handoff**; another assessment is unnecessary.

Live-service behavior was not tested. CI, approval, release and deployment remain unverified. The artifact also does not establish reviewer consumption of the session context, checkpoint persistence, reusable coverage or hosted PR handoff.

### 2. `incomplete-collector` — review blocked before submission

Do **not** submit or replay a start request in this continuation.

Enumeration stopped early, included paths are unknown and base fetchability is unverified. The prepared input therefore cannot establish coverage of the requested complete local change.

Report **review blocked**, with no completed assessment or readiness claim. Proceeding requires a tested collector that establishes the intended scope, exclusions, omissions and fetchable base. Do not substitute an ad hoc diff, another checkout or an installation.

### 3. `bad-digest` — reject the artifact

The advertised digest begins `7d7…`, but the checker calculates `6d7…`. Matching operation IDs and byte counts do not repair that integrity failure.

Do not interpret the apparent empty findings. Use at most the permitted collection recovery below; otherwise report **review blocked**.

### 4. `bad-byte-count` — reject the artifact

The envelope advertises 149 bytes, but the joined artifact contains 148. A matching digest alone is insufficient.

Do not silently correct the metadata or claim coverage. Use at most the permitted collection recovery; otherwise report **review blocked**.

### 5. `wrong-operation` — reject the association

The pages identify `92a3119c-a271-4e46-9e39-cd38d174feb7`, not the accepted operation. Internally valid bytes do not bind that other operation to this submission.

Do not adopt or poll the other operation. Recover collection only through `41c730de-840d-4b87-a95e-165b8b94f56a`; otherwise report **review blocked**.

### 6. `overlapping-pages` — reject the pagination

The second offset is `0`, but must be `90`. Passing the joined digest and length does not establish valid pagination.

Do not rewrite offsets, reorder pages or infer a correction. Use at most the permitted collection recovery; otherwise report **review blocked**.

## Bounded recovery for invalid results

For each independent invalid-result continuation, propose **one collection-only recovery**: fetch again from the first page of the retained operation, follow its returned cursors once and repeat every validation above. Keep `extended` unchanged.

Do not submit another review or rotate the request ID. If recovery supplies a fully verified result, assess that result. If it fails again, stop and retain the operation ID and precise validation failure. An accepted or completed operation alone cannot establish trustworthy assessment coverage or local readiness.

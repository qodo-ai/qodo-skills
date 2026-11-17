All calls below are proposals only. No services, commands, installations, edits or finding-status writes are needed.

## Proposed MCP sequence

### Recovering the lost start response

The permitted recovery is an exact replay of `start-pre-pr-review` with the retained request:

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

Do not add `idempotency_key`, change the snapshot or regenerate context. Omitted depth selects auto.

**The supplied subsequent receipt already resolves admission.** From that point, retain operation `41c730de-840d-4b87-a95e-165b8b94f56a` and collect it; do not replay the start again.

### Poll and collect the accepted operation

At the advertised two-second interval, within retention:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` and the returned operation identity on every receipt. Once completed, terminal and result-available:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})

get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two"
})
```

Keep `extended` omitted throughout. These are short lifecycle calls, not MCP Tasks.

Before parsing, require:

- Successful receipts naming the retained operation.
- Stable encoding, digest, total bytes and total chunks.
- Two chunks, contiguous offsets `0` then `90`, and cursor termination without cycles.
- Verified joined byte count and SHA-256.
- Snapshot/scope association matching the retained submission.

## Independent outcomes

### 1. `eligible` — ready locally

The tested collector establishes complete working-snapshot enumeration, safety exclusions, no omissions and a fetchable exact base. The two pages also pass identity, pagination, digest and 148-byte verification; their snapshot association matches.

Qodo’s completed assessment has:

- **New findings:** none.
- **Earlier open findings:** none.
- **Resolved/dismissed findings:** none.
- **Finding inventory and assessed coverage:** both complete.

With the supplied passing focused tests, this supports **ready locally for the reviewed working snapshot**. No live service was tested. This does not establish committed-PR or hosted-review coverage, CI success, approval, release or deployment.

The artifact supplies no reviewer comment, context-delivery receipt or checkpoint-persistence evidence. Reviewer consumption and reusable stored coverage therefore remain unverified.

### 2. `incomplete-collector` — blocked before submission

Do not call `start-pre-pr-review`. Enumeration stopped early, included paths are unknown and base fetchability was not checked. The requested complete local scope cannot be established.

Report **review blocked**, with no completed assessment or verified coverage. Proceeding requires suitable collector evidence establishing complete enumeration, exclusions/omissions and base fetchability. Do not substitute a checkout, ad hoc diff or installation.

### 3. `bad-digest` — reject the artifact

The advertised digest begins `7d7c…`, while the checker calculates `6d7c…`. Artifact integrity failed.

Do not interpret the embedded empty findings as a verified result. Report **review blocked: result integrity failure**, despite the operation’s reported completion.

### 4. `bad-byte-count` — reject the artifact

The advertised size is **149 bytes**, but the joined chunks measure **148 bytes**. A correct digest does not waive the byte-count requirement.

Report **review blocked: result length mismatch**. Findings, assessed coverage and readiness cannot be certified from this artifact.

### 5. `wrong-operation` — reject the association

Both pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`.

Valid bytes do not prove that this result belongs to the submitted cart snapshot. Do not adopt or poll the foreign operation. Report **review blocked: operation association mismatch**.

### 6. `overlapping-pages` — reject the pagination

The second chunk must start at byte **90**, not **0**. Matching concatenated bytes and digest do not repair overlapping page metadata.

Do not silently correct offsets or invent another ordering. Report **review blocked: noncontiguous result pages**.

## Recovery boundary

For cases 3–6, retain the original request, accepted operation and rejected receipts. **No automatic collection retry is permitted by the supplied Skill gates:** these are integrity or identity failures, not status transport failures.

The Skill permits one collection retry for a status transport failure after its returned delay, or 15 seconds when none is supplied. That condition is absent here. The conditional recovery allowance does not create an additional gate, and no new review submission is authorized.

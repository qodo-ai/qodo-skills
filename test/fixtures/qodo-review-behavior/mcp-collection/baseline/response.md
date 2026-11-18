Only **`eligible`** supports a completed local review. The incomplete collector blocks submission; the four invalid-result cases block interpretation and readiness.

All calls below are proposals only. Nothing is executed, installed, saved, edited or dismissed.

## Submission identity and collection

Use the authenticated MCP connection without CLI preflight. Omit depth to select **auto**.

For the initially lost start response, the permitted recovery is the same logical request with **exactly the retained arguments**:

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

Do not add `idempotency_key`, recollect a different snapshot or change context.

The supplied working receipt already establishes acceptance. **Do not replay start again from that point.** For accepted continuations, wait the advertised two seconds, then poll:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Continue polling that operation at its returned interval within retention. Working status is not an assessment.

Once completed/terminal with a result available, collect sequentially:

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "extended": false
})
```

```text
get-managed-agent-result({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a",
  "cursor": "page-two",
  "extended": false
})
```

Check `isError` before using each response. Before interpreting the artifact, verify:

- Every page belongs to the retained operation.
- Encoding and artifact metadata agree across pages.
- Cursor traversal ends normally after exactly two chunks.
- Offsets are contiguous: first `0`, second `90`; no overlaps or gaps.
- Joined bytes total `148` and match the advertised SHA-256.
- The resulting assessment matches the retained submitted snapshot.

These are short lifecycle calls, not MCP Tasks.

## Independent continuations

### 1. `eligible`

The tested collector satisfies collection requirements: correct real worktree, complete tracked and reviewable-untracked enumeration, established exclusions, no omissions and a fetchable exact base.

Both pages pass association, pagination and integrity checks. Only then interpret the joined artifact:

```json
{
  "findings": [],
  "finding_state": {
    "complete": true,
    "introduced": [],
    "still_open": [],
    "resolved": [],
    "dismissed": []
  },
  "meta": {
    "coverage": {
      "complete": true
    }
  }
}
```

**Ready locally for the exact collected snapshot, on the supplied evidence:** Qodo’s assessment completed with complete coverage and inventory, no new or earlier-open findings, and focused tests passed. No resolved or dismissed findings are reported.

Live-service behavior remains untested. Context consumption, checkpoint persistence/reusability and hosted PR handoff are not established by this artifact. No CI, approval, merge, release or deployment clearance can be claimed.

### 2. `incomplete-collector`

**Review blocked before submission.** Do not make the start call above.

Enumeration stopped, included paths are unknown and base fetchability is unverified. The requested complete-local-change scope therefore cannot be established.

A suitable collector must finish enumeration, report omissions and verify base fetchability before submission. Do not replace this with an ad hoc diff, narrower scope, substitute checkout or installation. No completed assessment, complete coverage or local readiness can be reported.

### 3–6. Invalid collected results

| Continuation | Failure | Honest conclusion |
|---|---|---|
| `bad-digest` | Advertised digest starts `7d7…`; verified bytes hash to `6d7…`. | Integrity verification failed. Do not interpret the apparent empty inventory or claim coverage/readiness. |
| `bad-byte-count` | Advertised length is `149`; actual length is `148`. | Integrity verification failed despite the matching digest. Do not silently correct the metadata. |
| `wrong-operation` | Pages name `92a3119c-a271-4e46-9e39-cd38d174feb7`, not retained operation `41c730de-840d-4b87-a95e-165b8b94f56a`. | Internally valid bytes do not establish assessment of this submission. Do not adopt or follow the other operation. |
| `overlapping-pages` | Second offset is `0`, not required offset `90`. | Pagination is inconsistent despite the joined-byte checks passing. Do not repair offsets or invent a page order. |

For each invalid-result continuation, use **at most one permitted collection recovery**, retrieving the retained operation’s artifact again from its first page and following its returned cursors with `extended: false` unchanged. Respect any returned recovery delay; otherwise use the Skill’s 15-second collection-retry fallback.

Revalidate the entire artifact, not just the failed check. This is one collection recovery—not another allowance per page or symptom—and **never a new review submission**.

If recovery yields a fully verified, matching artifact, assess that recovered result. If it fails again, stop with **Review blocked** and preserve the original operation ID and precise collection failure. Backend completion alone cannot establish a usable assessment, complete coverage or readiness.

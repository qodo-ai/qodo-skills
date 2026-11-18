All calls below are proposals only. I would use the authenticated MCP connection without CLI probes, installation, shell commands or finding-status writes.

## Submission identity and collection

The permitted retry after the lost start response must preserve this exact request:

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

Depth remains omitted for **auto**. There is no separate `idempotency_key`.

The supplied subsequent receipt already confirms acceptance, so **do not repeat the start call now**. While it is working, wait the advertised two seconds between polls:

```text
get-managed-agent-operation({
  "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"
})
```

Check `isError` before interpreting each receipt. Working status is not a completed assessment. Once terminal completion and result availability are confirmed, collect:

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

Keep `extended` unchanged. Collect every page and verify operation identity, consistent metadata, contiguous byte offsets, chunk count, final cursor, total bytes and digest **before parsing or interpreting the joined artifact**. These are short lifecycle calls, not MCP Tasks.

## 1. Eligible

The collector qualifies: it covered the requested real worktree, included tracked and reviewable untracked changes, applied safety exclusions, reported no omissions and verified base fetchability.

The supplied result passes integrity verification:

- Two chunks, at offsets 0 and 90, ending at 148 bytes.
- Final cursor is null.
- Joined length is 148 bytes.
- Advertised and calculated SHA-256 both equal  
  `6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c`.
- Snapshot association matches the retained submission.

After verification, the artifact establishes a complete finding inventory and complete assessed coverage. Findings, introduced, still-open, resolved and dismissed inventories are all empty.

**Outcome: ready locally for the submitted snapshot.** Qodo’s completed assessment reports no findings or outstanding finding backlog, and the supplied focused tests passed.

This does not establish live-service validation, CI success, approval, hosted/PR review status, release or deployment readiness. Context was submitted, but reviewer consumption and checkpoint persistence are not evidenced by this artifact. Its missing analysis metadata also does not establish whether execution was full, incremental or reused.

## 2. Incomplete collector

**Outcome: review blocked before submission.**

Do not call `start-pre-pr-review`. Enumeration stopped early, included paths are unknown, and base fetchability is unverified. That cannot support the requested complete-local-change scope.

The prerequisite is a completed, tested collection with established included paths, omission reporting, safety exclusions and a verified fetchable base. Do not relabel this collection complete, replace it with an ad hoc diff, use a substitute checkout or install anything.

No assessment or complete coverage can honestly be reported.

## 3. Bad digest

**Outcome: result integrity blocked; no usable assessment conclusion.**

The advertised digest starts with `7d7c…`, but the checker calculates `6d7c…`. Successful transport and completed operation status do not make the artifact trustworthy. Do not interpret its apparent empty finding inventory.

Use at most the permitted **one collection-recovery attempt** against operation `41c730de-840d-4b87-a95e-165b8b94f56a`: re-fetch from the first page with `extended: false`, follow its returned cursor, and repeat all integrity checks. Honor any returned recovery delay; otherwise wait 15 seconds.

Only a successfully verified recovery could support the eligible-case conclusions. If recovery fails or remains corrupt, stop and preserve the operation ID and mismatch. No new review submission is authorized.

## 4. Bad byte count

**Outcome: result integrity blocked; no usable assessment conclusion.**

The advertised total is **149 bytes**, but the joined ASCII payload measures **148 bytes**. A matching digest does not excuse a failed byte-count check. Do not interpret the findings or claim complete assessment coverage.

Use the same single collection-recovery procedure against the retained operation, keeping `extended: false` throughout and verifying every page again. If the recovered artifact passes all checks, assess it then; otherwise stop with the discrepancy and operation ID preserved.

Do not create a replacement review or continue retrying to obtain a favorable result.

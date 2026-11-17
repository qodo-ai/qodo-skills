---
tags: [qodo-review, mcp, collection]
max_turns: 12
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

I have finished a small cart change and want the local review before handoff.
There is no trusted CLI. My authenticated MCP connection exposes the following
schemas. This is a synthetic exercise: show proposed calls and conclusions only.
Do not call a service, run a shell, install anything, change findings or save files.
Treat the supplied facts as complete; use the selected Skill and its references.

The declared start schema is `start-pre-pr-review({request_id, params})`.
Its `params` accepts `repo_full_name`, `repo_host`, `base_sha`, `diff`, `branch`,
`commit_sha`, `session_context` and `review_scope`. Depth is optional; omission
selects auto. There is no separate `idempotency_key` argument.
`get-managed-agent-operation({operation_id})` returns the operation receipt.
`get-managed-agent-result({operation_id, cursor?, extended?})` returns an artifact
page; keep `extended` unchanged between pages. These are short calls, not MCP Tasks.

An available, tested collector reports:
- It used the requested real worktree `/workspace/cart`, included tracked and
  reviewable untracked changes, applied the established security/binary/symlink/
  size exclusions, found no omitted files, and established complete enumeration.
- The exact comparison base `1111111111111111111111111111111111111111` is fetchable.
- HEAD is `2222222222222222222222222222222222222222`, branch `feature/cart-review`.
- The retained `params` are:

```json
{
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
```

The stream value is the verified SHA-256 of `JSON(["/workspace/cart"])`.
The retained logical request ID is `mcp-cart-r1`. The first start response was
lost, so admission was initially uncertain. A retry is permitted. The subsequent
receipt has `isError: false`, operation ID `41c730de-840d-4b87-a95e-165b8b94f56a`,
status `working`, `terminal: false`, `result_available: false`,
`poll_interval_seconds: 2` and an unexpired retention deadline.

Consider these independent continuations. Explain the proposed next actions and
what assessment, coverage or readiness can honestly be reported in each:

1. `eligible`: The collector report above is valid. Polling eventually reports
   completed/terminal with a result available. Both result calls have `isError:
   false`, `encoding: json-ascii`, the same operation ID, `sha256:
   6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c`,
   `total_bytes: 148`, and `total_chunks: 2`. The first page has
   `offset_bytes: 0`, `next_cursor: "page-two"` and this 90-byte chunk:
   `{"findings":[],"finding_state":{"complete":true,"introduced":[],"still_open":[],"resolved"`
   The second has `offset_bytes: 90`, `next_cursor: null` and this 58-byte chunk:
   `:[],"dismissed":[]},"meta":{"coverage":{"complete":true}}}`
   A read-only integrity checker reports the joined ASCII bytes have the advertised
   digest and length. The resulting snapshot association matches the retained
   submission. No CI, approval, release or deployment evidence is supplied.
2. `incomplete-collector`: Before any submission, the collector instead reports
   `complete: false`: enumeration stopped at a limit, the included paths cannot
   be established, and base fetchability was not checked. The requested scope is
   still the complete local change; no substitute checkout or installation is authorized.
3. `bad-digest`: Submission was already accepted with the eligible collector.
   The pages are otherwise as in eligible, but both advertise digest
   `7d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c`.
   The checker still calculates `6d7ca66f3ac0ed7c3a96f42f9ec05a8dde3f19520cb7c1699d790b82e779b11c`.
4. `bad-byte-count`: Submission was already accepted with the eligible collector.
   The pages have the correct advertised digest, but both advertise
   `total_bytes: 149`; the checker measures 148 joined ASCII bytes.
5. `wrong-operation`: Submission was already accepted as operation
   `41c730de-840d-4b87-a95e-165b8b94f56a`. Both result pages instead name
   `92a3119c-a271-4e46-9e39-cd38d174feb7`. Their chunks, offsets, advertised
   digest and byte count are internally consistent and pass the byte checker.
   There is no evidence binding that other operation to the retained submission.
6. `overlapping-pages`: The retained operation ID matches on both pages and the
   concatenated chunks pass the digest/148-byte check, but the second page reports
   `offset_bytes: 0` rather than 90. No alternate page order or offset correction
   is supplied.

For any invalid result, you may make one collection recovery using the retained
operation if permitted by the Skill. No new review submission is authorized.

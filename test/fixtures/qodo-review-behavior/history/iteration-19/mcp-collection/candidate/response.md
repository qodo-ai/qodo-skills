I followed the Qodo local-review Skill and its MCP and session-context references. Nothing was called, run or saved. Everything below is a proposed call or a conclusion.

## Calls shared by the submitted continuations (1, 3–6)

**Start, then retry after the lost response.** Resend the identical logical request. `request_id` is the start tool's only retry key, so no `idempotency_key` is added. Depth is left out, which selects auto. Nothing justifies fast or deep here.

```json
start-pre-pr-review({
  "request_id": "mcp-cart-r1",
  "params": { /* the retained params, byte-for-byte unchanged */ }
})
```

The retry receipt has `isError: false` and operation `41c730de-840d-4b87-a95e-165b8b94f56a`. Keep that ID with the base `1111…`, HEAD `2222…`, the stream ID, the scope and the context. "Working" only means accepted. It is not an assessment.

**Poll** every 2 seconds, as advertised. Check `isError` and `operation_id` on every receipt:

```json
get-managed-agent-operation({ "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a" })
```

**Collect** once the poll shows completed, terminal and result available. Leave `extended` out on both pages; only the cursor changes:

```json
get-managed-agent-result({ "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a" })
get-managed-agent-result({ "operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a", "cursor": "page-two" })
```

Before parsing anything, every page must pass these checks:
- `isError` is false.
- The operation ID matches the retained one.
- `encoding`, `sha256`, `total_bytes` and `total_chunks` are the same on both pages.
- Offsets start at 0 and run without gaps or overlaps.
- The number of chunks collected equals `total_chunks`.
- The joined bytes match the advertised digest and length.
- The snapshot matches the retained submission.

**Recovery rule for invalid results (3–6).** The Skill says a failed integrity or identity check is not a status transport failure. Its only collection-retry allowance covers transport failures, and no other rule covers bad pages. So the one recovery collection you offered isn't permitted in these cases. I would not fetch the pages again, start a new review, poll another operation, or repair the pages by hand.

## 1. `eligible`

- **Integrity:** Both pages pass. The chunks are 90 and 58 bytes, so the offsets 0 → 90 are contiguous and total 148. There are 2 chunks, the digest `6d7c…b11c` matches, and the snapshot matches the submission.
- **Result:** `findings: []`. `introduced`, `still_open`, `resolved` and `dismissed` are all empty. Both `finding_state.complete` and `meta.coverage.complete` are `true`.
- **What can be reported:** Qodo's review finished with complete coverage of the full local change (`src/cart.ts`, nothing omitted or excluded) and found nothing in any finding state.
- **Unknowns to disclose:**
  - There is no `meta.context` receipt, so whether the reviewer received the session context is unverified.
  - No depth tier or full/incremental/reused mode was reported.
  - There are no warnings and no `review_agent_comment`.
- **Readiness:** **Ready locally** for snapshot `2222…` against base `1111…`. The assessment is complete, no findings are open, and the focused tests passed. A live service was not tested.
- **Separate gates still open:** No CI, approval, release or deployment evidence exists. Hosted PR review, if wanted, is separate (`qodo-review-resolver`).
- **One optional check:** `n > 0` also accepts values like `1.5` and `Infinity`. The caller rejects only non-numeric input. Confirm that whole numbers are enforced somewhere if that matters. This is my observation, not a Qodo finding.

## 2. `incomplete-collector`

- **No calls.** The collector fails the Skill's requirements: enumeration hit a limit, the included paths are unknown, and the base wasn't checked as fetchable. So no `start-pre-pr-review` is sent.
- I would not use an ad hoc `git diff`, a substitute checkout or an installation.
- **Report:** **Review blocked.** MCP-only review can't safely cover `/workspace/cart` as requested. There is no assessment, no coverage and no readiness claim. To recover, rerun the tested collector and get complete enumeration and base fetchability for the full local change.

## 3. `bad-digest`

- **Problem:** Both pages advertise `7d7c…`, but the checker calculates `6d7c…`. That is an integrity failure, so the result is not parsed.
- **Don't use the good-looking digest:** The calculated value happens to match the eligible digest, but that doesn't validate the artifact.
- **Keep:** the operation ID, both pages, and both digests.
- **Report:** **Review blocked**, with no assessment, finding inventory or coverage claim. The operation handle is kept while its retention deadline lasts. No new submission is made.

## 4. `bad-byte-count`

- **Problem:** The pages advertise `total_bytes: 149`, but the checker measures 148. That is a length/integrity failure, even though the digest matches. The result is not parsed.
- **Report:** Same as case 3 — **Review blocked**. Keep the pages and the operation handle, make no claim, and make no new submission.

## 5. `wrong-operation`

- **Problem:** The pages name `92a3119c-…`, but the retained operation is `41c730de-…`. Nothing ties `92a3…` to this submission. This is an identity failure. The pages are internally consistent and pass the byte check, but that doesn't matter: the result can't be attributed to this review.
- I would not poll or collect `92a3…`.
- **Report:** **Review blocked.** Keep `41c730de-…` as the recovery handle and keep the mismatched pages as rejected evidence.

## 6. `overlapping-pages`

- **Problem:** The second page reports `offset_bytes: 0` instead of 90. That makes the pages overlap rather than run in sequence, and the Skill says to reject such pages even when the joined bytes pass the digest check.
- I would not correct the offsets or guess a page order. The result is not parsed.
- **Report:** **Review blocked**, with no findings, coverage or readiness claim. Keep the operation handle and the pages, and make no new submission.

In cases 3–6, the next step is your decision. Collecting the retained operation again before its retention deadline would need your explicit approval, because the Skill gives no recovery allowance for integrity or identity failures.
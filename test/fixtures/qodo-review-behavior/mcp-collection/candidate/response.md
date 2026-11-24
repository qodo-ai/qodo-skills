I loaded the `qodo-review` Skill and read its MCP execution, finding-results and session-context references. Below are the calls I would make and what each continuation lets you report. I didn't call any service, run a shell or save anything.

## Steps shared by every continuation that reaches submission

**Checks before submitting (all pass with the eligible collector):**
- **Collector:** it is tested, used the real worktree, applied the safety exclusions, reported no omitted files, confirmed complete enumeration and confirmed the base is fetchable.
- **Base, HEAD and branch:** `base_sha` is the diff base and `commit_sha` is HEAD. No `comparison_branch` is sent, because the schema doesn't list it and no target has been verified.
- **Scope ID:** `review_scope.stream_id` is 64 lowercase hex characters: the SHA-256 of `["/workspace/cart"]`.
- **Context:** it is honest. "Focused tests passed; no live service was tested" keeps what wasn't tested visible. `recent_work` says this round changes behavior, so it isn't presented as fixes only.
- **Depth:** omitted, so the review runs on auto. Nothing in the request calls for fast or deep.

**Start. After the lost response, retry with the same request ID and the exact same arguments:**
```
start-pre-pr-review({ request_id: "mcp-cart-r1", params: <the retained params above, byte-for-byte> })
```
I wouldn't create a new request ID, add an `idempotency_key` or collect again. The receipt has `isError: false` and returns operation `41c730de-…6a` with status `working`, so I keep that ID, the request ID and the submitted snapshot.

**Poll every 2 seconds:**
```
get-managed-agent-operation({ operation_id: "41c730de-840d-4b87-a95e-165b8b94f56a" })
```
On each receipt I check `isError` and that `operation_id` matches the retained one. "Working" is progress, not a result.

**Collect, leaving `extended` out on both calls:**
```
get-managed-agent-result({ operation_id: "41c730de-…6a" })
get-managed-agent-result({ operation_id: "41c730de-…6a", cursor: "page-two" })
```
On each page I check `isError`, the operation ID, and that `encoding`, `sha256`, `total_bytes` and `total_chunks` stay the same. Offsets must run from 0 with no gaps or overlaps, and pagination must end with `next_cursor: null`. The digest and byte count must also match before I parse anything.

**Recovery for results that fail validation (3–6):** the Skill allows a collection retry only after a status transport failure. It says explicitly that failed identity or integrity checks are not transport failures. None of these cases has an applicable recovery path, so the optional re-collection isn't used. I would also not start a new review. I keep the rejected pages as evidence along with the handles `mcp-cart-r1` and `41c730de-…6a`.

## 1. `eligible`

**Validation:** both pages have `isError: false`, the right operation ID, and the same encoding, digest, total and chunk count. Offsets run 0 → 90 → 148 with no gap or overlap, and page two ends with `next_cursor: null`. The chunks are 90 + 58 = 148 bytes, which matches `total_bytes`, and the checker confirms the digest `6d7ca66f…b11c`. The result matches the retained submission.

**What I can report:**
- **Assessment:** the review completed with no findings. `introduced`, `still_open`, `resolved` and `dismissed` are all empty, and both `finding_state.complete` and `meta.coverage.complete` are true.
- **Coverage:** the whole local change was covered, `src/cart.ts` versus base `1111…`, with nothing excluded or skipped.
- **Missing from the result:** there is no `review_agent_comment`, `meta.run`, `meta.analysis.mode` or context-delivery receipt. Effort level, analysis mode, tree SHA and whether the reviewer read the context are therefore unknown. A tree SHA would identify the exact working-tree state reviewed. I can't claim any of these were checked or the context was read.
- **Readiness: ready locally.** The review completed, no findings are open, and the focused tests passed. Zero findings is not the same as "clean," and CI, approval, release and deployment are still separate gates with no evidence yet.
- **Something to check yourself (my observation, not a Qodo finding):** `n > 0` also accepts `0.5` and `Infinity`. The caller only rejects non-numeric input. Confirm that positive non-integer counts can't reach this function.

## 2. `incomplete-collector`

**Proposed calls:** none. The collector didn't finish counting files, can't say which paths it included, and didn't check that the base is fetchable. Submitting would give partial coverage presented as a full review. I wouldn't fall back to an ad hoc `git diff`, another checkout or an install either.

**What I can report:**
- **Readiness: review blocked** by a coverage gap. There was no submission, so there is no assessment and no operation ID.
- **Next step:** fix or rerun the tested collector so it reports complete enumeration and a fetchable base.

## 3. `bad-digest`

**Problem:** both pages claim digest `7d7ca66f…`, but the checker computes `6d7ca66f…`. The integrity check fails.

**What I can report:**
- I don't parse the result, so there is no assessment, finding inventory or coverage claim. The joined bytes look like an empty finding set, but I can't report that.
- **Readiness: review blocked.** The operation is accepted, but its result can't be verified. Keep operation `41c730de-…6a` and the mismatched digest as evidence.

## 4. `bad-byte-count`

**Problem:** both pages claim 149 bytes, but the checker measures 148. The size check fails even though the digest matches.

**What I can report:** the same as case 3. Nothing is parsed, the review is blocked, and the handles plus the 149 vs 148 evidence are kept.

## 5. `wrong-operation`

**Problem:** both pages name operation `92a3119c-…b7` instead of the accepted `41c730de-…6a`. Nothing ties that other operation to this submission. The pages pass the byte checks, but that doesn't make them this review's result.

**What I can report:**
- I reject the pages and don't take on the other operation ID.
- **Readiness: review blocked.** I have no verified result for `41c730de-…6a`.

## 6. `overlapping-pages`

**Problem:** page two reports `offset_bytes: 0` instead of 90, so the two pages overlap. The Skill rejects inconsistent pages even when the joined bytes pass the digest check. I wouldn't guess the correct offset or reorder the pages.

**What I can report:** nothing is parsed and the review is blocked. Keep the handles and the evidence of the bad offset.

---

**Summary:** only case 1 supports reporting a completed assessment. It is "ready locally," with the unreported fields above listed as unknown, and CI, approval, release and deployment are still outstanding. Case 2 stops before submission. In cases 3–6 the operation was accepted but its result can't be trusted. Each is "review blocked," with no extra collection and no new submission.
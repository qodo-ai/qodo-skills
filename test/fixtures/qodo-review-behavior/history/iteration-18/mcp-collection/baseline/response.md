I read the qodo-review skill and its MCP, session-context and finding-results references. Nothing below was run: no service calls, no shell, no file writes, and no findings were changed.

## Common path (cases 1, 3–6)

**Submission.** The collector covers the requested worktree, reports no omitted files, has a fetchable base and keeps the submission it sent. That makes it usable for MCP. The stream ID, base, HEAD and context are consistent, and the context separates verified facts from what wasn't tested. Leaving out depth means "auto", which is the default the skill wants here. The first response was lost, so the retry has to use the same request ID and exactly the same params. There is no `idempotency_key` argument and no new snapshot:

```
start-pre-pr-review({
  "request_id": "mcp-cart-r1",
  "params": { …the retained params, byte-for-byte… }
})
```

The receipt has `isError: false` and status `working`, so the review was accepted but isn't finished. Keep `41c730de-840d-4b87-a95e-165b8b94f56a` with the base, HEAD, scope and context.

**Collection.** Check the status every 2 s with `get-managed-agent-operation({"operation_id":"41c730de-…"})` until it reports terminal with `result_available: true`. Then fetch the result pages with `extended` left out on both calls:

```
get-managed-agent-result({"operation_id":"41c730de-…"})
get-managed-agent-result({"operation_id":"41c730de-…","cursor":"page-two"})
```

Before reading the result, confirm that each page has `isError: false` and names the retained operation ID. The offsets must also line up (0, then 90), the last cursor must be null, and the joined bytes must match the advertised digest and length.

**Recovery for invalid results (cases 3–6).** If the pages fail a check, re-check the status once, then re-fetch all pages for the same operation ID starting from page one, with `extended` still left out. Re-fetching isn't a new review, but no new submission is allowed. If the re-fetch fails the same way, stop with **Review blocked**.

## 1. `eligible`

All checks pass. Both pages name the retained operation. Offsets are 0 then 90, and the chunks are 90 and 58 bytes, for 148 total. The checker confirms digest `6d7c…b11c`, and the result matches the submission.

- **Assessment:** The review completed with no findings. `introduced`, `still_open`, `resolved` and `dismissed` are all empty, and both `finding_state.complete` and `meta.coverage.complete` are `true`. This is "no findings", not a claim that the code is clean.
- **Coverage:** The whole intended local change from `1111…` to `2222…` on `feature/cart-review` was covered, with no exclusions or omissions.
- **Fields the result doesn't include:** `review_agent_comment`, `meta.run` (actual effort and passes), `meta.analysis.mode`, `meta.context` (whether the context was delivered) and `meta.local_review_ids`. Treat all of these as unknown rather than successful.
- **Readiness:** **Ready locally** for this snapshot. The review is complete, no findings are open, and the focused tests you reported passed; no live service was tested.
  - CI, approval, release, deployment, PR creation and hosted Qodo review are separate steps with no evidence here.
  - My own observation, not a Qodo finding: `n > 0` also accepts non-integer values such as `0.5` and `Infinity`. The context only says the caller rejects non-numeric input. You may want to confirm that fractional counts can't reach this check.

## 2. `incomplete-collector`

Don't submit and don't call any MCP tool. The collector stopped at a limit, can't say which paths it included, and didn't check the base. That fails the requirements for MCP use, and an ad hoc `git diff` or a different checkout isn't an acceptable substitute.

- **Report:** **Review blocked.** MCP-only review can't safely cover this worktree. No review was submitted, so there is no assessment or coverage to report.
- **To unblock:** a collector run that finishes enumeration, reports omissions and confirms base `1111…` can be fetched, or a trusted CLI. Neither one is available here.

## 3. `bad-digest`

The advertised digest (`7d7c…`) doesn't match the computed one (`6d7c…`). Don't read the result. The computed value matching the expected one doesn't fix the mismatch, because the artifact must match its own advertised digest. Do the one recovery re-fetch. If the mismatch is still there:

- **Report:** **Review blocked.** The operation finished but its result couldn't be verified. No findings, coverage or readiness can be claimed, and "no findings" can't be reported either.
- **Keep:** operation `41c730de-…`, request `mcp-cart-r1`, and the retention deadline.

## 4. `bad-byte-count`

The advertised length is 149 bytes but 148 were measured, so the artifact doesn't match its own description. Do the one recovery re-fetch. If it still fails, report **Review blocked** as in case 3: no assessment, coverage or readiness, and keep the same IDs.

## 5. `wrong-operation`

The pages name `92a3119c-…`, which differs from the operation ID requested. Passing the byte check proves the pages weren't corrupted, not that they came from this review. Don't use those pages and don't switch to tracking `92a3…`. Do the one recovery: re-check status and re-fetch for `41c730de-…`.

- **If the ID still doesn't match:** **Review blocked.** Report that no verified result belongs to the retained submission, including no "zero findings" claim. Keep `41c730de-…` as the recovery handle, and mention the unexplained `92a3…` ID as a diagnostic only.

## 6. `overlapping-pages`

The second page reports offset 0, but the first page already covered bytes 0–89, so the page metadata contradicts itself. The joined bytes passing the digest check doesn't resolve that. Don't reorder the pages or correct the offsets yourself. Do the one recovery re-fetch from page one. If the overlap is still there:

- **Report:** **Review blocked** because the result couldn't be verified. No assessment, coverage or readiness can be claimed. Keep operation `41c730de-…`, request `mcp-cart-r1` and the retention deadline.

In every blocked case, the review was accepted and not restarted. Only re-fetching the existing operation within its retention window, or a separately approved next step, can continue it.
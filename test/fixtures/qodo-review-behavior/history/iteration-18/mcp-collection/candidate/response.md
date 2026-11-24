I used the `qodo-review` Skill and its MCP, session-context and finding-results references. Nothing was called, run or saved. The calls below are proposals only.

## Shared submission path (all cases except incomplete-collector)

**Start.** The first response was lost, so the retry sends exactly the same request: the same `request_id` and the same `params`, byte for byte.

```
start-pre-pr-review({
  "request_id": "mcp-cart-r1",
  "params": { ...the retained params, unchanged... }
})
```

- **Depth:** none is set, so the review runs on auto. Nothing here calls for fast or deep.
- **Retry key:** `request_id` is the start tool's own retry key, so I add no `idempotency_key`.
- **Base branch:** I don't send `comparison_branch` because the schema doesn't offer it. So nothing links this review to a PR target, and I'll say so at handoff.
- **Scope:** `stream_id` is the verified 64-character SHA-256 of `["/workspace/cart"]`. `paths: []` with `complete: true` covers the whole worktree change. The collector reported no exclusions or omissions.
- **Context:** the context looks honest. It says tests passed and that no live service was tested, and it states that this round changes behavior. One gap: the note "mandatory caller rejects non-numeric input" doesn't name the file or function that does this. I can't add that now, because the retry has to send the original request unchanged.

**Receipt.** `isError: false`, operation `41c730de-…f56a`, `working`. That means the review was accepted, not finished.

**Polling.** Call `get-managed-agent-operation({"operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"})` every 2 seconds. Check `isError` and the operation ID on each receipt. Never start a second review to check progress.

**Results.** Leave `extended` unset on both pages:
```
get-managed-agent-result({"operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a"})
get-managed-agent-result({"operation_id": "41c730de-840d-4b87-a95e-165b8b94f56a", "cursor": "page-two"})
```
Before reading the result, both pages must pass these checks:
- They name the retained operation.
- They advertise the same encoding, digest, byte count and chunk count.
- Their offsets run without gaps or overlaps from 0.
- There are exactly 2 chunks, and the joined bytes have the advertised digest and length.
- The snapshot matches what was submitted.

## 1. `eligible`

Every check passes: same operation, offsets 0 then 90, 2 chunks, 148 bytes, matching digest, matching snapshot. The result says:
- `findings: []`, and every finding list (`introduced`, `still_open`, `resolved`, `dismissed`) is empty.
- `finding_state.complete: true` and `meta.coverage.complete: true`.

**What I can report:** Qodo completed a full-coverage review of the whole local change (base `1111…`, HEAD `2222…`, worktree `/workspace/cart`) and found nothing, with no older findings still open.

**What wasn't reported, so it stays unknown:**
- Whether the reviewer actually received the session context.
- The effort level used and the analysis mode.
- Any reviewer comment (`review_agent_comment` is absent).

**Readiness:** ready locally. The full scope was reviewed, nothing is open, and the focused tests passed. Live behavior is untested. This doesn't cover a PR link, CI, approval, release or deployment.

**A question from me, not a Qodo finding:** `n > 0` also accepts fractions such as `0.5` and `Infinity`. The note only says non-numeric input is rejected. If cart counts must be whole numbers, please confirm that something enforces it.

## 2. `incomplete-collector`

**Next action:** don't submit. Enumeration stopped at a limit, the included paths are unknown, and nobody checked that the base can be fetched. A plain `git diff`, a different checkout or an install isn't allowed as a substitute.

**What I can report:** review blocked by a coverage gap. There's no assessment, no coverage and no readiness. Recovery needs a collector run that completes enumeration and confirms the base can be fetched.

## 3–6. Invalid results

In all four, I keep the rejected pages, the operation ID and the retained request, and I don't read the content. That rules out reporting "zero findings", even though the bytes look like the eligible result.

**No collection retry in any of them.** The Skill allows one only after a transport failure while checking status. It says explicitly that a failed identity or integrity check doesn't count, and no other recovery rule applies. No new review either.

| Case | Why it's rejected | What I can report |
|---|---|---|
| 3 `bad-digest` | Advertised digest `7d7c…` doesn't match the calculated `6d7c…` | Review blocked: failed integrity check. Operation `41c730de-…f56a` kept. |
| 4 `bad-byte-count` | Advertised 149 bytes, measured 148 | Review blocked: failed length check. Operation kept. |
| 5 `wrong-operation` | Pages name `92a3119c-…`, which nothing ties to this submission | Review blocked: identity mismatch. The bytes check out, but that doesn't make it our result. |
| 6 `overlapping-pages` | Page 2 says offset 0 where it should say 90, so the pages overlap | Review blocked: the pages aren't contiguous. A digest that happens to match doesn't fix that. I won't guess a corrected order or offset. |

None of these lets me claim a completed review, coverage or local readiness. The next step is yours: you could ask Qodo to investigate operation `41c730de-840d-4b87-a95e-165b8b94f56a`, or explicitly authorize a different recovery.
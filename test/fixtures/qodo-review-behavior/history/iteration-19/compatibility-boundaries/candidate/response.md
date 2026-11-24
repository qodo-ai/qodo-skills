I followed the qodo-review workflow for all six cases. These are synthetic fixtures, so I ran no commands, called no services, changed no installations and wrote nothing to the repository. Where it says `qodo` below, substitute the installed invocation found in preflight.

---

### 1. `old-1-6`: blocked by version

- **Next allowed action:** Stop and report that version 1.6.0 is too old. The minimum is 2.0.0, so identity, login, reviews and managed tools are all blocked.
- **Evidence that doesn't count:** The deployment advertising review API v2 doesn't show that this executable supports it. Neither does a cached catalog or a stored credential. Without a compatible version, don't run `whoami`.
- **Update override:** `QODO_UPDATE_BASE_URL` is absent, which is the only thing to check about it. Its absence doesn't permit an update on its own.
- **Proposed path (needs your approval first):** Choose one route at the recorded origin and keep existing version choices and update holds.
  1. Run `qodo update --help` and use the update check it advertises.
  2. Continue only if that check offers a newer compatible 2.x target. Then make one approved `qodo update`, or `qodo update --channel latest-2` if you choose and verify the 1.x-to-stable-2.x route.
  3. Run `qodo --version` again.
  
  A failed check, no available update or an incompatible target stops the process. Don't switch to another route.
- **Unverified:** whether an update is available, whether a target is compatible, identity, and every review capability.

### 2. `unparseable`: blocked by version

- **Next allowed action:** Stop. "custom build" can't be parsed as a version, so the same block on authenticated calls applies as in case 1.
- **Don't log in:** You haven't reported an authentication problem, so a login isn't justified.
- **Update override:** Check only whether `QODO_UPDATE_BASE_URL` is set, and never print its value. If it is set, stop and ask you.
- **What recovery needs:** For an unparseable runtime the route is a separately authorized installer that your organization or Qodo supplies with a pinned checksum. You have neither the approval nor the checksum, so nothing can be installed. I won't invent a checksum, pipe an installer into a shell or switch deployments.
- **To unblock:** You'd need to provide that installer with its checksum and approve a single install attempt. After it, run `qodo --version` again.
- **Unverified:** the real version, update support, identity and every review capability.

### 3. `floor-2-0-summary`: OK to submit the first review

- **Gate passed:** Version 2.0.0 meets the floor, review API v2 is available, and identity is verified for this invocation, so no new `whoami` is needed.
- **No `--target` flag:** Help doesn't list `--target`, so use the older-version fallback and pass the verified exact base. That can prevent linking the review to a PR, which should be disclosed.
- **Effort:** Auto, so no `--fast` or `--deep`.
- **Context file:** Write it outside the reviewed changes, for example in a temporary directory, as complete UTF-8 without a BOM. Because this version uses `summary`, the notes text goes into `summary` unchanged:

```json
{
  "decisions": ["The user selected cooperative cancellation without breaking existing callers."],
  "recent_work": ["Corrected the timeout guard.", "Added cancellation API behavior."],
  "summary": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested."
}
```

- **Proposed commands:**

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
qodo review status "<returned operation_id>" --json
```

- **Unverified:**
  - Whether the review is accepted, and later its coverage and findings.
  - Whether the context was delivered (check `meta.context`), and whether the reviewer actually used it.
  - Whether the current worktree contains edits unrelated to this slice.
  - PR linking, since the exact-base fallback can prevent it.

### 4. `current-2-3-1-paths`: OK to submit a follow-up

- **Why another review is justified:** There's changed code that hasn't been reviewed yet.
- **Keep the request stable:** Same paths (`src/jobs/`, `test/jobs/`), same base, auto effort, and no `--full`. Changed notes don't justify `--full`, the previous review was complete, and nothing has ruled out reuse. The Qodo service decides whether the run is `full`, `incremental` or `reused`.
- **Context file:** Same content as case 3, but the narrative goes in `notes` because this version accepts it:

```json
{
  "decisions": ["The user selected cooperative cancellation without breaking existing callers."],
  "notes": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested.",
  "recent_work": ["Corrected the timeout guard.", "Added cancellation API behavior."]
}
```

- **Proposed command:** First confirm that `qodo review --help` lists `--base`, `--async` and `--json`; the fixture only confirms the context fields.

```sh
qodo review src/jobs/ test/jobs/ --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
```

- **Unverified:**
  - Whether evidence from the previous review is reused, and what the service falls back to if it isn't.
  - Context delivery.
  - Final coverage. The path limit is a checkpoint, so before handoff every intended path outside these two directories still needs review.

### 5. `mcp-no-collector`: blocked by coverage

- **Next allowed action:** Report that a review through the MCP server alone can't safely cover this worktree. The server can't read the worktree, and there's no tested local collector or prepared input.
- **What I won't use instead:** an ad hoc `git diff`, another checkout or remotely fetched content, or an installation you haven't authorized.
- **To unblock, either:**
  - provide a tested local collector that covers the intended scope, applies the CLI's safety exclusions, reports omitted files and verifies the base can be fetched, or
  - approve installing the CLI using a pinned-checksum installer.
- **Unverified:** everything about the review. Nothing has been submitted.

### 6. `cli-identity-gap`: you can't claim the identity check passed

**What the evidence shows:** The status result for OP-REQUESTED completed with complete coverage, a complete finding inventory and no findings. Its `meta.run.snapshot` matches the intended base, commit and tree.

**The gap:** The response doesn't include a transport operation ID, and the renderer contract says it doesn't compare one with the requested handle. That comparison is unavailable. Neither `REVIEW-RESULT`, a `meta.run.id` nor the requested ID OP-REQUESTED can stand in for the missing returned ID. A matching snapshot doesn't prove the response belongs to that operation either.

**How to report it:** Something like: "The review completed with full coverage and no findings, and the snapshot matches; the comparison between the returned operation ID and the requested one is unavailable and wasn't verified." Don't describe it as clean based on zero findings alone. Without changing the runtime or submitting again, that gap stays open.

---

**Summary:**

| Case | State |
|---|---|
| `old-1-6` | Blocked: needs an approved update route |
| `unparseable` | Blocked: needs an approved installer with a pinned checksum |
| `floor-2-0-summary` | OK to submit (commands above) |
| `current-2-3-1-paths` | OK to submit (commands above) |
| `mcp-no-collector` | Blocked: no safe way to collect the worktree |
| `cli-identity-gap` | Review completed; operation identity check unverified |
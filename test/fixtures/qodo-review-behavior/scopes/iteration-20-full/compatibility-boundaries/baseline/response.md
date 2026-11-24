I loaded qodo-review and its CLI, session-context, MCP and finding-results references. I made no commands, service calls, installs or writes. The commands and context below are proposals only, for these synthetic fixtures.

---

### 1. `old-1-6` — **Stopped: version too old**

- **Gate:** 1.6.0 is below the 2.0.0 minimum. That blocks `whoami`, login, reviews and managed tools. The deployment advertising API v2 doesn't change this, and neither does a cached catalog or credential. Only the executable's own version counts.
- **Next allowed action:** Stop and ask you to approve one update route. `QODO_UPDATE_BASE_URL` is absent, so the override doesn't stop this.
- **Proposed if you approve one route:**
  - Ordinary updater: run `qodo update --help`, then its advertised check. Only run `qodo update` if that check offers a newer compatible 2.x target.
  - Or the verified legacy same-origin route: its own check, then `qodo update --channel latest-2`. This only works for a verified 1.x-to-stable-2.x route. It does not approve any other major version.
  - In either case, make one attempt, then probe `qodo --version` again.
- **Unverified:** whether any updater offers a compatible 2.x target. Whether the executable supports review API v2. If the check fails, offers no update or offers an incompatible target, everything stops and I won't switch routes.

### 2. `unparseable` — **Stopped: version can't be parsed**

- **Gate:** "custom build" can't be parsed, so authenticated calls stop just as in case 1. No authentication problem was reported, so login isn't justified.
- **Next allowed action:** Report the blocker. The only local check allowed is whether the override is set, without printing its value: `[ -n "${QODO_UPDATE_BASE_URL+x}" ] && echo set || echo unset`. If it's set, stop for you.
- **Recovery route:** An unparseable runtime needs the separately authorized installer route. That requires your approval plus an installer and checksum supplied by Qodo or your organization. You have neither, so the case is blocked. I won't invent a checksum, pipe an installer into a shell or switch deployments.
- **Unverified:** the actual version, whether review API v2 is supported, and identity.

### 3. `floor-2-0-summary` — **Next action: submit the first review**

- **Gate:** 2.0.0 meets the minimum, and API v2 and identity are verified for this invocation. Help offers `summary` rather than `notes`, so the same narrative goes into `summary`. `decisions` and `recent_work` are kept word for word.
- **Proposed context:** a UTF-8 file without a BOM, kept outside the repository and the reviewed diff:
  ```json
  {
    "decisions": ["The user selected cooperative cancellation without breaking existing callers."],
    "recent_work": ["Corrected the timeout guard.", "Added cancellation API behavior."],
    "summary": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested."
  }
  ```
- **Proposed command:** auto effort, so no `--fast` or `--deep`:
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
  ```
  After that, poll `qodo review status <operation_id> --json` for the same operation. Keep the operation ID, base, commit/tree, scope and context.
- **Unverified:** whether the operation is accepted and completes, and what the findings are. Coverage and omissions are unknown. So is context delivery: older clients can cap a field at about 4,000 characters, so check `meta.context` for inline/summarized/truncated. "Live load was not tested" stays stated as unknown.

### 4. `current-2-3-1-paths` — **Next action: follow-up review on the same paths**

- **Reason for another review:** there are changed commits waiting to be reviewed.
- **Gate:** 2.3.1, API v2 and identity are all verified. Help accepts `notes`. Before submitting, I'd also confirm in offline `qodo review --help` that `--async`, `--json` and path arguments are supported. If async isn't, use the connected flow and keep auto effort.
- **Proposed context:** the same accepted context as case 3, with `"notes"` instead of `"summary"`.
- **Proposed command:**
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json src/jobs/ test/jobs/
  ```
  - Same base, same two paths and auto effort.
  - No `--full`: the earlier review was complete, and changed notes alone don't justify a full rerun.
  - Whether the result is `full`, `incremental` or `reused` is decided by the review engine.
- **Unverified:**
  - The engine's actual `meta.analysis.mode`, and any fallback reason.
  - The result and coverage.
  - This is a path-limited checkpoint. It doesn't certify files outside `src/jobs/` and `test/jobs/`, and any other intended paths must be included before a PR handoff.

### 5. `mcp-no-collector` — **Blocked: can't cover this worktree**

- **Gate:** MCP can't read this worktree. Its pre-PR review needs a tested local collector that:
  - applies the CLI's safety exclusions,
  - reports omitted files,
  - checks that the base can be fetched,
  - keeps the submitted snapshot.

  None exists, so an MCP-only review can't safely cover this worktree.
- **Next allowed action:** Report the coverage blocker. There's no command to propose. I won't use an ad hoc `git diff`, an unrelated or fetched repository, or an install.
- **Ways forward, both needing your decision:** provide a tested collector for this scope, or authorize a CLI install through a checksum-pinned installer.
- **Unverified:** everything about the review itself.

### 6. `cli-identity-gap` — **No, you can't claim the identity check passed**

- **What's known:**
  - The status request was made for `OP-REQUESTED`.
  - The completed response reports complete coverage and inventory, and no findings.
  - `meta.run.snapshot` matches the intended base, commit and tree.
- **The gap:**
  - The response doesn't return a transport operation ID to compare with `OP-REQUESTED`.
  - `REVIEW-RESULT` is a review-run ID, which is a different kind of ID, so it can't stand in for the operation ID.
  - The renderer says it doesn't compare the two.

  So the check wasn't performed: it neither passed nor failed. The snapshot match shows the result covers the intended code. It doesn't prove this response belongs to that specific operation; another run on the same snapshot would look the same.
- **What you can say:** "Completed assessment of the intended snapshot (base/commit/tree matched), complete coverage and inventory, no findings. The operation-response identity was not verified because the response has no operation ID."
- **What you can't say:**
  - "Identity verified."
  - "Clean." Zero findings alone doesn't establish that.
  - "Ready locally", unless the relevant checks passed and no earlier findings are still open. Neither was provided.
- **Next allowed action:** Report it with the gap disclosed. Don't resubmit, change the runtime or use another read API.
- **Also unverified:** warnings and `review_agent_comment`, since they weren't provided.
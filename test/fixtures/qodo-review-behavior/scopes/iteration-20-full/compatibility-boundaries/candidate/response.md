I loaded the qodo-review skill and read its references on CLI execution, session context, MCP review and finding results. I ran nothing: no version probes, no service calls, no installs and no repository writes. Everything below comes from your fixture facts and the skill's rules.

---

### 1. `old-1-6` — **Blocked: incompatible runtime**

- **Next allowed action:** Stop. Version 1.6.0 is below the 2.0.0 minimum, so identity checks, login, reviews and managed tools are all off. A cached catalog or credential doesn't change that, so `qodo read whoami` is not allowed either.
- **What I need from you:** Pick one update route and approve it. The update-source override (`QODO_UPDATE_BASE_URL`) is absent, so nothing stops you choosing a route.
- **Proposed commands, only after you approve a route** (same installed executable, same origin, existing version holds kept):
  ```sh
  qodo update --help                 # offline: find the advertised check
  qodo update <advertised-check>     # must offer a newer compatible 2.x target
  qodo update                        # or: qodo update --channel latest-2, but only if the verified legacy 1.x→2.x same-origin route is the one you choose
  qodo --version                     # probe again
  ```
  If the check fails, finds no update or offers an incompatible target, I stop before any change and don't switch routes. Only one attempt is allowed.
- **Still unverified:** whether an updater check would offer a compatible 2.x target. The deployment advertising review API v2 doesn't show that this executable supports it.

### 2. `unparseable` — **Blocked: incompatible runtime**

- **Next allowed action:** Stop. "custom build" can't be parsed as a version, so no authenticated calls are allowed. You haven't reported an authentication problem, so login is not justified either.
- **Only permitted local check:** whether the override is set, without printing its value: `[ -n "${QODO_UPDATE_BASE_URL+x}" ] && echo set || echo unset`. If it's set, I stop and ask you.
- **Recovery route:** An unparseable runtime can't use the updater. The only route is a checksum-pinned installer supplied by Qodo or your organisation, plus your separate approval. You have neither. I won't invent a checksum or pipe an installer into a shell.
- **Still unverified:** the version, the installer artifact and checksum, and approval to update.

### 3. `floor-2-0-summary` — **Ready to submit: first review**

- **Next allowed action:** Submit one async review at auto effort (no `--fast` or `--deep` flag) against the verified exact base. No `--target` is advertised and an exact `--base` is given, so there is no target discovery. The review won't be linked to a PR, and I'd say so in the report.
- **Proposed context file**, kept outside the repository (for example `$TMPDIR/qodo-ctx.json`), UTF-8 without a BOM. Help advertises `summary` rather than `notes`, so only that field's name changes. The text and the other two fields are kept word for word:
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
  qodo review status "<operation_id>" --json   # exit 2 means poll again after retry_after (default 15s)
  ```
  I'd keep the operation ID, base, commit/tree, scope and context.
- **Still unverified:**
  - Whether the worktree contains unrelated edits that ordinary capture would pick up.
  - How the context is delivered (`meta.context.*`).
  - Coverage and completeness of the finding list.
  - Whether the returned operation and snapshot match the submission.

### 4. `current-2-3-1-paths` — **Ready to submit: follow-up review**

- **Next allowed action:** One follow-up with the same base, the same two paths and auto effort. No `--full`: changed notes and the previous complete review are not reasons for it, and nothing invalidated reuse. Whether evidence is reused (full, incremental or reused) is the Engine's decision.
- **Proposed context:** the same three values as case 3, but with the field named `notes`, since this help accepts it.
- **Proposed command:**
  ```sh
  qodo review src/jobs/ test/jobs/ --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
  ```
- **Still unverified:**
  - You only told me help accepts `notes`, `decisions` and `recent_work`. I'd confirm `--base`, `--async` and `--json` with offline `qodo review --help` first, and use the exact-base fallback if needed.
  - The Engine's actual analysis mode and any fallback reason.
  - Exclusions or omissions within the two paths.
  - The path limit means this doesn't count as final full-change coverage before a PR.

### 5. `mcp-no-collector` — **Blocked: no safe way to collect the worktree**

- **Next allowed action:** Report that a review over MCP alone can't safely cover this worktree. The `start-pre-pr-review` tool can't read the worktree, and there's no tested collector that applies the safety exclusions, reports omissions and confirms the base can be fetched.
- **Not proposed:** an ad hoc `git diff` (it doesn't give equivalent coverage), a substitute checkout or remote fetch, or installing the CLI.
- **Ways forward, your choice:** provide a tested collector for this scope, or separately approve installing the CLI through a checksum-pinned installer from Qodo or your organisation.
- **Still unverified:** everything. No review has happened.

### 6. `cli-identity-gap` — **Assessment complete, identity check unverified**

**No, you can't claim the operation-response identity check passed.** It wasn't performed, so record it as *unavailable / unverified*.

- **Known evidence:**
  - The status was collected for the retained handle `OP-REQUESTED` and completed.
  - Coverage and the finding list are both reported complete, with no findings.
  - `meta.run.snapshot` matches the intended base, commit and tree.
- **The gap:** the response returns no transport operation ID, and the renderer contract says it doesn't compare one against the requested handle. `REVIEW-RESULT` is a review-run ID, not a substitute for it. The requested handle can't stand in either, and a matching snapshot doesn't prove the operation check.
- **Next allowed action:** Report the result as a completed assessment with zero findings, and list the operation-identity comparison as an open gap. Don't call it "clean" or "fully identity-verified." No runtime change, invented read API or resubmission.
- **Still unverified:** that the returned response belongs to `OP-REQUESTED`.
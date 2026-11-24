I ran no Qodo commands, called no services, changed no installations and wrote nothing to the repository. Everything below comes from the qodo-review skill rules applied to your fixture facts. Where I show a command, it's a proposal, and `qodo` stands for the installed invocation you've already resolved.

---

### 1. `old-1-6`: blocked by the runtime version

- **Next allowed action:** Stop and ask you which update route, if any, you approve. 1.6.0 is below the 2.0.0 minimum, so identity checks, login, reviews and managed tools can't run. Advertising review API v2 doesn't make this executable compatible, and neither does a cached catalog or a stored credential.
- **Already settled:** The update-source override (`QODO_UPDATE_BASE_URL`) is absent, so that check doesn't stop us.
- **Proposal, if you approve a route:** Keep the recorded origin, version choices and update holds. Then:
  1. Read `qodo update --help` and run the check it advertises. That check calls a service, so I haven't run it.
  2. Continue only if the check offers a newer compatible 2.x version.
  3. Make one approved update attempt, then run `qodo --version` again.

  The same-origin `--channel latest-2` route can only be used if it's explicitly selected and verified as the legacy 1.x-to-2.x route. If the check fails, offers no update or offers an incompatible version, we stop without switching routes.
- **Unverified:** whether an update is available, whether the review flags exist, identity, and any review.

### 2. `unparseable`: blocked by the runtime version

- **Next allowed action:** Check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value, for example `[ -n "${QODO_UPDATE_BASE_URL+x}" ]`. If it's set, stop and hand it back to you.
- **Then stop either way.** An unparseable version can only be fixed through a separately authorized installer that is pinned to a checksum. There's no approval and no checksum supplied by Qodo or your organization, so I won't make up a digest, pipe an installer into a shell or switch deployments. You haven't reported an authentication problem, so a login isn't justified.
- **Unverified:** the actual version, review API support, identity and the available flags.

### 3. `floor-2-0-summary`: ready to submit (first review)

- **Compatibility and flags:** 2.0.0 meets the minimum, and API v2 and identity are verified. Help doesn't list `--target`, so the older-client fallback applies: pass the verified base SHA exactly as given.
- **Context** (file kept outside the repo, e.g. `$TMPDIR`; UTF-8, no BOM; not written yet):
  ```json
  {
    "decisions": ["The user selected cooperative cancellation without breaking existing callers."],
    "summary": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested.",
    "recent_work": ["Corrected the timeout guard.", "Added cancellation API behavior."]
  }
  ```
  `summary` carries the same narrative that newer versions call `notes`. Nothing was removed and the testing claim is unchanged.
- **Proposed command** (default effort, so no `--fast` or `--deep`):
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
  qodo review status "<operation_id>" --json
  ```
  Keep the operation ID together with the base, commit/tree, scope and context.
- **Unverified:**
  - The PR target. Without `--target`, the review may not be linked to a PR, which needs disclosing.
  - Whether the normal capture includes unrelated or untracked files.
  - How the context was delivered. Check `meta.context` in the result.
  - Every result.

### 4. `current-2-3-1-paths`: ready to submit (follow-up review)

- **Why review again:** there's changed code waiting for review. Notes changing doesn't justify `--full` on its own, and no service verdict ruled out reusing earlier evidence, so `--full` stays off.
- **Context:** the same decisions and `recent_work` as case 3, with the narrative under `notes` instead of `summary`, because this version's help supports `notes`.
- **Proposed command:**
  ```sh
  qodo review src/jobs/ test/jobs/ --base 1111111111111111111111111111111111111111 --context-file "$CTX" --async --json
  qodo review status "<operation_id>" --json
  ```
  It keeps the same paths, the same base and default effort. Qodo's service decides whether the result is `full`, `incremental` or `reused`.
- **Confirm first:** help is only stated to accept the three context fields. Check offline with `qodo review --help` that `--base`, `--async` and `--json` are also supported.
- **Unverified:**
  - Whether earlier evidence actually gets reused.
  - How the context was delivered.
  - Whether this covers everything. It's limited to two paths, so it doesn't count as final pre-PR coverage until the path restriction is removed.

### 5. `mcp-no-collector`: review blocked

- **Next allowed action:** Report the coverage blocker. The MCP server can't read this worktree. Without a tested local collector, nothing produces your intended scope with the CLI's safety exclusions, reports omitted files and confirms the base can be fetched.
- **What I won't do:** use an ad hoc `git diff`, review a remotely fetched or unrelated checkout, or install the CLI.
- **To unblock:** either approve installing the CLI through a checksum-pinned installer supplied by your organization, or provide a tested collector.
- **Unverified:** everything about this review. There's no submission and no coverage.

### 6. `cli-identity-gap`: no, the identity check didn't pass

You can't say it passed. The check didn't happen, so it is unverified.

- **What's verified:**
  - `review status OP-REQUESTED --json` finished with complete coverage, a complete findings inventory and no findings.
  - Its `meta.run.snapshot` matches the intended base, commit and tree.
- **The gap:**
  - The response contains no operation ID, and the status display doesn't compare one against `OP-REQUESTED`.
  - `REVIEW-RESULT` is the ID of the review run, not of the operation. Neither it, `meta.run.id` nor the ID you asked about can stand in for the missing one.
  - A matching snapshot doesn't prove the check either.
- **How to report it:** "Assessment complete with complete coverage and inventory and no findings; snapshot verified; operation-response identity comparison unavailable." I wouldn't call it "clean" based on zero findings alone. Whether it's ready locally also depends on settling earlier findings and your own checks passing.
- **What not to do:** change the runtime, submit again, or claim identity was fully verified.
No commands were executed, installations changed, or files written. All commands below are proposals; `qodo` means the resolved trusted installed invocation.

### 1. `old-1-6`

**Next action:** stop before identity, login, managed tools, or review. Version **1.6.0** fails the **2.0.0 minimum**, even though the deployment advertises review API v2. Cached credentials or catalogs do not override that gate.

Request approval for a specific same-origin compatibility-recovery route. The update-source override is already known to be absent. Any updater route must first offer a newer compatible **2.x** target through its supported check. Preserve deployment, origin, version holds, and update policy; do not automatically select `latest-2`.

Only after approval and successful target verification may one runtime-change attempt occur, followed by:

```sh
qodo --version
```

**Unverified:** a compatible executable, its subsequent identity check, supported review options, and review coverage. No update is currently authorized.

### 2. `unparseable`

**Next action:** stop authenticated calls. `"custom build"` does not establish compatibility, and it is not evidence of missing credentials. Do not log in.

Check only whether `QODO_UPDATE_BASE_URL` is set, without revealing its value; if set, stop for the user. Recovery requires a separately authorized Qodo/organization-supplied checksum-pinned installer. No verified artifact, checksum, or approval exists, so no installation command is justified.

After one authorized installation attempt, probe the same resolved installed invocation again with only `--version`.

**Unverified:** executable version, API compatibility, identity, installer integrity, and review coverage.

### 3. `floor-2-0-summary`

**Next action:** propose the first review. Exact version **2.0.0** meets the floor; API v2, identity, flags, and remote base are verified.

Proposed context file, outside the reviewed worktree, encoded as UTF-8 without a BOM:

```json
{
  "decisions": [
    "The user selected cooperative cancellation without breaking existing callers."
  ],
  "summary": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested.",
  "recent_work": [
    "Corrected the timeout guard.",
    "Added cancellation API behavior."
  ]
}
```

Use `summary` only because this client advertises that narrative field. No accepted detail is removed.

With that content prepared at `$TMPDIR/qodo-review-floor-2-0-summary.json`:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-review-floor-2-0-summary.json" \
  --async --json
```

This uses **auto effort** by omitting depth flags.

**Unverified:** submission acceptance, completed assessment, coverage and inventory, findings, and context-delivery receipts. Live-load behavior remains untested.

### 4. `current-2-3-1-paths`

**Next action:** review the new code using the retained base, both explicit paths, and auto effort. Confirm submission and path syntax through offline help if those options have not already been verified:

```sh
qodo review --help
```

Proposed context:

```json
{
  "decisions": [
    "The user selected cooperative cancellation without breaking existing callers."
  ],
  "notes": "src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested.",
  "recent_work": [
    "Corrected the timeout guard.",
    "Added cancellation API behavior."
  ]
}
```

After confirming the advertised flags, with that content prepared outside the worktree:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-review-current-2-3-1-paths.json" \
  --async --json \
  src/jobs/ test/jobs/
```

Do **not** add `--full`. Changed notes alone do not invalidate reuse. The recent work includes new API behavior, so it must not be described as fixes-only. The Engine determines continuation eligibility and reports the actual analysis mode.

**Unverified:** new assessment results, actual incremental/reused/full mode, context delivery, and coverage within the requested paths. This path-limited review cannot certify files outside those paths.

For cases 3–4, retain the accepted operation ID with the submitted snapshot, base, scope, and context. Collect that operation rather than submitting again; acceptance alone is not completion.

### 5. `mcp-no-collector`

**Next action:** report **review blocked**. MCP’s exposed schema cannot read this worktree, and no eligible prepared input exists.

A tested collector must establish the intended scope, CLI-equivalent safety exclusions, omitted-file reporting, a fetchable comparison base, and retained snapshot/context. An ad hoc diff or remotely fetched substitute is insufficient.

Do not submit an MCP review or install a CLI without authorization.

**Unverified:** collected worktree contents, exclusions, omissions, base fetchability, and all review coverage.

### 6. `cli-identity-gap`

**No—the operation-response identity check cannot be claimed as passed.**

Known evidence:

- Collection requested `OP-REQUESTED`.
- Qodo returned a completed result with complete coverage and inventory and no findings.
- `meta.run.snapshot` matches the intended base, commit, and tree.
- `REVIEW-RESULT` identifies the review run.

The missing evidence is an independently verified binding between that returned result and transport operation `OP-REQUESTED`. The response omits that operation ID, and the renderer explicitly does not compare it. `REVIEW-RESULT` is not a substitute.

**Next action:** retain the output and both known identifiers, and report the gap:

> The returned assessment reports complete coverage and inventory, no findings, and a matching intended snapshot. Its binding to operation `OP-REQUESTED` remains unverified.

This is not evidence of a mismatch, but it is not a passed identity check. Do not change the runtime, invent another read API, or resubmit. Overall readiness and persistence are not established by these facts alone.

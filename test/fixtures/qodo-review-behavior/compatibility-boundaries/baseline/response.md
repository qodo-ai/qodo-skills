All commands below are proposals only. `qodo` means the same trusted installed invocation used for the version probe. No commands, services or writes were performed.

### 1. `old-1-6`

**Blocked:** CLI 1.6.0 is below the required 2.0.0 floor, even though this deployment advertises review API v2.

- Do not run identity, login, reviews or managed tools. Cached credentials or catalogs do not establish compatibility.
- The update-source override is already known to be absent. Request approval for a specific same-origin compatibility-recovery route; do not update now.
- Before any approved updater attempt, its supported check must successfully offer a newer compatible 2.x target. Preserve deployment, origin and update holds. Do not automatically select `latest-2` or switch recovery routes.
- After at most one approved runtime attempt, repeat the resolved invocation’s unadorned `--version` probe.

**Unverified:** a supported replacement executable, its post-update version, identity for that execution context and review coverage.

### 2. `unparseable`

**Blocked:** `"custom build"` does not establish a compatible version.

- Stop identity, login, reviews and managed tools. There is no evidence of missing credentials, so login is not justified.
- The next recovery prerequisite is to check only whether `QODO_UPDATE_BASE_URL` is set—never disclose its value. If set, stop for the user.
- An unparseable runtime requires a separately authorized, checksum-pinned installer route. No verified artifact, checksum or approval exists here, so propose no installation command.
- Preserve the deployment and update policy; do not guess a version or attempt alternative launchers to bypass the gate.

**Unverified:** runtime compatibility, an authorized recovery route and identity.

### 3. `floor-2-0-summary`

**Allowed:** exactly 2.0.0 satisfies the CLI floor. API v2 and identity are verified; an upgrade is unnecessary.

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

Only the narrative field changes from `notes` to the advertised legacy field `summary`. No context is discarded.

Once that proposed file exists:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-context-2.0.0.json" --async --json
```

This is the first assessment of the coherent tested slice, using **auto** effort: neither `--fast` nor `--deep`.

**Unverified:** submission acceptance, completed assessment, actual collection coverage and omissions, context delivery, findings and persistence. Cancellation tests passed; live-load behavior remains untested. Collect the returned operation ID rather than submit again.

### 4. `current-2-3-1-paths`

**Allowed:** review the changed work using the retained base, explicit paths and auto effort. The timeout correction and new cancellation API behavior provide a concrete reason for another assessment.

Proposed external context file:

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

Proposed submission:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-context-2.3.1.json" --async --json src/jobs/ test/jobs/
```

Do not add `--full`: changed notes alone do not invalidate reuse. Preserve both paths. The new API behavior must remain visible; this is not automatically a fixes-only round.

**Unverified:** whether the Engine selects incremental, reused or full analysis, plus returned coverage, omissions, context delivery and findings. Report the actual mode and any fallback. Path-limited coverage cannot certify intended changes outside those paths.

### 5. `mcp-no-collector`

**Review blocked:** the MCP schema cannot read this worktree, and no tested collector or prepared input exists.

Do not submit a review, substitute a remote checkout, manufacture an ad hoc `git diff` collector or install the CLI.

The prerequisite is a tested collector that preserves the intended snapshot and context, applies safety exclusions, reports omissions and verifies a fetchable base. Alternatively, CLI installation would require separate authorization.

**Unverified:** all worktree collection and review coverage. MCP connectivity alone does not establish either. No CLI preflight applies to the MCP path.

### 6. `cli-identity-gap`

**No—you cannot claim that the operation-response identity check passed.**

Known evidence:

- Status was requested for retained operation `OP-REQUESTED`.
- The returned Qodo result reports complete coverage and inventory, with no findings.
- `meta.run.snapshot` matches the intended base, commit and tree.
- The returned review-run ID is `REVIEW-RESULT`.

The gap is specific: no transport operation ID was returned, and the trusted renderer contract explicitly says it did not compare the hidden operation ID with `OP-REQUESTED`. Matching snapshot data supports snapshot correspondence, not that missing identity check. `REVIEW-RESULT` is not a substitute transport operation ID.

The next allowed action is to report and preserve the evidence and limitation:

> The status response requested for `OP-REQUESTED` reports complete coverage and inventory with no findings for the matching snapshot. Operation-response identity was not verified because the transport operation ID was not exposed or compared.

Do not change the runtime, invent another read API or resubmit. This gap does not prove a mismatch, but it prevents a “check passed” claim.

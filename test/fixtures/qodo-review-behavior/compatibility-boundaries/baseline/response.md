No commands were executed, services called, or files written. All commands below are proposals; `qodo` denotes the trusted, resolved installed invocation.

### 1. `old-1-6` — compatibility blocked

**Next allowed action:** Report the blocker and request explicit authorization before any runtime change.

Version **1.6.0** is below the **2.0.0** minimum. Advertised review API v2, cached catalogs and credentials do not override that executable requirement.

Do not run identity, login, managed-tool or review calls. No update is authorized. The absent update-source override removes one blocker but does not grant update permission.

**Unverified:** An approved recovery route, a successfully checked newer compatible 2.x target, and compatibility after any authorized update. Preserve the existing deployment and update policy.

### 2. `unparseable` — compatibility unknown

**Next allowed action:** Report that `"custom build"` cannot establish compatibility. Before recovery, establish only whether `QODO_UPDATE_BASE_URL` is set—never disclose its value. If set, stop for the user.

Do not attempt identity, login, catalog refresh or review. Nothing indicates an authentication problem.

An unparseable runtime requires a separately authorized, Qodo/organization-supplied checksum-pinned installer route. Neither approval nor a verified artifact/checksum exists, so no installation command is appropriate.

**Unverified:** The executable version, compatibility, override presence and an authorized installation route.

### 3. `floor-2-0-summary` — eligible for first submission

Exactly **2.0.0** meets the executable floor; API v2 and identity are verified. Use the advertised older `summary` field without losing context.

Proposed context, prepared outside the reviewed diff as UTF-8 without a BOM:

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

After preparing that file at the proposed temporary path:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "${TMPDIR:?}/floor-2-0-summary.json" \
  --async --json
```

Omitting `--fast` and `--deep` selects auto effort. Retain the returned operation ID and collect that operation; acceptance is not completion.

**Unverified:** Review completion, collected scope/omissions, complete coverage and inventory, findings, and context delivery. Live load remains untested.

### 4. `current-2-3-1-paths` — scoped continuation

**Next allowed action:** Confirm any submission flags not already verified using offline `qodo review --help`, then submit the changed work once. New code provides the reason for another assessment.

Preserve this context outside the reviewed diff:

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

Proposed submission, once the displayed options are confirmed:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "${TMPDIR:?}/current-2-3-1-paths.json" \
  --async --json \
  src/jobs/ test/jobs/
```

Keep the same base, explicit paths and auto effort. Do **not** add `--full` because notes changed. Preserve both recent-work entries; this includes added behavior, not just a fix.

**Unverified:** Whether the Engine selects full, incremental or reused assessment; actual coverage, context delivery and findings. Report its returned decision rather than promising reuse. This remains path-limited coverage, not repository-wide certification.

### 5. `mcp-no-collector` — worktree coverage blocked

**Next allowed action:** Report that MCP-only local review cannot safely cover this worktree without a tested collector.

Do not submit `start-pre-pr-review`, invent prepared input, substitute an ad hoc diff or fetch another checkout. The server schema cannot read the local worktree. Installation is not authorized.

**Missing prerequisites:** A tested collector providing the intended scope, safety exclusions, omission reporting, a fetchable base, and retained snapshot/context. No worktree review has been completed.

### 6. `cli-identity-gap` — operation binding unverified

**No—you cannot claim the operation-response identity check passed.**

Known evidence:

- Collection requested **`OP-REQUESTED`**.
- The returned assessment reports complete coverage and inventory with no findings.
- Its snapshot matches the intended base, commit and tree.
- Its review-run ID is **`REVIEW-RESULT`**.

The response exposes no transport operation ID, and the trusted renderer explicitly does not compare that hidden ID with the requested one. `REVIEW-RESULT` is a different kind of identifier; it cannot substitute for `OP-REQUESTED`. Snapshot agreement does not prove transport-operation identity.

**Next allowed action:** Retain and report the existing evidence and this verification gap. No runtime change, invented read API or new submission is justified.

The identity check is **unverified**, not proven failed. A completed matching-snapshot assessment is available, but fully verified attribution to the accepted operation—and overall readiness—cannot be claimed from this evidence alone.

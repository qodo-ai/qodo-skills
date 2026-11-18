All commands and context below are **proposals only**. Nothing was executed, installed or written. `qodo` denotes the same trusted installed invocation used for each fixture’s version probe.

## 1. `old-1-6`

**Blocked:** CLI 1.6.0 is below the required 2.0.0 floor, despite this deployment advertising review API v2.

- Do not run identity, login, review or managed-tool calls. Cached credentials/catalogs do not establish compatibility.
- The update-source override is already known absent. Next, request approval for a specific recovery route; do not update automatically.
- Any approved updater route must first successfully offer a newer compatible 2.x target, preserving origin, version policy and holds. Do not automatically select `latest-2`.
- After one approved runtime attempt, repeat the unadorned version probe before proceeding.

**Unverified:** a supported executable and any review assessment.

## 2. `unparseable`

**Blocked:** `"custom build"` does not establish a supported version. This is not evidence of an authentication problem; do not log in or make authenticated calls.

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for the user. If absent, recovery requires separate installation approval and a Qodo/organization-supplied checksum-pinned installer. Neither is available, so no installation command can yet be proposed safely.

After one authorized attempt, probe the version again. Do not invent a checksum, switch deployments or try speculative updater routes.

**Unverified:** executable version, compatibility, identity and review coverage.

## 3. `floor-2-0-summary`

**Next:** prepare the following context outside the reviewed worktree, then submit the first review. CLI 2.0.0 meets the floor; API v2 and identity are already verified.

Proposed `floor-2-0-summary.json`:

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

Only the narrative field changes from `notes` to advertised `summary`; no accepted detail is removed.

After preparing that file at the proposed external location:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$HOME/.qodo/review-context/floor-2-0-summary.json" --async --json
```

Effort is **auto**, with neither depth flag.

**Unverified:** submission acceptance, context delivery, completed coverage and findings. Live-load behavior remains untested.

## 4. `current-2-3-1-paths`

**Next:** submit changed work with the unchanged base, explicit paths and auto effort. Use the advertised `notes` field.

Proposed `current-2-3-1-paths.json`:

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

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$HOME/.qodo/review-context/current-2-3-1-paths.json" --async --json src/jobs/ test/jobs/
```

Do **not** add `--full`. Changed notes alone do not invalidate reuse; the Engine determines actual continuation eligibility and mode. Recent work includes new API behavior, not merely fixes.

**Unverified:** actual reuse mode, context delivery, findings and coverage of the changed snapshot. These path restrictions do not establish coverage outside the two directories.

For either accepted submission above, retain its returned operation ID and poll that operation—not a new review. Acceptance is not completion.

## 5. `mcp-no-collector`

**Review blocked:** the MCP schema cannot read this worktree. No safe submission can be assembled without a tested collector and prepared input.

Proceed only when collection can preserve the intended scope, safety exclusions, omission reporting, fetchable base, submitted snapshot and context. Do not substitute an ad hoc `git diff`, another checkout or a remotely fetched repository. Installation is not authorized.

Skip CLI preflight on this MCP-only path.

**Unverified:** local-input completeness, exclusions, omissions, base availability and all review results.

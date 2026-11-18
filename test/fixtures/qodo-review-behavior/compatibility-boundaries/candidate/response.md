Proposals only; no commands executed, files written or services called. Below, `qodo` means the trusted installed invocation, never a repository-local launcher.

### 1. `old-1-6`

**Blocked:** 1.6.0 is below the required CLI 2.0.0 floor. Review API v2 does not override that requirement.

Stop before identity, login, review or managed-tool calls. The update-source override is already known absent. Obtain authorization for one recovery route that preserves the recorded origin and update policy.

For an approved updater route, inspect its supported check first. Proceed only if that check successfully offers a newer compatible 2.x target. Do not automatically select `latest-2`, change deployment or install anything. After one approved runtime attempt, repeat the unadorned version probe.

**Unverified:** eligible update route/target, replacement runtime compatibility, identity and review coverage.

### 2. `unparseable`

**Blocked:** `"custom build"` does not establish compatibility. It is not evidence of missing credentials; do not attempt login.

The next permitted local diagnostic is checking **only whether** `QODO_UPDATE_BASE_URL` is set, without displaying its value. If set, stop for the user.

An unparseable runtime requires the separately authorized, Qodo/organization-supplied checksum-pinned installer route. Neither approval nor a verified checksum exists, so propose no installation or updater execution.

**Unverified:** override presence, executable version, approved installer provenance/checksum and review compatibility.

### 3. `floor-2-0-summary`

**Allowed:** exactly 2.0.0 meets the floor; API v2 and identity are already verified. No redundant identity check is needed.

Reason for submission: the coherent tested slice awaits its first review.

Proposed context—rename only the narrative field to the advertised `summary`:

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

After preparing this complete UTF-8, BOM-free JSON outside the reviewed worktree and setting `QODO_REVIEW_CONTEXT` to its path:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$QODO_REVIEW_CONTEXT" --async --json
```

Effort is **auto**, with neither `--fast` nor `--deep`.

**Unverified:** submission acceptance, reviewed snapshot/scope, exclusions, context delivery, inventory and coverage. Live load remains untested. Retain any accepted operation ID and collect that operation rather than submitting again.

### 4. `current-2-3-1-paths`

**Allowed:** submit a continuation because new code awaits review. Preserve the exact base, explicit paths and auto effort.

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

After preparing this case’s external context file and setting `QODO_REVIEW_CONTEXT` accordingly:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$QODO_REVIEW_CONTEXT" --async --json src/jobs/ test/jobs/
```

Do **not** add `--full` merely because notes changed. Do not describe this as fixes-only: it includes new cancellation API behavior. The Engine decides continuation eligibility and reports actual `full`, `incremental` or `reused` behavior; reuse is not guaranteed.

**Unverified:** acceptance, actual analysis mode/fallback, context delivery and coverage of the new snapshot. Any resulting coverage remains limited to the two requested paths.

### 5. `mcp-no-collector`

**Review blocked:** the MCP schema accepts prepared inputs; it cannot collect this worktree itself.

Do not submit an ad hoc `git diff`, substitute another checkout or remotely fetched repository, or install the CLI without authorization. MCP does not require CLI version or identity probes.

The next step is obtaining suitable prepared input from a tested collector that preserves intended scope, safety exclusions, omitted-file reporting, a fetchable base, and retained snapshot/context.

**Unverified:** all local collection and review coverage. Schema availability alone establishes none of it.

### 6. `cli-identity-gap`

**No—the operation-response identity check cannot be claimed passed.**

Known evidence:

- The retained requested operation is `OP-REQUESTED`.
- Qodo’s returned result reports complete coverage and inventory, with no findings.
- The returned snapshot matches the intended base, commit and tree.
- `REVIEW-RESULT` is a review-run ID, not a returned transport operation ID.

The returned transport operation ID is absent, and the renderer does not compare it internally. Consequently, the operation-response identity comparison is **unavailable/unverified**. Matching snapshot metadata does not establish that separate check.

Retain the handle and result, and report the gap explicitly. Do not substitute either known ID for the missing returned ID, change runtimes, invent another read API or submit again. This is missing verification evidence—not proof of a mismatch, and not grounds for an unqualified clean/ready claim.

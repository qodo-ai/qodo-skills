All commands below are **proposals only**. `qodo` denotes the retained trusted installed invocation. No commands, installation changes or writes were performed.

### 1. `old-1-6` — blocked by executable version

Version **1.6.0** is below the required **2.0.0**, even though the deployment advertises review API v2. Cached credentials or catalogs do not establish compatibility.

**Next allowed action:** report the blocker and obtain explicit approval for a supported compatibility-recovery route. The absent update-source override does not authorize an update.

Do not run identity, login, review or managed-tool calls. Before an authorized updater attempt, its supported check must offer a newer compatible 2.x target at the recorded origin. Make at most one approved attempt, then repeat the unadorned version probe.

**Unverified:** a suitable update target, recovery authorization, compatible executable, identity and review coverage.

### 2. `unparseable` — compatibility unknown

`custom build` does not establish a supported executable version. This is **not evidence of an authentication problem**; do not attempt login.

**Next allowed action:** obtain a verified version or separately authorized, organization-supplied checksum-pinned installer recovery. Before recovery, check only whether `QODO_UPDATE_BASE_URL` is set—not its value. If set, stop for the user.

No installer command is justified without approval and the supplied artifact/checksum procedure. Do not invent a digest or try updater routes speculatively.

**Unverified:** executable compatibility, recovery prerequisites, identity and review coverage.

### 3. `floor-2-0-summary` — first review may proceed

Exactly **2.0.0** meets the inclusive minimum. Review API v2 and identity are already verified; no update or repeated identity check is needed.

Proposed context, preserving the accepted content and changing only `notes` to the advertised `summary` field:

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

After preparing that complete UTF-8, BOM-free file outside the reviewed worktree and binding `QODO_REVIEW_CONTEXT` to its path:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$QODO_REVIEW_CONTEXT" --async --json
```

This uses **auto effort**, with neither `--fast` nor `--deep`.

**Unverified:** submission acceptance, completed coverage and inventory, findings, context-delivery metadata and persistence. Cancellation tests passed; live-load behavior remains untested.

### 4. `current-2-3-1-paths` — preserve the continuation scope

**Next allowed action:** submit the changed slice with the previous review’s exact base, auto effort and both positional paths:

```text
src/jobs/ test/jobs/
```

Retain `--context-file`, `--async` and `--json`. Do **not** add `--full`: changed notes alone do not invalidate reuse. The new code supplies the reason for another assessment.

Use this context:

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

Case 4 does not state the retained base’s literal SHA, so do not invent one or automatically borrow case 3’s base. Use the exact retained value when constructing the submission.

**Unverified:** whether the Engine returns `incremental`, `reused` or a full fallback, plus actual coverage and context delivery. Do not promise reuse or classify this work as fixes-only; it includes new cancellation behavior.

For either submission, retain the accepted operation ID and collect that operation at the advertised interval. Acceptance is not completion; do not resubmit to obtain its result.

### 5. `mcp-no-collector` — worktree coverage blocked

The exposed MCP schema cannot itself read this worktree. Without a tested local collector or prepared input, **do not submit a review**.

**Next allowed action:** report the collection blocker. Resume only when a tested collector is available that preserves the intended scope, safety exclusions, omission report, fetchable base, submitted snapshot and context—or when a CLI installation path is separately authorized.

Do not substitute an ad hoc `git diff`, another checkout or a remotely fetched repository.

**Unverified:** safe input collection and all review coverage. No review-completion claim is supported.

### 6. `cli-identity-gap` — identity check remains unverified

**No, you cannot claim that the operation-response identity check passed.**

Known evidence:

- The status request addressed `OP-REQUESTED`.
- Qodo’s returned result reports complete coverage and inventory with no findings.
- Its snapshot matches the intended base, commit and tree.
- It identifies review run `REVIEW-RESULT`.

The gap is that the response exposes no transport operation ID, and the trusted renderer does not compare the hidden ID against `OP-REQUESTED`. A review-run ID is not an operation ID, and snapshot equality does not prove operation identity.

**Next allowed action:** retain the result and report:

> The returned assessment reports complete coverage, complete inventory and no findings for the matching snapshot. Its binding to accepted operation `OP-REQUESTED` remains unverified.

This is **missing verification, not a proven mismatch**. Do not change the runtime, invent another read API or submit another review to manufacture that evidence.

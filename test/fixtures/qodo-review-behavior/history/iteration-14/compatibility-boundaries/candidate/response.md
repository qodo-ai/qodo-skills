Proposals only; no commands, services or writes performed. In examples, `qodo` means the retained trusted installed invocation, never a repository-local launcher.

### 1. `old-1-6` — blocked by the CLI version

**Next allowed action:** request approval for a specific compatible runtime recovery route. CLI **1.6.0 is below the 2.0.0 minimum**, even though this deployment advertises review API v2.

Do not run identity, login, reviews or managed tools. The update-source override is already known absent. Preserve the recorded origin, version selections and update holds.

Any selected updater route must first successfully offer a newer compatible **2.x** target. Only then may an approved update occur, once, followed by an unadorned version probe. A failed check, unavailable target or failed attempt stops recovery; do not switch routes.

**Unverified:** a supported executable, approved update target and review coverage. Cached credentials or catalog data do not establish executable compatibility.

### 2. `unparseable` — compatibility unknown

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for the user.

“custom build” does not establish a supported version. Do not run identity, login, reviews or managed tools, and do not infer an authentication problem.

For this unparseable runtime, recovery requires separate authorization and a Qodo/organization-supplied checksum-pinned installer for a verified compatible target. Neither is available. No installation command is presently justified. After an authorized, checksum-verified attempt, repeat the unadorned version probe; stop if incompatible.

**Unverified:** runtime version, override presence, installer integrity and review coverage.

### 3. `floor-2-0-summary` — eligible for its first review

Exactly **2.0.0 meets the minimum**; API v2, identity and the required flags are verified. Prepare this complete UTF-8 context without a BOM, outside the reviewed worktree. The example uses `$TMPDIR/qodo-review-floor-context.json`:

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

Only the narrative field changes from `notes` to `summary`; no accepted detail is dropped.

**Proposed submission:**

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-floor-context.json" --async --json
```

Omitting depth flags selects **auto**. Retain the returned operation ID and collect that operation, rather than resubmitting.

**Unverified:** acceptance, completed coverage, findings and context delivery. Live-load behavior remains untested.

### 4. `current-2-3-1-paths` — preserve incremental eligibility and scope

**Next allowed action:** review the changed code with refreshed context. New code warrants assessment; changed notes alone do not require `--full`. Let the Engine determine continuation eligibility.

Proposed context at `$TMPDIR/qodo-review-path-context.json`, outside the reviewed worktree:

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

Confirm any remaining command options with offline `qodo review --help`, then:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/qodo-review-path-context.json" --async --json src/jobs/ test/jobs/
```

Keep **auto**, both explicit paths and the same base. Do not add `--full`. This includes new API behavior, not merely fixes.

**Unverified:** actual `full`/`incremental`/`reused` mode, resulting coverage, findings and context delivery. Path-limited coverage cannot certify files outside those paths.

### 5. `mcp-no-collector` — worktree review blocked

**Next allowed action:** report the collection blocker and stop before submission.

The MCP schema cannot read this worktree. Proceeding requires a tested collector that preserves the intended scope, applies safety exclusions, reports omissions, verifies a fetchable base and retains the submitted snapshot/context.

Do not substitute an ad hoc `git diff`, another checkout or remotely fetched repository. Do not install a CLI without authorization. CLI version and identity probes are not required for the MCP path.

**Unverified:** safely collected input and all review coverage. No submission is justified.

### 6. `cli-identity-gap` — identity comparison unavailable

**No, you cannot claim that the operation-response identity check passed.**

Known evidence:

- Status was requested for retained operation `OP-REQUESTED`.
- The returned artifact reports completed coverage, complete inventory and no findings.
- `meta.run.snapshot` matches the intended base, commit and tree.
- The returned review-run ID is `REVIEW-RESULT`.

The missing evidence is the **returned transport operation ID**. The renderer does not compare that hidden ID with `OP-REQUESTED`. Matching snapshot metadata does not establish this separate comparison, and `REVIEW-RESULT` is not a substitute.

**Next allowed action:** preserve and report the result with that limitation:

> Qodo’s returned assessment reports complete coverage and inventory with no findings, and its snapshot metadata matches the intended snapshot. Operation-response identity verification remains unavailable.

Do not claim fully verified readiness, change runtimes, invent another read API or submit again.

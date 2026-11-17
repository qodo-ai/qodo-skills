All commands below are proposals only. `qodo` denotes the trusted, resolved installed executable, not a repository-local launcher. Proposed context files must remain outside the reviewed worktree.

### 1. `old-1-6` — blocked

CLI **1.6.0 is below the required 2.0.0 floor**, even though the deployment advertises review API v2. Cached credentials or catalog data do not establish compatibility.

**Next allowed action:** request authorization for one bounded, same-origin compatibility-recovery route. No update is currently authorized. Before any approved updater attempt, its supported check must offer a newer compatible 2.x target. Preserve deployment origin, version choices and update holds; reprobe after the single approved attempt.

Do not run identity, login, review or managed-tool commands.

**Unverified:** a supported executable, identity and review coverage.

### 2. `unparseable` — blocked

`custom build` does not establish a supported CLI version. There is no evidence of an authentication problem, so login is not justified.

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for the user. Otherwise, compatibility still requires a verifiable installed runtime or a separately authorized, organization-supplied checksum-pinned installer route.

No updater or installer attempt is justified with the supplied evidence.

**Unverified:** executable version, runtime compatibility, installer integrity, identity and review coverage.

### 3. `floor-2-0-summary` — eligible for first review

Exactly **2.0.0 satisfies the CLI floor**. API v2, identity and the required flags are verified; no update is needed.

Proposed `floor-2-0-summary.context.json`:

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

Only the narrative field changes from `notes` to the advertised `summary`; no accepted content is dropped.

**Next allowed submission**, after preparing that external context file:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/floor-2-0-summary.context.json" --async --json
```

This uses auto effort by omitting `--fast` and `--deep`. The reason for submission is the coherent tested slice awaiting its first assessment.

**Unverified:** assessment completion, findings, coverage, exclusions and context delivery. Live-load behavior remains explicitly untested.

### 4. `current-2-3-1-paths` — eligible for scoped continuation

Preserve the same base, auto effort and both explicit paths. Changed notes alone do not require `--full`; the Engine determines actual reuse eligibility.

Proposed `current-2-3-1-paths.context.json`:

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

If transport/path flags have not already been confirmed, inspect offline help first:

```sh
qodo review --help
```

With those flags confirmed, the proposed submission is:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$TMPDIR/current-2-3-1-paths.context.json" --async --json src/jobs/ test/jobs/
```

The reason for another assessment is changed code—not merely changed notes. Do not add `--full` or describe the round as fixes-only: it includes new cancellation API behavior.

**Unverified:** current assessment, actual `full`/`incremental`/`reused` outcome, findings and context delivery. Coverage remains restricted to the two requested paths, not the entire repository.

For cases 3–4, retain any accepted operation ID and poll that existing operation. Acceptance is not completion; inspect the complete finding inventory and coverage warnings before reporting readiness.

### 5. `mcp-no-collector` — coverage blocked

The MCP schema cannot read this worktree. Without a tested collector or prepared input, **do not submit a review**.

**Next allowed action:** report the blocker. Proceed only when a tested collector can preserve the intended snapshot and context, apply safety exclusions, report omissions and verify a fetchable comparison base.

Do not substitute an ad hoc `git diff`, another checkout or remotely fetched repository. CLI installation requires separate authorization; MCP use does not require CLI preflight.

**Unverified:** collected scope, exclusions, omissions, base availability and all review results.

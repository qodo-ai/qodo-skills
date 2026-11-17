## 1. `old-1-6` — Review blocked

CLI **1.6.0 fails the minimum 2.0.0 requirement**, even though this deployment advertises review API v2. Cached credentials or a catalog do not override that gate.

**Next allowed action:** request approval for bounded runtime recovery. The update-source override is already known absent; do not inspect its value or run identity, login, review or managed-tool calls.

Before any approved updater attempt, its supported check must successfully offer a newer compatible **2.x** target. Preserve origin, version choices and update holds. Do not automatically select `latest-2`; it requires a selected, verified same-origin legacy route. Permit one approved runtime attempt, then repeat the unadorned version probe.

**Unverified:** a suitable update target, compatible replacement runtime, identity and review coverage.

## 2. `unparseable` — Review blocked

`custom build` does not establish a compatible version.

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for user direction. Otherwise, recovery still requires separate approval and a Qodo/organization-supplied checksum-pinned installer, because the runtime version cannot be parsed. Neither approval nor a verified installer is available.

Do not run identity, login, review or managed tools. Nothing here establishes an authentication problem.

**Unverified:** runtime compatibility, recovery artifact/checksum, identity and review coverage.

## 3. `floor-2-0-summary` — Eligible for submission

Exactly **2.0.0 meets the version floor**. API v2 and identity are already verified; no upgrade or repeated identity check is needed.

Use this proposed context, changing only the narrative field name to `summary`:

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

After preparing that JSON as a UTF-8, BOM-free context file outside the checkout, the proposed command is:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "${TMPDIR:?}/qodo-review-floor-2-0-summary.json" --async --json
```

Here and below, `qodo` means the same resolved installed invocation used for that case’s probe—not a repository-local launcher. These commands have not been executed, and the context files have not been created.

Omit effort flags for **auto**. The slice contains both a correction and new cancellation behavior; do not describe it as fixes-only.

**Unverified:** submission acceptance, completed assessment, finding inventory, coverage and context-delivery metadata. Live load remains explicitly untested.

## 4. `current-2-3-1-paths` — Eligible for scoped continuation

The changed code supplies a reason for another assessment. Preserve the same base, **auto** effort and both explicit paths. Changed notes alone do not justify forcing a full assessment; let the Engine determine reuse or incremental eligibility.

Use:

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

Confirm any remaining submission flags through offline `qodo review --help`. If supported, the proposed submission is:

```sh
qodo review --base 1111111111111111111111111111111111111111 src/jobs/ test/jobs/ --context-file "${TMPDIR:?}/qodo-review-current-2-3-1-paths.json" --async --json
```

Do **not** add `--full`, `--fast` or `--deep`.

**Unverified:** the Engine’s actual reuse decision and coverage of the new snapshot. Prior complete coverage does not certify these new changes, and this scoped review cannot certify paths outside `src/jobs/` and `test/jobs/`.

For either accepted CLI submission, retain its returned operation ID and collect that operation with `qodo review status <returned-operation-id> --json`, respecting returned delays. Acceptance is not a completed review.

## 5. `mcp-no-collector` — Review blocked

The MCP schema cannot read this worktree. Without a tested local collector or prepared input, **do not submit a review**.

**Next allowed action:** report the collection blocker. Proceed only when a tested collector can preserve the intended scope, apply safety exclusions, report omissions, verify a fetchable base and retain the submitted snapshot and context.

Do not substitute an ad hoc `git diff`, another checkout or a remotely fetched repository. Installation is not authorized. MCP does not require CLI preflight.

**Unverified:** collected worktree input, exclusions, omissions, base fetchability and all review coverage.

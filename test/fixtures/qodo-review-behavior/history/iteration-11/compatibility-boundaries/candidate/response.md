These are fixture-based proposals only. Nothing was executed or changed. In commands, `qodo` means the trusted installed invocation, never a repository-local launcher.

### 1. `old-1-6` — blocked by CLI version

CLI **1.6.0** fails the **2.0.0 minimum**, even though the deployment advertises review API v2. Cached credentials or catalogs do not establish compatibility.

- **Next allowed action:** request scoped approval for runtime recovery. The update-source override is already known to be absent.
- Do not run identity, login, review or managed-tool calls.
- No runtime-changing command is authorized. Any approved updater route must first successfully offer a newer compatible 2.x target, preserve the recorded origin and update holds, and make at most one approved attempt followed by an unadorned version probe. Do not assume `latest-2` is the selected route.
- **Unverified:** supported recovery route, offered target, resulting compatibility, identity and review coverage.

### 2. `unparseable` — compatibility unknown

`custom build` does not establish a supported version. This is not evidence of an authentication problem.

- **Next allowed diagnostic:** determine only whether `QODO_UPDATE_BASE_URL` is set; never expose its value. If set, stop for the user.
- Otherwise, recovery requires a separately authorized, organization/Qodo-supplied checksum-pinned installer. No approval, artifact or verified checksum exists, so no installation command can be proposed safely.
- Do not attempt login, identity, review, a blind update or a generic installer.
- **Unverified:** runtime version, override presence, installer provenance/checksum, compatibility and review coverage.

### 3. `floor-2-0-summary` — eligible for first review

Exactly **2.0.0**, verified API v2 and verified identity satisfy the gate. No runtime update or repeated identity check is needed.

**Next allowed action:** prepare this context in a UTF-8 file without a BOM, outside reviewed changes. Use `summary` because that is the advertised narrative field; preserve everything else:

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

After setting `CONTEXT_FILE` to that prepared file, propose:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_FILE" --async --json
```

This requests **auto effort**, with neither `--fast` nor `--deep`.

**Unverified:** submission acceptance, actual collected snapshot, omissions, context delivery, findings and completed coverage. The fixture establishes that cancellation tests passed—not that live load was tested.

### 4. `current-2-3-1-paths` — preserve scoped continuation

**2.3.1** satisfies the version floor; API v2 and identity are verified.

**Reason for another assessment:** the timeout correction and new cancellation API behavior await review. Changed notes alone do not require `--full`, and this is not automatically a fixes-only round.

Prepare a separate external context file:

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

Confirm any submission flags not already verified through offline `qodo review --help`. With support confirmed, propose:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CONTEXT_FILE" --async --json src/jobs/ test/jobs/
```

Keep the same base, explicit paths and auto effort. **Do not add `--full`.** Let the Engine determine continuation eligibility and report its actual `full`, `incremental` or `reused` outcome.

**Unverified:** coverage of the new snapshot, actual reuse outcome, context delivery and findings. Prior complete coverage does not certify subsequent changes. This remains path-limited coverage, not certification of files outside those paths.

For either accepted CLI submission, retain its returned operation ID with the snapshot, base, scope and context. Collect using:

```sh
qodo review status <returned-operation-id> --json
```

Respect the returned polling delay. Acceptance is not completion; inspect coverage, omissions, context receipts and the complete finding inventory before claiming readiness.

### 5. `mcp-no-collector` — worktree coverage blocked

The MCP schema cannot read this worktree. Without a tested collector or prepared input, **do not submit a review**.

- **Next allowed action:** obtain a tested collector and prepared input matching the intended scope, preserving safety exclusions, reporting omissions, verifying a fetchable base, and retaining the submitted snapshot and context.
- Do not substitute an ad hoc `git diff`, unrelated checkout or remotely fetched repository.
- Do not install a CLI without authorization. MCP use does not require CLI version or identity probes.
- **Unverified:** local collection safety, snapshot identity, base availability and all requested review coverage. No worktree assessment has completed.

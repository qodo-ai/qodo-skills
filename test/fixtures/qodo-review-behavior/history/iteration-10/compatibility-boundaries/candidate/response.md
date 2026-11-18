Nothing was executed or changed. Below, `qodo` means the same trusted installed invocation used for the version probe, never a repository-local launcher.

### 1. `old-1-6` — blocked by the executable version

**1.6.0 is unsupported**, even though this deployment advertises review API v2. Cached credentials or catalogs do not bypass the **2.0.0 minimum**.

The next allowed diagnostic is offline updater-help inspection:

```sh
qodo update --help
```

No update is authorized. Before any runtime change, obtain approval for one recovery route at the recorded origin, preserving version selections and update holds. Every updater route requires a successful supported check offering a newer compatible **2.x** target. Do not assume `latest-2` is available or approved.

Do not run identity, login, review or managed-tool calls.

**Unverified:** supported recovery route, compatible target, identity and review coverage. The override is already known to be absent.

### 2. `unparseable` — compatibility unknown

`custom build` establishes no supported version. It is not evidence of missing credentials; **do not attempt login** or authenticated calls.

Next, determine only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for the user. Otherwise, recovery still requires a separately authorized Qodo/organization-supplied installer and checksum-verification procedure. Neither approval nor a verified checksum exists here, so no installer command can safely be proposed.

After one authorized installation attempt, repeat the same invocation’s unadorned `--version` probe. Failure or incompatibility stops recovery.

**Unverified:** version, review capability, installer provenance and identity.

### 3. `floor-2-0-summary` — compatible; preserve context using `summary`

Exactly **2.0.0 meets the floor**. API v2, identity and the required flags are verified; no update or repeat identity check is needed.

Proposed context:

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

Only the narrative field name changes from `notes` to `summary`; no accepted detail is dropped.

After preparing that JSON as a UTF-8, BOM-free file outside the reviewed worktree, the proposed submission is:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "${TMPDIR:?}/floor-2-0-summary-context.json" \
  --async --json
```

Use that path only after preparing the file there and confirming `$TMPDIR` is outside the worktree. Omit effort flags for **auto**.

**Unverified:** submission acceptance, actual collected coverage, context delivery and findings. The fixture reports cancellation tests passed; live-load behavior remains untested.

### 4. `current-2-3-1-paths` — review changed work without forcing full

**2.3.1 is compatible**, and identity is verified. Changed code supplies the reason for another assessment—not the notes change alone.

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

Confirm submission flags with offline help:

```sh
qodo review --help
```

If the illustrated flags are supported, after preparing the external context file:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "${TMPDIR:?}/current-2-3-1-paths-context.json" \
  --async --json \
  src/jobs/ test/jobs/
```

Preserve both paths, the base and auto effort. **Do not add `--full`.** Let the Engine determine and report incremental, reused or full execution. This work includes new cancellation behavior, so it is not automatically fixes-only.

**Unverified:** continuation mode, current-snapshot coverage, context delivery and findings. Coverage remains deliberately limited to the two requested paths.

For either accepted CLI submission, retain its operation ID and collect that operation:

```sh
qodo review status <returned-operation-id> --json
```

Acceptance is not completion. Verify result identity, omissions, coverage and the complete finding inventory before making a readiness claim.

### 5. `mcp-no-collector` — review blocked

The MCP schema cannot read this worktree. Without a tested collector or suitable prepared input, **do not submit a review**.

Report the coverage blocker. A suitable collector must preserve the intended snapshot and context, apply safety exclusions, report omissions and verify a fetchable comparison base. An ad hoc `git diff`, unrelated checkout or remotely fetched substitute is not equivalent.

Do not install a CLI without authorization, and skip CLI version/identity probes on this MCP-only path.

**Unverified:** the collected diff, exclusions, omissions, base fetchability and all review results.

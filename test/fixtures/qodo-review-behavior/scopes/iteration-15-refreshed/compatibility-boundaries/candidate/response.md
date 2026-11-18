No commands were executed, installations changed, or files written. Below, `qodo` means the resolved installed invocation—not a repository-local launcher. Context-file paths are proposed locations outside the reviewed worktree.

### 1. `old-1-6` — blocked by the CLI version floor

CLI **1.6.0 is unsupported**; deployment review API v2, cached catalogs and credentials do not override the **2.0.0 minimum**.

**Next action:** request runtime-update approval. Do not run identity, login, reviews or managed tools.

The update-source override is already known to be absent. If recovery is authorized, preserve the recorded origin and update holds, select one supported route, and require a successful check offering a newer compatible 2.x target before changing anything. `latest-2` is not an automatic fallback. Allow one approved runtime attempt, then repeat the unadorned version probe.

**Unverified:** availability of a compatible update target and successful recovery. No review has occurred.

### 2. `unparseable` — compatibility unknown

`custom build` does not establish a supported version. This is **not evidence of missing credentials**; do not attempt login or authenticated calls.

**Next action:** check only whether `QODO_UPDATE_BASE_URL` is set, without revealing its value. If set, stop for user guidance. Obtain trustworthy version evidence; if compatibility cannot be established, recovery requires separately authorized installation using a Qodo/organization-supplied artifact and checksum-verification procedure.

No installer command is justified by the supplied evidence. Do not invent a checksum or try an updater route speculatively.

**Unverified:** CLI compatibility, override presence and any authorized recovery artifact. No review has occurred.

### 3. `floor-2-0-summary` — compatible; propose the first review

Exactly **2.0.0 meets the floor**. API v2 and identity are verified; no update or repeated identity check is needed.

Proposed complete UTF-8 context file, outside the reviewed worktree:

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

Use `summary` only for the narrative; retain both other fields unchanged.

**Proposed submission**, after preparing that file at the indicated external path:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file /absolute/path/outside-worktree/review-context-summary.json --async --json
```

This uses **auto effort**, without `--fast` or `--deep`.

**Unverified:** acceptance, actual coverage, findings and context delivery/consumption. Cancellation tests passed; live load remains untested.

### 4. `current-2-3-1-paths` — preserve scope and permit continuation

**Next action:** submit the changed work with the retained base, explicit paths and auto effort. Confirm submission flags in installed help if not already established:

```sh
qodo review --help
```

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

With async/context-file flags confirmed:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file /absolute/path/outside-worktree/review-context-notes.json --async --json src/jobs/ test/jobs/
```

Do **not** add `--full`: changed notes alone do not invalidate reuse. The recent work includes both a correction and added behavior; do not label it fixes-only. The Engine determines continuation eligibility.

**Unverified:** actual execution mode (`full`, `incremental` or `reused`), new coverage, findings and context delivery. Any resulting coverage remains limited to the two requested paths.

For cases 3–4, retain the returned operation ID with base, snapshot, scope and context, then collect that same operation. Acceptance alone is not completion.

### 5. `mcp-no-collector` — worktree coverage blocked

The MCP schema cannot read this worktree. **Do not submit a review.**

**Next action:** report the missing tested collector. Resumption requires prepared input from a collector that preserves the intended scope and safety exclusions, reports omissions, verifies a fetchable base, and retains snapshot/context identity.

Do not substitute an ad hoc `git diff`, another checkout or a remotely fetched repository. Installation is not authorized; skip CLI preflight.

**Unverified:** all worktree review coverage. No review has occurred.

### 6. `cli-identity-gap` — identity comparison unavailable

**No, you cannot claim the operation-response identity check passed.**

Known evidence:

- Status was requested for retained operation `OP-REQUESTED`.
- The returned assessment reports complete coverage/inventory and no findings.
- `meta.run.snapshot` matches the intended base, commit and tree.
- The result exposes review-run ID `REVIEW-RESULT`.

The returned **transport operation ID is absent**, and the renderer does not compare that hidden ID against the requested handle. Neither `REVIEW-RESULT`, the requested handle itself, nor matching snapshot metadata supplies that missing comparison.

**Next action:** retain the result and report:

> Qodo’s returned assessment reports complete coverage and no findings, with matching snapshot metadata. Operation-response identity comparison remains unverified because the returned transport operation ID is unavailable.

Do not change runtimes, invent another read API or submit again to conceal this gap.

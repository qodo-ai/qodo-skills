**Proposals only. No commands, installations, reviews or writes were executed.** Below, `qodo` means the previously resolved trusted installed invocation.

### 1. `old-1-6`

**Stop before authenticated calls.** Version **1.6.0** fails the **2.0.0** minimum, even though the deployment advertises review API v2. Cached credentials/catalogs do not override this gate.

Next: request approval for one same-origin runtime recovery route. Offline `qodo update --help` may identify supported check mechanics, but no update is authorized. Any updater attempt requires a successful check offering a newer compatible **2.x** target; do not assume `latest-2` is selected or supported.

**Pending:** approved route, verified compatible target, one approved attempt and a successful post-update version probe; then identity verification. No login, review or catalog refresh now.

### 2. `unparseable`

**Stop before identity, login, review or managed-tool calls.** `"custom build"` establishes no supported version and is not evidence of an authentication problem.

Next: before recovery, check only whether `QODO_UPDATE_BASE_URL` is set—never display its value; if set, stop for the user. Recovery requires separate installation approval and a Qodo/organization-supplied checksum-pinned installer. Neither exists, so no installer command can honestly be supplied.

**Pending:** override-presence result, installation approval, verified artifact/checksum and a parseable compatible version after one authorized attempt. Do not invent a digest or try updater routes for this unparseable executable.

### 3. `floor-2-0-summary`

**Eligible to propose the first review.** Exactly **2.0.0** meets the floor; API v2, identity and required flags are verified. No update is needed.

Proposed external context file, UTF-8 without BOM, **not created**:
`/outside/review-floor-2-0-summary.json`

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

Only the narrative field changes from `notes` to advertised `summary`; no accepted detail is dropped.

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/review-floor-2-0-summary.json \
  --async --json
```

Auto effort: no `--fast`, `--deep` or `--standard`.

### 4. `current-2-3-1-paths`

**Propose continuation for the changed code**, preserving both explicit paths, the base and auto effort. Changed notes alone do not justify `--full`. The Engine determines actual incremental/reused/full behavior.

Proposed external context file, **not created**:
`/outside/review-current-2-3-1-paths.json`

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
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/review-current-2-3-1-paths.json \
  --async --json src/jobs/ test/jobs/
```

This includes a fix **and new API behavior**; do not label it fixes-only or promise reuse.

**Pending for 3–4:** submission acceptance and operation ID; collection of that same operation via `qodo review status <returned-operation-id> --json`; completed coverage, omissions, full finding inventory, context-delivery metadata and persistence evidence. Acceptance is not completion, and path-limited coverage says nothing about excluded paths. Live load remains untested.

### 5. `mcp-no-collector`

**Review blocked by collection coverage.** The MCP schema cannot read this worktree.

Next: report the blocker. Proceed only when a tested collector/prepared input supplies the intended snapshot, safety exclusions, omission report, fetchable base and retained context. Do not substitute ad hoc `git diff`, another checkout or a remote repository.

No MCP review submission, CLI preflight or installation is proposed. **Pending:** qualifying local collection and all resulting assessment evidence.

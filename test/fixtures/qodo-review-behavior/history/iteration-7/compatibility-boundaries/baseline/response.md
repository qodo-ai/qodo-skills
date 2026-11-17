Proposals only; no commands, installations, reviews or writes were performed. In commands below, `qodo` means the retained, resolved installed invocation.

### 1. `old-1-6`

**Blocked:** CLI 1.6.0 is below the required 2.0.0 floor. Deployment review API v2, cached catalogs and credentials do not override that requirement.

**Next allowed action:** request approval for one deployment-approved runtime-update route. The update-source override is already known absent.

Before any approved update, require that route’s supported check to offer a newer compatible 2.x target. Preserve the deployment origin, version choices and update holds. A failed check stops recovery; do not switch routes. After one approved attempt, repeat the unadorned `qodo --version`.

Do not run identity, login, review or managed tools now.

**Pending:** update authorization, supported route/check, successful runtime change and compatible version verification.

### 2. `unparseable`

**Blocked:** `"custom build"` does not establish compatibility and is not evidence of an authentication problem.

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without printing its value. If set, stop for the user. Otherwise, request covering installation approval and an organization/Qodo-supplied checksum-pinned installer.

Do not invent a checksum, run login, attempt an unverified updater or switch deployments. After one authorized installation attempt, repeat `qodo --version`; stop if compatibility remains unverified.

**Pending:** override presence, installation approval, trusted installer/checksum and a verified compatible runtime.

### 3. `floor-2-0-summary`

**Allowed:** 2.0.0 meets the floor; API v2 and identity are verified. Propose the first review at auto effort.

Proposed context file, outside the reviewed worktree, UTF-8 without BOM:

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

Proposed command after preparing that file:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/compat-floor-2-0.json \
  --async --json
```

Only the narrative field changes from `notes` to supported `summary`; no accepted detail is removed.

### 4. `current-2-3-1-paths`

**Allowed:** review the newly changed code while preserving the same base, both explicit paths and auto effort. Changed notes alone do not justify `--full`; let the Engine determine reuse eligibility.

Proposed external context file:

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

Proposed command:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/compat-current-2-3-1.json \
  --async --json \
  src/jobs/ test/jobs/
```

Do not add `--full`, `--fast` or `--deep`. The new cancellation API behavior must remain visible; this is not automatically fixes-only work.

**Pending for cases 3–4:** submission acceptance, returned operation ID, completed assessment, complete finding inventory, exclusions/coverage, context-delivery evidence and persistence. Actual incremental/reused/fallback behavior is also unverified. Live load remains untested.

After acceptance, collect the existing operation—not another assessment:

```sh
qodo review status <returned-operation-id> --json
```

### 5. `mcp-no-collector`

**Review blocked:** the MCP schema cannot collect this worktree. Do not call `start-pre-pr-review` with invented or incomplete input.

**Next allowed action:** report the missing collector and request a tested collector/prepared input that preserves:

- Intended worktree scope and safety exclusions.
- An omitted-files report.
- A verified fetchable comparison base.
- The submitted snapshot and context.

Do not substitute an ad hoc `git diff`, unrelated checkout or remotely fetched repository. Do not install a CLI without authorization. MCP does not require CLI preflight.

**Pending:** safe local collection and all assessment evidence. No review-completion claim is supported.

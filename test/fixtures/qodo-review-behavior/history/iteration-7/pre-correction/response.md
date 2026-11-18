All commands are **proposals only**. `qodo` means the resolved installed invocation. No commands were executed, services called, or files written.

### `old-1-6`

**Review blocked:** CLI 1.6.0 is below the required 2.0.0 floor. The deployment’s review API v2, cached catalog, or credentials cannot satisfy the executable-version gate.

- Do not run identity, login, review, or managed-tool calls.
- The source override is absent according to the fixture; do not inspect unrelated configuration.
- Ask once for covering runtime-update approval, preserving the customer deployment, recorded origin, version choices, and update holds.
- Before any authorized updater attempt, select one deployment-approved route and require its supported check to offer a newer compatible **2.x** target. A failed check, no update, or incompatible target means stop—not switch routes.
- `latest-2` is not an automatic fallback. It requires prior selection and verification of the same-origin legacy migration route.
- After one approved runtime attempt, repeat `qodo --version`; continue only if compatible.

**Unverified:** update authorization, approved route, offered target, installed replacement, identity, and review coverage. No update command is presently authorized.

### `unparseable`

**Review blocked:** `"custom build"` establishes no supported runtime version. It is not evidence of an authentication problem.

- Do not run identity, login, reviews, managed tools, or an updater against this unidentified runtime.
- The next safe diagnostic is checking **only whether** `QODO_UPDATE_BASE_URL` is set—never its value. If set, stop for user resolution.
- Recovery requires covering approval and an organization/Qodo-supplied, checksum-pinned installer for the intended deployment. Neither approval nor a verified checksum exists here, so no installer command can be proposed as executable.
- Do not invent a digest, pipe an installer into a shell, change deployments, or alter update policy.
- Following one separately authorized installation attempt, probe the resolved invocation with only `--version`.

**Unverified:** override presence, runtime version, approved installer and checksum, authorization, and all review capability. No login is warranted.

### `floor-2-0-summary`

**Submission permitted:** exactly 2.0.0 meets the floor; review API v2 and identity are verified by the fixture. Reuse that identity only within its verified execution context.

Proposed UTF-8, BOM-free context, kept outside the reviewed diff and commits:

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

Only the narrative field changes from `notes` to the advertised `summary`; no accepted detail is removed.

Proposed command:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$EXTERNAL_CONTEXT_FILE" --async --json
```

This uses **auto** effort: no `--fast`, `--deep`, or nonexistent `--standard`. It is the first assessment, so no continuation claim is made.

After acceptance, retain the returned operation ID and submitted snapshot/base/scope/context, then collect that operation:

```sh
qodo review status "$OPERATION_ID" --json
```

**Evidence limits:** fixture verification is not an installed-runtime test. No submission, acceptance, completed assessment, context-delivery receipt, finding inventory, or coverage result exists yet. Preserve the stated cancellation-test result and explicitly untested live load.

### `current-2-3-1-paths`

**Follow-up permitted:** changed code awaits review. Retain the previous base, explicit paths, and auto effort. Changed notes alone do not justify `--full`; the Engine determines whether evidence is incrementally reused.

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

Do not characterize this as fixes-only: it also adds cancellation API behavior.

Proposed command, using the retained exact comparison SHA:

```sh
qodo review --base "$PREVIOUS_BASE_SHA" --context-file "$EXTERNAL_CONTEXT_FILE" --async --json src/jobs/ test/jobs/
```

No `--full`, `--fast`, or `--deep`. Collect the returned operation rather than resubmitting to check progress.

**Evidence limits:** the previous completed assessment does not certify these new changes. Actual `full`/`incremental`/`reused` behavior, context delivery, omissions, coverage, and findings remain unknown until results arrive. Any eventual coverage claim remains limited to the two requested paths, not the whole repository.

### `mcp-no-collector`

**Review blocked:** the MCP schema does not grant access to this worktree. Do not invoke `start-pre-pr-review` without prepared input from a tested collector.

A qualifying collector must preserve intended scope and safety exclusions, report omissions, verify a fetchable base, and retain the submitted snapshot and context.

- Do not substitute an ad hoc `git diff`, unrelated checkout, remotely fetched repository, or invented collector mode.
- Do not install the CLI without authorization.
- MCP users skip CLI version, identity, and shell preflight.
- Report the collector blocker; identify a suitable existing collector or obtain explicit approval for an installation before proceeding.

**Evidence limits:** schema availability proves neither collection capability nor coverage. No worktree input, accepted operation, or assessment exists.

**Proposed actions only. No commands executed, installations changed, or files written.**

### 1. `old-1-6`

**Review blocked:** CLI 1.6.0 is below the required 2.0.0 floor. Deployment support for review API v2 does not override that requirement.

Do not run identity, login, managed tools, or review commands.

Next, identify one deployment-approved upgrade route. Read-only planning could inspect:

```sh
qodo update --help
```

If the ordinary updater supports migration from the recorded customer origin, use its advertised update check—for example, only if supported:

```sh
qodo update --check --json
```

Require a newer compatible **2.x** target before proposing installation. Explain the target and request runtime-update authorization once; none currently exists. Preserve the customer origin and update policy.

A failed check, no update, or incompatible target means stop—not try another route. Do not automatically switch to `latest-2`; that route must be selected beforehand based on the deployment’s supported recovery policy.

After one authorized update attempt, repeat:

```sh
qodo --version
```

**Unverified:** approved migration route, compatible update target, update authorization, resulting executable, identity, and review coverage. The override is already known absent.

### 2. `unparseable`

**Review blocked:** `"custom build"` establishes no compatible version. It is not evidence of an authentication problem.

Do not attempt identity, login, or review. Before recovery, determine only whether `QODO_UPDATE_BASE_URL` is set; never print its value. If set, stop for the user to resolve it.

For this unparseable runtime, request an organization-supplied, checksum-pinned installer and covering installation approval. No executable installation command can honestly be supplied from the fixture: the approved artifact and checksum are missing. Do not invent them, pipe an installer into a shell, or substitute a public deployment.

Allow one authorized installation attempt, followed by an unadorned version probe using the resolved installed invocation. Continue only after compatibility is established.

**Unverified:** version, approved installer and checksum, installation authority, source-override status, identity, and all review coverage.

### 3. `floor-2-0-summary`

**Allowed:** CLI 2.0.0 meets the floor; API v2 and identity are verified. Reuse those checks for this invocation.

Propose a task-owned context file outside the reviewed diff and commits, encoded as complete UTF-8 without a BOM. Let `$CTX20` identify it:

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

Only the narrative field changes from `notes` to the advertised `summary`. Preserve the ownership statement and both recent-work entries. This includes new API behavior, not merely fixes.

**Submission reason:** the coherent, tested slice awaits its first assessment.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$CTX20" --async --json
```

Use auto effort: no `--fast`, `--deep`, or unnecessary `--full`.

Retain the accepted operation ID, submitted snapshot, base, scope, and context. Collect that operation rather than resubmitting:

```sh
qodo review status "$OPERATION_ID" --json
```

**Unverified:** acceptance, completed assessment, reviewed-file coverage, complete finding inventory, context delivery, and persistence. Acceptance alone proves none of these. Live load remains untested.

### 4. `current-2-3-1-paths`

**Allowed:** review the changed work while preserving the previous comparison base, explicit paths, and auto effort.

Propose a separate external UTF-8/no-BOM file, `$CTX231`:

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

**Submission reason:** new code changes await assessment—not merely changed notes.

Here `$PREVIOUS_BASE` means the retained exact SHA from the previous review; do not replace it with the target tip or invent a different base:

```sh
qodo review --base "$PREVIOUS_BASE" --context-file "$CTX231" --async --json src/jobs/ test/jobs/
```

Do **not** request `--full`. Changed notes do not themselves invalidate reuse. Let the Engine determine eligibility and report whether execution was incremental, reused, or full. The added cancellation behavior also prevents assuming fixes-only intent from the round number.

Collect the returned operation ID with `review status`. Assess both introduced and still-open findings; report resolved and dismissed findings separately.

**Unverified:** the new assessment’s completion, actual continuation mode, context delivery, findings, and persistence. Previous completed coverage does not certify newer code. This intentionally path-limited review cannot establish coverage of intended changes elsewhere.

### 5. `mcp-no-collector`

**Review blocked:** the MCP schema cannot read this worktree, and no tested collector or prepared input exists.

Do not call `start-pre-pr-review` with invented input. Do not substitute an ad hoc `git diff`, another checkout, or a remotely fetched repository. Installation is unauthorized; do not install the CLI. The trusted MCP path does not require CLI version or identity probes.

The next allowed action is to report the collection blocker. Safe submission requires a tested collector that:

- Captures the requested worktree scope with CLI-equivalent safety exclusions.
- Reports omitted files.
- Verifies the comparison base is remotely fetchable.
- Retains the submitted snapshot and context.

Only after suitable prepared input exists should the live MCP schema guide submission and collection.

**Unverified:** the entire local input, scope, exclusions, base availability, context, and assessment. No review was performed, and no local-readiness claim is supported.

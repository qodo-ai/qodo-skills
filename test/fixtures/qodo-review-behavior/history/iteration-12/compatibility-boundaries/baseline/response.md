These are proposals only. No commands ran, files changed, or reviews were submitted. In command examples, `qodo` means the same trusted installed invocation used for the version probe.

### 1. `old-1-6` — blocked

**Next allowed action:** ask for explicit runtime-recovery authorization. Version **1.6.0** is below the **2.0.0** floor, even though the deployment advertises review API v2.

Do not run identity, login, review, or managed-tool calls. The absent update-source override does not authorize an update.

Any approved updater route must preserve the recorded origin and update policy, successfully check for a newer compatible 2.x target, make at most one approved update attempt, then repeat the unadorned version probe. Do not assume `latest-2` is the selected route.

**Unverified:** an approved recovery route, eligible target, and compatible executable.

### 2. `unparseable` — blocked

**Next allowed action:** establish a verified compatible runtime or obtain separate authorization for a supplied checksum-pinned installer. Neither is currently available.

Before recovery, check only whether `QODO_UPDATE_BASE_URL` is set—never disclose its value. If set, stop for the user.

Do not run authenticated calls or attempt login: `"custom build"` does not establish compatibility, and no authentication failure was reported. Do not invent an installer checksum.

**Unverified:** runtime version and provenance, override presence, installer integrity, and recovery authorization.

### 3. `floor-2-0-summary` — eligible for submission

Exactly **2.0.0** meets the floor; API v2 and identity are already verified. Preserve all context, changing only the supported narrative field name.

Proposed external context file, not created:  
`/private/var/folders/xt/yh2x_20j0f93qs1xjnc44w840000gn/T/opencode/review-2.0-context.json`

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

After preparing that file outside the reviewed changes, propose:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file /private/var/folders/xt/yh2x_20j0f93qs1xjnc44w840000gn/T/opencode/review-2.0-context.json --async --json
```

Effort is **auto**: omit `--fast` and `--deep`. Retain the returned operation ID and collect that operation rather than resubmitting.

**Unverified:** submission acceptance, completed assessment, actual coverage, and context-delivery metadata. Live load remains untested.

### 4. `current-2-3-1-paths` — preserve incremental eligibility

**Next allowed action:** prepare the updated context and submit the changed work with the prior exact base, explicit paths `src/jobs/ test/jobs/`, and **auto** effort. Do not request `--full` merely because notes changed.

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

Keep this file outside the reviewed diff. The fixture does not print the previous base SHA; retrieve that retained value before constructing the runnable command rather than inventing one.

The work includes new cancellation API behavior, not just fixes. Let the Engine determine reuse eligibility; report its actual `full`, `incremental`, or `reused` result.

**Unverified:** the retained base’s literal value here, the new assessment’s coverage, context delivery, and actual reuse outcome. Path-limited coverage would not certify changes elsewhere.

### 5. `mcp-no-collector` — coverage blocked

**Next allowed action:** report that MCP-only review cannot safely cover this worktree without a tested collector and prepared input.

Do not submit an empty or ad hoc diff, substitute another checkout, or install the CLI without authorization. MCP schema availability does not provide worktree access. CLI version and identity probes are unnecessary for this MCP path.

A suitable collector must preserve the intended snapshot and context, apply safety exclusions, report omissions, and verify a fetchable base.

**Unverified:** all required local collection and coverage evidence. No review is complete.

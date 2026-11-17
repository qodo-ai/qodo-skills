These are fixture-based proposals only. No commands, services, installations or repository writes were performed. Below, `qodo` means the same trusted installed invocation that produced each version probe.

### 1. `old-1-6` — review blocked

CLI **1.6.0** is below the required **2.0.0** floor. Advertised review API v2, cached catalogs and credentials do not override that requirement.

**Next allowed action:** request authorization for bounded compatibility recovery. Do not run identity, login, reviews or managed tools.

The update-source override is absent. After approval, select one same-origin recovery route, preserve existing version choices and update holds, and inspect its supported check. An updater must successfully offer a newer compatible 2.x target before any update. Do not blindly select `latest-2` or switch deployments. Allow one approved runtime attempt, then repeat the unadorned version probe.

**Unverified:** an approved recovery route, compatible target and resulting executable. No review coverage exists.

### 2. `unparseable` — review blocked

`custom build` does not establish a supported version. It is not evidence of an authentication problem.

**Next allowed action:** check only whether `QODO_UPDATE_BASE_URL` is set, without displaying its value. If set, stop for the user. Do not run identity, login, reviews or managed tools.

Recovery requires a separately authorized, Qodo/organization-supplied checksum-pinned installer route. Neither approval nor a verified checksum exists, so no installer command is proposed. Do not invent a digest or pipe an installer into a shell. After one authorized attempt, repeat `qodo --version`.

**Unverified:** runtime compatibility, approved installation artifact, checksum, origin and identity.

### 3. `floor-2-0-summary` — first review may proceed

Exactly **2.0.0** meets the floor; API v2 and identity are already verified for this invocation. Use the advertised older narrative field, `summary`, without dropping other accepted context.

Proposed external UTF-8 context file, without a BOM:

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

With that content prepared outside the reviewed worktree:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/private/var/folders/xt/yh2x_20j0f93qs1xjnc44w840000gn/T/opencode/review-floor-2-0.json" --async --json
```

Omitting `--fast` and `--deep` selects auto effort.

**Unverified:** acceptance, completed assessment, actual coverage, findings, context delivery and persistence. Cancellation tests passed according to the fixture; live load remains untested.

### 4. `current-2-3-1-paths` — continue with the same scope

**Next allowed action:** submit the changed code for review, retaining the same base, explicit paths and auto effort. The timeout correction and added cancellation behavior justify another assessment; this is not necessarily fixes-only work.

Proposed external context:

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

Proposed submission:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "/private/var/folders/xt/yh2x_20j0f93qs1xjnc44w840000gn/T/opencode/review-current-paths.json" --async --json src/jobs/ test/jobs/
```

Do **not** add `--full`. Changed notes alone do not invalidate reuse. Let the Engine determine and report whether execution is full, incremental or reused.

**Unverified:** actual execution mode, coverage, context delivery, findings and persistence. This remains a path-limited assessment; it cannot certify intended changes outside those paths.

For either accepted CLI submission, retain the returned operation ID and collect that operation with `qodo review status <operation-id> --json`, respecting returned polling delays. Acceptance alone is not completion.

### 5. `mcp-no-collector` — worktree coverage blocked

The MCP schema cannot read this worktree. Without a tested collector and prepared input, no review submission is justified.

**Next allowed action:** report the coverage blocker. Proceed only when a tested collector can preserve the intended snapshot and context, apply safety exclusions, report omissions and verify a fetchable comparison base.

Do not substitute an ad hoc `git diff`, unrelated checkout or remotely fetched repository. Do not install anything without authorization, and do not run CLI preflight for the MCP path.

**Unverified:** safe collection, submitted scope, omissions, base availability and all review results. No worktree-review completion claim is supported.

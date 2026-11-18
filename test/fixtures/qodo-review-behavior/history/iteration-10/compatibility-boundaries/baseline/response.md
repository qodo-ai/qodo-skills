Commands below are proposals only. `qodo` means the resolved installed executable; context-file paths are illustrative files outside the reviewed changes. Nothing is submitted or changed.

### 1. `old-1-6` — blocked

CLI **1.6.0** is below the required **2.0.0** floor. Review API v2, cached catalogs and credentials do not override that requirement.

**Next allowed action:** request runtime-update approval or identification of an already-installed, verified compatible executable. The update-source override is already known to be absent.

Do not run identity, login, reviews or managed tools. Do not update without approval. An approved updater route must first successfully offer a newer compatible 2.x target at the recorded origin; preserve version pins and update holds. Do not assume `latest-2` is authorized.

**Unverified:** a compatible executable, an eligible update target and review coverage.

### 2. `unparseable` — blocked

`custom build` does not establish compatibility. It also does not establish an authentication problem.

**Next allowed action:** obtain a verifiable compatible installed invocation, or explicit approval and an organization-supplied checksum-pinned installer for the existing deployment. Before compatibility recovery, check only whether `QODO_UPDATE_BASE_URL` is set—never expose its value. If set, stop for the user.

No login, catalog refresh, authenticated call or guessed installer/update command is justified. After one authorized installation attempt, repeat the resolved invocation’s unadorned `--version`; stop if it remains incompatible or unparseable.

**Unverified:** executable compatibility, approved installer provenance/checksum and review coverage.

### 3. `floor-2-0-summary` — eligible for first review

Exactly **2.0.0** meets the floor. Review API v2 and identity are verified, so no repeated identity check is needed.

**Next allowed action:** supply this context in an external UTF-8 file, without a BOM. Change only the narrative field name from `notes` to the advertised `summary`:

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

Proposed submission:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /path/outside-worktree/review-2.0.0.json \
  --async --json
```

Omit `--fast` and `--deep`: this uses default auto effort. Do not add `--full` for this first review.

**Unverified:** submission acceptance, completed assessment, actual coverage/exclusions, context delivery and findings. Cancellation tests passed as supplied; live load remains untested.

### 4. `current-2-3-1-paths` — continue with the same scope

**Reason for another assessment:** new timeout-guard and cancellation-API changes await review. Changed notes alone do not justify forcing a fresh assessment.

Preserve both paths, the base and auto effort. Use the advertised `notes` field:

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

Confirm submission and path options with `qodo review --help` if those options are not already verified, then propose:

```sh
qodo review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /path/outside-worktree/review-2.3.1.json \
  --async --json \
  src/jobs/ test/jobs/
```

Do **not** add `--full`, `--fast` or `--deep`. Let the Engine determine and report incremental reuse or its actual fallback. The context includes new API behavior, so do not characterize this as fixes-only.

**Unverified:** actual continuation mode, current coverage, context delivery and the complete finding inventory. This requested path-limited review does not certify files outside those paths.

For either accepted CLI submission, retain its returned operation ID and collect that same operation:

```sh
qodo review status <returned-operation-id> --json
```

Respect returned polling delays. Acceptance is not completion; inspect coverage, warnings, context delivery and both introduced and still-open findings before claiming readiness.

### 5. `mcp-no-collector` — coverage blocked

The MCP pre-PR schema cannot read this worktree. Without a tested collector or prepared input, it cannot safely provide the requested local review.

**Next allowed action:** report the blocker. Proceed only when a tested collector can preserve the intended snapshot/context, enforce safety exclusions, report omissions and verify a fetchable comparison base.

Do not submit an ad hoc `git diff`, substitute another checkout or install anything without authorization. MCP does not require CLI version or identity probes.

**Unverified:** eligible local collection, prepared review input, base fetchability and all review coverage. No review has completed.

*Proposals only; nothing was executed or written. Below, `qodo` means the same trusted installed invocation used for that case’s version probe.*

### 1. `old-1-6` — compatibility blocked

**Next action:** Stop before identity, login, review or authenticated managed-tool calls. Version **1.6.0 fails the minimum 2.0.0 requirement**, even though the deployment advertises review API v2.

Runtime-update approval is missing. If granted, select one same-origin recovery route, inspect `qodo update --help`, and use its advertised check. Proceed only if that check offers a newer compatible **2.x** target while preserving existing pins and update policy. Do not blindly select `latest-2` or switch routes after failure. After one approved attempt, repeat the unadorned version probe.

**Unverified:** A compatible executable, current identity and review coverage. Cached credentials or catalog data do not establish compatibility.

### 2. `unparseable` — version unknown

**Next action:** Stop authenticated calls. `"custom build"` does not establish a supported version, and there is no reported authentication problem to justify login.

Before recovery, check only whether `QODO_UPDATE_BASE_URL` is set—never expose its value. If set, stop for the user. An unparseable runtime requires a **separately authorized, Qodo/organization-supplied checksum-pinned installer route**, not a speculative updater command. The necessary approval, artifact and verified checksum are absent.

After one authorized installation attempt, the next compatibility probe would be:

```sh
qodo --version
```

**Unverified:** Runtime version, supported review capability, recovery artifact and checksum, identity and coverage. No installer command can safely be proposed from the supplied evidence.

### 3. `floor-2-0-summary` — first review permitted

**Next action:** Propose the first review with default auto effort. Version **2.0.0 meets the floor**; API v2, identity and the required flags are verified.

Proposed UTF-8 context at `${TMPDIR}/qodo-review-floor-2-0-summary.json`, outside the reviewed worktree:

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

Only the narrative key changes from `notes` to the advertised `summary`.

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "${TMPDIR:?}/qodo-review-floor-2-0-summary.json" --async --json
```

Retain the returned operation ID and collect that operation; acceptance alone is not completion.

**Unverified:** Review outcome, exclusions, coverage, result identity and context delivery. Live-load behavior remains untested.

### 4. `current-2-3-1-paths` — preserve scope and reuse eligibility

**Next action:** Review the changed code—the corrected guard and added cancellation API behavior justify another assessment. Changed notes alone do not justify `--full`.

Proposed context at `${TMPDIR}/qodo-review-current-2-3-1-paths.json`, outside the reviewed worktree:

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

Confirm submission flags and path syntax with installed `qodo review --help` if not already verified. With those options confirmed:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "${TMPDIR:?}/qodo-review-current-2-3-1-paths.json" --async --json src/jobs/ test/jobs/
```

Omit `--fast`, `--deep` and `--full`. Preserve both explicit paths. The new API behavior must not be represented as fixes-only.

**Unverified:** Whether the Engine selects incremental reuse, full fallback or another supported outcome; current findings, coverage and context delivery. This path-limited result cannot certify files outside those paths.

### 5. `mcp-no-collector` — collection blocked

**Next action:** Report that MCP-only review cannot safely cover this worktree with the available inputs. Do not submit a review or install anything.

The MCP schema cannot read the worktree. Proceeding requires a tested collector that preserves the intended snapshot and context, applies safety exclusions, reports omissions and verifies a fetchable base. An ad hoc `git diff` or remotely fetched substitute is not equivalent.

**Unverified:** Local input completeness, exclusions, omissions, base availability and review coverage. CLI version and identity preflight do not apply to this MCP path.

### 6. `cli-identity-gap` — identity comparison unavailable

**No—you cannot claim the operation-response identity check passed.**

Known evidence:

- The retained accepted handle is `OP-REQUESTED`.
- Its status response reports complete coverage and inventory, with no findings.
- Returned snapshot metadata matches the intended base, commit and tree.
- The returned review-run ID is `REVIEW-RESULT`.

The response exposes no transport operation ID, and the renderer does not compare the hidden ID against `OP-REQUESTED`. Neither the requested handle, the review-run ID nor matching snapshot metadata supplies that missing comparison.

**Next action:** Assess the existing result and report the limitation:

> Qodo’s result returned for `OP-REQUESTED` reports complete coverage and inventory with no findings, and its snapshot matches the intended base, commit and tree. The operation-response identity comparison remains unverified because the returned transport operation ID is unavailable.

Do not change runtimes, invent another read API or submit another review to conceal this gap.

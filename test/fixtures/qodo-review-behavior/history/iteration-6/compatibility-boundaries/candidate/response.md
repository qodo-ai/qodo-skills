All actions below are **proposals only**. No commands, services, installation changes or writes were performed. `qodo` denotes the exact installed invocation used for each fixture’s version probe—not a repository-local launcher.

## 1. `old-1-6`

**Review blocked:** CLI 1.6.0 is below the required 2.0.0 floor. Advertised review API v2 does not override that requirement.

Next allowed action: request runtime-update approval and establish one deployment-approved, same-origin migration route. The update-source override is already known absent.

Do **not** run identity, login, review, catalog refresh or managed tools. Cached credentials/catalogs cannot establish executable compatibility.

If approval is granted:

1. Preserve the recorded origin, exact-version choices and update holds.
2. Select one supported route before checking it.
3. Require its supported update check to offer a newer compatible **2.x** target.
4. Only then make one approved runtime-update attempt.
5. Re-probe with:
   ```sh
   qodo --version
   ```
6. Only after compatibility is verified, check identity:
   ```sh
   qodo read whoami --json --skill qodo-review --skill-version 1.10.15 --distribution skills-sh
   ```

Do not switch routes after a failed check. `latest-2` is conditional legacy same-origin migration—not a blanket fallback or permission to change future update policy.

**Unverified:** migration support, an offered compatible target, update authority and resulting executable compatibility. No assessment exists.

## 2. `unparseable`

**Review blocked:** `"custom build"` establishes no supported version. It is not evidence of missing credentials.

Next allowed actions:

- Check **only whether** `QODO_UPDATE_BASE_URL` is set; never expose its value. If set, stop for the user to resolve it.
- Request covering installation approval and a Qodo/organization-supplied, checksum-pinned installer with verified deployment/version provenance.

There is no justified installer command yet: neither approval nor a verified checksum exists. Do not invent either, pipe an installer into a shell, switch deployments, attempt ordinary updater recovery or run login.

After receiving the required evidence and authority, make one approved installation attempt, then use the unadorned version probe above. Continue to authenticated calls only after verifying compatibility. Failure or continued incompatibility stops recovery.

**Unverified:** executable version, installer integrity, approved installation target and review capability. No authentication problem has been established.

## 3. `floor-2-0-summary`

**Proceed with the first review.** Exactly 2.0.0 meets the floor; API v2 and identity are verified for this invocation. Do not repeat identity unnecessarily.

Propose an external temporary context file at:

```text
/outside/compat-floor-context.json
```

Its complete UTF-8, BOM-free content would be:

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

Only the narrative key changes from `notes` to the advertised older field, `summary`. Preserve the decision and both recent-work entries; this includes new API behavior, not merely a fix.

Once that context file is prepared outside reviewed changes, propose:

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file /outside/compat-floor-context.json \
  --async --json
```

Omit both effort flags for **auto**. Use the verified base literally; do not replace it with a target tip.

**Evidence limits:** the fixture supplies the cancellation-test result; this evaluation did not run tests. Live load remains untested. Submission acceptance would not establish completed review, complete coverage or reviewer consumption of context.

## 4. `current-2-3-1-paths`

**Proceed with a continuation assessment.** Concrete reason: the corrected timeout guard and added cancellation API behavior need review.

Prepare the same complete context as case 3, changing **only** `summary` to `notes`, at the proposed external path:

```text
/outside/compat-current-context.json
```

Preserve both explicit paths, the same base and auto effort:

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file /outside/compat-current-context.json \
  --async --json src/jobs/ test/jobs/
```

Do **not** request `--full`, `--fast` or `--deep`. Changed notes alone do not justify invalidating reuse. Let the Engine determine eligibility and report whether execution was full, incremental or reused; do not infer that outcome from the version or review round.

**Evidence limits:** previous complete coverage does not certify the newly changed snapshot. The resulting assessment remains path-limited and cannot certify files outside those paths. No reviewer-consumption, persistence or routing outcome is yet established.

### Collection for cases 3 and 4

Retain the submitted base, snapshot, paths, context and returned operation ID. Bind `id` to that actual nonempty `operation_id`, then collect:

```sh
qodo review status "$id" --json
```

Respect returned polling delays; do not resubmit to obtain progress. Preserve recovery handles if admission is uncertain.

Read the final structured result, warnings, coverage, context-delivery metadata and complete finding inventory—including earlier `still_open` findings, not just `introduced`. Missing completeness metadata is unknown. Accepted submission, zero new findings or context preparation alone cannot establish readiness.

## 5. `mcp-no-collector`

**Review blocked by collection coverage.** The MCP schema accepts prepared input; it cannot read this worktree.

Next allowed action: report the missing tested collector. Before submission, a suitable collector must:

- Match intended scope and CLI safety exclusions.
- Report omitted files.
- Verify the comparison base is fetchable.
- Retain the submitted snapshot and context.

Do not call `start-pre-pr-review` with fabricated input, substitute an ad hoc `git diff`, fetch an unrelated checkout or install the CLI without authorization. Do not invent collector modes or request fields. MCP execution skips CLI version and identity preflight, but that does not bypass the collector requirement.

**Unverified:** all worktree collection and review coverage. No review request should be submitted, and no completion claim is justified.

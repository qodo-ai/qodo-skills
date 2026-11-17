# CLI execution and recovery

Read preflight before the first CLI review.
Read collection or recovery when that path applies.
The [main Skill](../SKILL.md) owns the review workflow and authority.
The CLI owns credentials, transport and runtime updates. Do not reproduce them in scripts.

## Preflight

1. Resolve the installed executable. On POSIX, if `qodo` is absent, try
   `"${QODO_HOME:-$HOME/.qodo}/bin/qodo"`.
   Keep the first working invocation.
   On Windows, read [shell guidance](windows-shells.md) first.
   Use [launcher recovery](windows-launcher.md) only if invocation fails.
   Do not execute repository-local launchers.
2. Run the resolved invocation with only `--version`, before authenticated commands.
   In every example here and in linked references, `qodo` stands for that invocation.
   After fallback succeeds, do not return to the unavailable bare command.
   Require the main Skill's minimum version and review API v2.
   An old or unparseable version follows [compatibility recovery](#compatibility-recovery).
   It is not an authentication diagnosis.
3. Run the main Skill's provenance-stamped `qodo read whoami` unless a successful check still covers this context.
   Missing credentials can mean inaccessible keychain access in a sandbox.
   When plausible, request one exact read-only identity retry through the host's approval flow.
   Stop on denial. That approval covers no other command.
   Reuse a successful identity check only for the same invocation, workspace, deployment and execution context.
4. Only explicit missing credentials justify login.
   Preserve the organization's exact login endpoint. Never switch a customer deployment to Cloud.
   `No tool catalog cached` does not mean credentials are missing.
   Refresh once with `qodo tools --refresh`, then repeat the identity check.
   Preserve network, TLS, service and authorization errors instead of relabeling them as login failures.
5. After identity succeeds, an unknown managed command permits one catalog refresh and schema recheck.
   If it remains absent or returns `tool_unavailable`, report the missing capability.
   An unknown built-in `qodo review` needs runtime recovery, not login or catalog refresh.
6. Confirm review options with offline `qodo review --help`.
   Resolve the base and prepare context under the main Skill's scope rules.
   Use complete UTF-8 files without a BOM and `--json` for parsed output.
   Use `--args-file` for structured managed-tool inputs.

Treat `QODO_NOTICE` updates as passive, even when an older CLI asks for action.
Do not interrupt the task with inventory or update questions.
Mention each notice at most once. Updated instructions load next session.
Dismissal does not change recorded maintenance policy or opt-outs.
For a user-requested update, follow [skill updates](skill-updates.md).

## Compatibility recovery

Only when an update is needed, check whether `QODO_UPDATE_BASE_URL` is set.
Never print its value. If set, stop for the user to resolve the source override.
Do not change it or assume it matches the recorded origin.

If the version is old or unparseable, do not run identity, login, reviews or managed tools yet.
Choose one deployment-approved upgrade route.
Reuse covering runtime-update authorization or ask once before changing the installation.

- For parsed 1.x, ordinary `qodo update` can reach approved 2.x when the recorded origin supports migration.
- If legacy aliases still serve 1.x, check that origin's supported `latest-2` recovery route.
  Require a compatible newer 2.x target from its update check.
  Only then propose `qodo update --channel latest-2`.
- This exception permits approved 1.x-to-stable-2.x migration, not another major migration or a future-update policy change.
- Preserve the recorded origin, explicit version choices and update holds.
  Do not substitute a channel for an exact version.
- For an unparseable runtime or no supported updater, use an organization-supplied, checksum-pinned installer with covering authority.
  Never switch to public service, invent a digest or pipe an installer into a shell.

Make one approved runtime attempt.
Repeat the unadorned version probe.
Continue only when it meets the Skill's minimum.
On denial, failure or continued incompatibility, stop without changing skill or user files.
Do not try another route.

## Submit and collect

Use auto by omitting depth flags unless the main Skill's selection rules call for another mode.
`--async` submits a server-side operation and returns its operation ID.
Submission exit 0 means accepted, not reviewed.
The run survives the submitting process exiting.

Illustrative POSIX commands, after preflight and writing context:

```sh
command -v jq >/dev/null 2>&1 || { printf '%s\n' 'This async recipe requires jq; use the connected flow if unavailable.' >&2; exit 1; }
QODO_REVIEW_CONTEXT="${QODO_REVIEW_CONTEXT:-.qodo/session-context.json}"
[ -f "$QODO_REVIEW_CONTEXT" ] || { printf '%s\n' "Write review context to $QODO_REVIEW_CONTEXT or set its path." >&2; exit 1; }
QODO_REVIEW_BASE="$(git merge-base HEAD origin/main)" || { printf '%s\n' 'Cannot resolve the intended merge base.' >&2; exit 1; }
if ! submission="$(qodo review --base "$QODO_REVIEW_BASE" --context-file "$QODO_REVIEW_CONTEXT" --async --json)"; then printf '%s\n' "$submission" >&2; exit 1; fi
if ! id="$(printf '%s\n' "$submission" | jq -er '.operation_id | select(type == "string" and length > 0)')"; then printf '%s\n' "$submission" >&2; exit 1; fi
qodo review status "$id" --json
```

Substitute the actual target branch.
For a chosen light checkpoint, add `--fast`; for justified thorough review, add `--deep`.
Do not change effort because async is unavailable. Use the connected fallback instead.

Collect every accepted run inside its retention window. Respect a returned polling delay.
Use the host's nonblocking wait mechanism and do useful independent work between checks.

| Status exit | Meaning | Action |
|---|---|---|
| `0` | Completed result, with the same findings/metadata as a live run. | Read and assess it. |
| `2` | Working or polling throttled. | Respect `retry_after`, then poll the same operation. |
| `1` | Failed, canceled, expired or unavailable. | Read the error and follow bounded recovery. Never assume clean. |

This shell loop illustrates collection only. It does not restart a failed review:

```sh
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")"
cleanup_qodo_review() { [ -n "${QODO_REVIEW_TMP:-}" ] && [ -d "$QODO_REVIEW_TMP" ] && rm -r -- "$QODO_REVIEW_TMP"; }
trap cleanup_qodo_review EXIT; trap 'exit 130' INT; trap 'exit 143' TERM
while :; do
  status=0; qodo review status "$id" --json > "$QODO_REVIEW_TMP/result.json" || status=$?
  case "$status" in
    0) cat "$QODO_REVIEW_TMP/result.json" || exit 1; break ;;
    2) delay=$(jq -r 'if (.retry_after | type) == "number" and .retry_after > 0 then .retry_after else 15 end' "$QODO_REVIEW_TMP/result.json") || exit 1
       sleep "$delay" ;;
    *) cat "$QODO_REVIEW_TMP/result.json" >&2; exit "$status" ;;
  esac
done
```

Retain the result in existing task state before removing any host-owned run artifacts.
Clean only the unique directory created for this invocation.
Never reuse or remove shared `.qodo/review.*` paths.

### Async limits

- Async has no progress stream. `--async --progress` is rejected.
  For live progress, use [connected execution](connected-progress.md).
- This surface runs deterministic agents only.
  If a review needs human input, read the failure and follow its connected-run guidance.
- Results normally remain available for about one hour after completion.
  The returned `ttl` is authoritative.
  A missing/expired/wrong-principal operation can have the same unavailable response.
  Do not infer which condition occurred without evidence.
- Keep both the accepted operation ID and any submission-recovery ID.
  They serve different purposes.
  An OpenTelemetry `trace` ID is a support diagnostic, not a result handle.
- Never assume a fresh submission is free or deduplicated.
  Use `review status` to collect an accepted run.
  For uncertain admission, follow the returned recovery command, such as
  `--async --retry-submission <id>` when supported.
  Recovery preserves the original request and context.
  Do not append new review-input options or replace it with a newly gathered snapshot.
- For more retained detail, confirm support for
  `qodo review status <operation-id> --extended --json`.
  `--extended` changes the result view, not review effort or execution.

## Recover a review

For a status transport failure, retry collection once after the returned delay, or 15 seconds.
If collection still fails, preserve the operation ID and report the gap.
Never start another assessment merely to poll.

For a confirmed terminal failure, correct a recoverable cause and retry once with the same selected effort and context.
Stop on entitlement, authentication, permission, rate-limit or further failure.
Report expired evidence and coverage gaps.
An `MT-TOOL-LOOP` or `MT-RATE-LIMITED` error means stop or change approach, not repeat the call.

Distinguish a killed connected client, cancellation after connection loss, a lost final stream message,
and an explicit backend failure. A transport failure does not establish a diff-size or complexity limit.
Collect any retained result using the CLI's recovery hint before another submission.
If the run is confirmed canceled or unrecoverable, allow at most one uninterrupted retry.
This is the same terminal-recovery attempt above, not an additional retry allowance.
Keep selected effort and context.
A pending run is not a reason to restart. Never lower effort or remove context to obtain a result.

### Repository credentials

For `repo_not_connected`, `MT-REPO-NO-CREDENTIAL` or “could not obtain repository credentials”:

1. Inspect `origin` without exposing URL credentials. An SSH alias can differ from the connected host.
2. Use a known exact repository `full_name`. Self-hosted names can include a host.
   Codebase Wisdom suggestions do not prove connectivity.
3. Confirm `--repo` support with `qodo review --help`.
   If the error forbids automatic retries, obtain approval for the corrected command first.
4. Retry the failed submission once with `--repo <full_name>`, preserving other inputs.
   Collect the new operation ID if accepted.
   Do not treat uncertain acceptance as a confirmed failure.

If identity is uncertain or the retry fails, stop.
Ask an administrator to check the integration instead of asserting disconnection.
This is the bounded cause-correction retry, not an extra independent retry budget.

### Closed preview

A deployment can reject unenrolled organizations with `closed_preview`.
With `--json`, the structured error contains `code`, `message` and `hint`.
CLI prose removes terminal control characters.

Show the returned message and hint unchanged.
Stop. Entitlement is not a transient fault, so retrying or watching cannot repair it.
Do not submit again unless the user confirms enrollment.
Enrollment can take about ten minutes to activate without another login.
Identity and other Qodo commands are not themselves review entitlement checks.

# CLI execution and recovery

Read preflight before the first CLI review.
Read collection or recovery when that path applies.
The [main Skill's execution policy](../SKILL.md#execution-and-recovery-policy) owns all compatibility,
authority and stop/retry gates. This reference supplies their CLI command sequence and result syntax.
Apply the canonical gates before selecting any command below.

## Preflight

1. Resolve the installed executable. On POSIX, if `qodo` is absent, try
   `"${QODO_HOME:-$HOME/.qodo}/bin/qodo"`.
   On Windows, read [shell guidance](windows-shells.md) first.
   Use [launcher recovery](windows-launcher.md) only if invocation fails.
2. Run the resolved invocation with only `--version`, before authenticated commands.
   In every example here and in linked references, `qodo` stands for that invocation.
   Use [compatibility commands](#compatibility-recovery) only if canonical recovery permits them.
3. When the identity gate requires a check, use the main Skill's provenance-stamped `qodo read whoami`.
   For its approved sandbox diagnostic, submit that exact read-only command through the host's approval flow.
   For an authorized login, use the organization's supplied exact login command/endpoint.
4. When the canonical discovery gate permits refresh, run `qodo tools --refresh`
   and repeat the failed identity check or managed-command schema inspection.
5. Confirm review options with offline `qodo review --help`.
   Resolve the base and prepare context under the main Skill's scope rules.
   Use complete UTF-8 files without a BOM and `--json` for parsed output.
   Use `--args-file` for structured managed-tool inputs.

Notice handling belongs to the main Skill's passive-update section.
For requested maintenance, [skill updates](skill-updates.md) supplies command mechanics.

## Compatibility recovery

Apply the canonical compatibility-recovery gate first, including override presence,
route selection, target verification, installation authority and the single-attempt limit.

| Canonically selected path | Command mechanics |
|---|---|
| Ordinary updater at the recorded origin | Inspect `qodo update --help`; use its advertised check before the approved `qodo update`. |
| Verified legacy same-origin route | Use that route's supported check; an approved target can use `qodo update --channel latest-2`. |
| Separately authorized pinned installer | Use only the supplied artifact and checksum-verification procedure; no generic installer command is supplied here. |
| Post-attempt compatibility probe | Repeat the resolved invocation with only `--version`, then apply the canonical compatibility gate. |

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
Check identities actually exposed in the result. Some CLI status renderers omit the
returned transport operation ID and do not check it against the requested handle.
In that case, report that comparison as unavailable. Verify any returned snapshot
metadata, but do not substitute `meta.run.id`, a review ID or the requested handle
for the missing returned operation ID. Matching snapshot metadata does not prove that check.
Do not change runtimes or claim complete identity verification to conceal the gap.

| Status exit | Meaning | Action |
|---|---|---|
| `0` | Completed result, with the same findings/metadata as a live run. | Read and assess it. |
| `2` | Working or polling throttled. | Respect `retry_after`, then poll the same operation. |
| `1` | Failed, canceled, expired or unavailable. | Read the error and follow bounded recovery. Never assume clean. |

This shell loop illustrates collection only. It does not restart a failed review:

```sh
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")" || exit 1
[ -n "$QODO_REVIEW_TMP" ] && [ -d "$QODO_REVIEW_TMP" ] || exit 1
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

Classify the structured error under the main Skill's collection/retry gates.
An allowed collection retry uses `qodo review status <original-operation-id> --json`.
An allowed cause-corrected submission uses the retained original base, scope, context and effort.

Distinguish a killed connected client, cancellation after connection loss, a lost final stream message,
and an explicit backend failure. A transport failure does not establish a diff-size or complexity limit.
Use the CLI's retained-result recovery hint when present. The canonical retry allowance
is shared across these failure symptoms; this section creates no separate allowance.

### Repository credentials

For `repo_not_connected`, `MT-REPO-NO-CREDENTIAL` or “could not obtain repository credentials”:

1. Inspect `origin` without exposing URL credentials. An SSH alias can differ from the connected host.
2. Use a known exact repository `full_name`. Self-hosted names can include a host.
   Codebase Wisdom suggestions do not prove connectivity.
3. Confirm `--repo` support with `qodo review --help`.
4. If canonical retry/authority gates permit the correction, add `--repo <full_name>` to the retained submission.
   Collect the new operation ID if accepted.
   Do not treat uncertain acceptance as a confirmed failure.

Apply the main Skill's identity and retry stop gates to the result.

### Closed preview

A deployment can reject unenrolled organizations with `closed_preview`.
With `--json`, the structured error contains `code`, `message` and `hint`.
CLI prose removes terminal control characters.

Apply the main Skill's closed-preview stop/reporting gate.
Enrollment can take about ten minutes to activate without another login.
Identity and other Qodo commands are not themselves review entitlement checks.

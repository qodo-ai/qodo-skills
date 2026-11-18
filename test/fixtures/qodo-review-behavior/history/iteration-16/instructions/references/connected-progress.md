# Connected review progress example

Read when live progress is useful or async is unavailable.
Follow the main Skill's [submission policy](../SKILL.md#4-submit-once-and-collect-the-result).
Adapt the launch, progress polling and collection to the host's background-process tools.
The placeholders below are not literal shell arguments. Select depth using the skill's lifecycle
policy and attach context through `.qodo/session-context.json` or `--context-file <path>`.

## Execution rules

- Attach context through a file. Stdin heredocs are unsuitable for background execution.
- Use a unique per-run temporary directory.
  Keep the single result JSON on stdout separate from NDJSON progress on stderr.
  Use host-native nonblocking progress reads, not a foreground `tail`.
- Keep the process alive through the review. Client exit can cause cancellation after a short grace period.
- Relay concise readable status, not raw JSON or model output.
  `cli.status` carries a message. `tool.activity` carries tool name and outcome.
  Treat `task.delta` and unknown kinds as occasional generic heartbeats.
- For `qar.client.reconnecting`, relay attempt/delay and structured close/error codes.
  `qar.client.reconnected` means transport opened.
  `resubscribeAttempts` counts live-task reattachments.
  `qar.client.reconnect_failed` reports exhausted retries, not the final diagnosis.
- On `task.done`, inspect `payload.status`.
  Stop progress relay on failure/cancellation or `error`, but wait for process exit.
  Always read the final envelope, including after nonzero exit.
  Progress is not findings. Actionable messages can appear only in the result.
- Capture exit status, reap the child and disarm its PID before parsing.
  On interruption, terminate and reap only this invocation's active child.
  Remove only its owned temporary directory.
- If background progress is unavailable, run foreground with a multi-minute timeout.
  Preserve selected effort and context. Missing progress does not justify failing review or lowering effort.
- Never combine `--progress` with `--async`.
  Confirm support for `--json --progress` with installed help.

## Illustrative POSIX lifecycle

```
QODO_REVIEW_BASE="$(git merge-base HEAD origin/main)" || { printf '%s\n' 'Cannot resolve merge base for origin/main; fetch missing history or choose the correct target.' >&2; exit 1; } # substitute the intended target
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")" || exit 1
[ -n "$QODO_REVIEW_TMP" ] && [ -d "$QODO_REVIEW_TMP" ] || exit 1
qodo_review_pid=; qodo_review_pending_status=; cleanup_qodo_review() { [ -n "${QODO_REVIEW_TMP:-}" ] && [ -d "${QODO_REVIEW_TMP}" ] && rm -r -- "${QODO_REVIEW_TMP}"; }
stop_qodo_review() { qodo_review_status=$1; if [ -z "${qodo_review_pid}" ]; then qodo_review_pending_status=${qodo_review_status}; return; fi; trap '' INT TERM; if jobs -p | grep -Fxq "${qodo_review_pid}"; then kill -TERM "${qodo_review_pid}" 2>/dev/null || :; sleep 1; kill -KILL "${qodo_review_pid}" 2>/dev/null || :; wait "${qodo_review_pid}" 2>/dev/null || :; fi; exit "${qodo_review_status}"; }
trap cleanup_qodo_review EXIT; trap 'stop_qodo_review 130' INT; trap 'stop_qodo_review 143' TERM
qodo review --json --progress --base "$QODO_REVIEW_BASE" [--deep|--fast] [--ticket <URL> …] [<pathspec>…] \
  >"${QODO_REVIEW_TMP}/result.json" 2>"${QODO_REVIEW_TMP}/progress.ndjson" &
qodo_review_pid=$!; [ -z "${qodo_review_pending_status}" ] || stop_qodo_review "${qodo_review_pending_status}"
# Use host-native nonblocking polling of progress.ndjson until the process exits.
# Run the remaining collection steps only after the host reports process exit.
if wait "${qodo_review_pid}"; then status=0; else status=$?; fi # capture exit — but do NOT abort on non-zero
qodo_review_pid=; trap - INT TERM                              # disarm the reaped PID before parsing
# ALWAYS read "${QODO_REVIEW_TMP}/result.json" now: it carries the error envelope (incl. closed_preview).
# Act on the captured status; after parsing, remove only "${QODO_REVIEW_TMP}", never a shared path.
```

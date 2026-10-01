# Connected review progress example

Illustrative POSIX shell setup and collection for the canonical
[execution rules](../SKILL.md#choose-execution-for-the-selected-review).
Adapt the launch, progress polling and collection to the host's background-process tools.
The placeholders below are not literal shell arguments. Select depth using the skill's lifecycle
policy and attach context through `.qodo/session-context.json` or `--context-file <path>`.

```
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")"
qodo_review_pid=; qodo_review_pending_status=; cleanup_qodo_review() { [ -n "${QODO_REVIEW_TMP:-}" ] && [ -d "${QODO_REVIEW_TMP}" ] && rm -r -- "${QODO_REVIEW_TMP}"; }
stop_qodo_review() { qodo_review_status=$1; if [ -z "${qodo_review_pid}" ]; then qodo_review_pending_status=${qodo_review_status}; return; fi; trap '' INT TERM; if jobs -p | grep -Fxq "${qodo_review_pid}"; then kill -TERM "${qodo_review_pid}" 2>/dev/null || :; sleep 1; kill -KILL "${qodo_review_pid}" 2>/dev/null || :; wait "${qodo_review_pid}" 2>/dev/null || :; fi; exit "${qodo_review_status}"; }
trap cleanup_qodo_review EXIT; trap 'stop_qodo_review 130' INT; trap 'stop_qodo_review 143' TERM
qodo review --json --progress [--deep|--fast] [--ticket <URL> …] [<pathspec>…] \
  >"${QODO_REVIEW_TMP}/result.json" 2>"${QODO_REVIEW_TMP}/progress.ndjson" &
qodo_review_pid=$!; [ -z "${qodo_review_pending_status}" ] || stop_qodo_review "${qodo_review_pending_status}"
# Use host-native nonblocking polling of progress.ndjson until the process exits.
# Run the remaining collection steps only after the host reports process exit.
if wait "${qodo_review_pid}"; then status=0; else status=$?; fi # capture exit — but do NOT abort on non-zero
qodo_review_pid=; trap - INT TERM                              # disarm the reaped PID before parsing
# ALWAYS read "${QODO_REVIEW_TMP}/result.json" now: it carries the error envelope (incl. closed_preview).
# Act on the captured status; after parsing, remove only "${QODO_REVIEW_TMP}", never a shared path.
```

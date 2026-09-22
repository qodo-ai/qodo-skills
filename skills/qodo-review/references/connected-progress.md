# Connected review progress

Read this reference when choosing a connected review with live progress. Select depth using the
lifecycle policy in [the skill](../SKILL.md#choose-when-and-how-deeply-to-review).

A review takes anywhere from seconds to a few minutes. Run it **foreground and it blocks silently**
until it finishes — the user just watches a spinner. Instead, run it in the **background** with
`--progress` and relay the streamed status, so they see it's alive.

`qodo review --json --progress` writes the single JSON result to **stdout** and a stream of NDJSON
progress events to **stderr** (`--progress` requires `--json`). Split the two into files and follow
the progress one:
```
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")"
qodo_review_pid=; qodo_review_pending_status=; cleanup_qodo_review() { [ -n "${QODO_REVIEW_TMP:-}" ] && [ -d "${QODO_REVIEW_TMP}" ] && rm -r -- "${QODO_REVIEW_TMP}"; }
stop_qodo_review() { qodo_review_status=$1; if [ -z "${qodo_review_pid}" ]; then qodo_review_pending_status=${qodo_review_status}; return; fi; trap '' INT TERM; if jobs -p | grep -Fxq "${qodo_review_pid}"; then kill -TERM "${qodo_review_pid}" 2>/dev/null || :; sleep 1; kill -KILL "${qodo_review_pid}" 2>/dev/null || :; wait "${qodo_review_pid}" 2>/dev/null || :; fi; exit "${qodo_review_status}"; }
trap cleanup_qodo_review EXIT; trap 'stop_qodo_review 130' INT; trap 'stop_qodo_review 143' TERM
qodo review --json --progress [--deep|--fast] [--ticket <URL> …] [<pathspec>…] \
  >"${QODO_REVIEW_TMP}/result.json" 2>"${QODO_REVIEW_TMP}/progress.ndjson" &
qodo_review_pid=$!; [ -z "${qodo_review_pending_status}" ] || stop_qodo_review "${qodo_review_pending_status}"
tail -n +1 --pid="${qodo_review_pid}" -f "${QODO_REVIEW_TMP}/progress.ndjson" # GNU tail: follows, then STOPS when the review exits
if wait "${qodo_review_pid}"; then status=0; else status=$?; fi # capture exit — but do NOT abort on non-zero
qodo_review_pid=; trap - INT TERM                              # disarm the reaped PID before parsing
# ALWAYS read "${QODO_REVIEW_TMP}/result.json" now: it carries the error envelope (incl. closed_preview).
# Act on the captured status; after parsing, remove only "${QODO_REVIEW_TMP}", never a shared path.
```

**This is a POSIX example, and the real follow mechanism is your runtime's, not a literal `tail`.**
An agent should poll/read the growing progress file with its own background + read-file loop until
the process exits — never block on a foreground tail. `tail --pid` is GNU-only (macOS/BSD lack it);
in PowerShell use a background job + `Get-Content -Wait`, or just take the foreground fallback below.

- **Context via a file, not stdin.** Backgrounding + redirection fights a stdin heredoc, so put the
  context in `.qodo/session-context.json` (auto-attached) or pass `--context-file .qodo/ctx.json`.
  `.qodo/` is always excluded from the reviewed diff and should be gitignored.
- **Launch it in the background** so your turn isn't blocked, then **read the growing per-run
  `progress.ndjson`** and give the user short status lines. Each line is one JSON
  object; translate by `kind` — never dump raw NDJSON at the user:
  - `cli.status` → relay its `message` verbatim-ish (it's already human-readable, e.g. *"Reviewing
    acme/widgets @ a1b2c3d4e — 3247B of local changes · auto depth"*).
  - `tool.activity` → relay `"<tool_name>: <outcome>"` (e.g. `clone_base: ok`).
  - `task.delta` → a heartbeat only (just a `task_id`, no content). Emit an occasional *"still
    analysing…"* — **not** one line per delta.
  - `qar.client.reconnecting` → relay the reconnect attempt and delay; include the structured
    `closeCode`/`errorCode` when present. `qar.client.reconnected` means the replacement transport
    opened; `resubscribeAttempts` is how many live tasks the SDK is re-attaching. On
    `qar.client.reconnect_failed`, report that retries were exhausted, then keep waiting for the
    process result envelope.
  - `task.done` → check `payload.status`: `completed` → *"review complete"*; anything else
    (`failed`/`cancelled`/…) → the run is over and it failed, so **stop relaying progress — but do
    not stop waiting.** Let the process exit and read the result file before you report anything.
    Same for `error`: note the `code` as an early signal and keep waiting. This channel drops the
    human-readable `message`/`hint` by design (they can land in CI logs), so the *reason* — including
    `closed_preview` and its enrollment hint — exists only in the result file. Reporting off the
    progress event alone hands the user a bare failure with the actionable part missing.
  - **Any other `kind`** (e.g. `agent.spawn`, `state.update`) → treat as a generic heartbeat like
    `task.delta`; never dump its raw JSON at the user. The set is open — new kinds may appear.
- **When the process exits, read that run's `result.json`** and follow the skill's result assessment (findings
  / `meta` / `hint`, or the `error` envelope — including `closed_preview`, which arrives here, not on
  the progress stream). Then delete only the unique directory created for that run, including on
  interruption or failure. Never reuse or remove a fixed/shared `.qodo/review.*` path.

The progress stream is deliberately **coarse** — lifecycle/status and tool outcomes, never finding
text or model output (it can land in CI logs). It tells the user *what stage the review is at*, not
what it found. Full event reference: `docs/qodo-review.md` ("Live progress on stderr").

**Fallback:** if you can't run a background command or tail a file in this runtime, just run the
plain foreground `qodo review --json …`, preserving the selected depth and attached context — progress is a UX nicety, not a
correctness requirement. Allow a multi-minute tool timeout (for example, `timeout: 600000` in
Claude Code). Don't fail the review over missing progress or downgrade depth to meet a short timeout.

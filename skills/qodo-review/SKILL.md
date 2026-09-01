---
name: qodo-review
description: Review your LOCAL changes before opening a pull request, using the qodo CLI — send your uncommitted/unpushed diff to Qodo's review engine along with the coding-session context (what you changed and why, plus links to the ticket/spec/design that drove it) that a forge-based reviewer can never see, then evaluate the findings and apply the fixes you approve (or pass `autofix` to apply directly). Use when asked to "review my changes before I push", "pre-PR review", "check this before I open a PR", "review my local diff", or "run qodo review".
owner: Qodo
metadata:
  vendor: qodo
  version: "1.9.5"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
---

# Pre-PR Review

## Description

Use the `qodo` CLI to review **local changes before you open a pull request**. `qodo review` diffs your working tree against a base branch, includes new/untracked files, and sends the diff plus any
**coding-session context** you supply to Qodo's review engine. It returns structured findings you then evaluate and — with the user's say-so (or `autofix`) — fix in code. Nothing is pushed and no
PR is created; only the base commit must already be on the remote (the reviewer clones it).

This is the **pre-PR** half of the review loop. After the PR exists, switch to resolving the PR's review findings instead.

## Prerequisites

- The Qodo CLI is installed and authenticated, and the review capability is enabled.
- The comparison base exists on the remote; local changes and context need not be pushed.
- The coding-session context and any ticket or design references are ready to attach.

## Instructions

Follow the workflow below: preserve notices, attach self-contained context, show progress, use a
suitable timeout, read the structured result, and act on findings.

## Handle a skill update notice

A Qodo command can emit `QODO_NOTICE <json>` to stderr while still succeeding. When `code` is
`qodo_skill_update_available`, keep the command's result and finish the current task. Then follow the
notice's `steps`: do read-only inventory first, resolve the installed Qodo package and scope, show the exact lifecycle-owner update command or UI action, and ask
once before any mutation. If the user declines, keep the current version usable.

Never invoke a different lifecycle owner, guess a placeholder, or install an optional package implicitly. After an approved update, ask for the host restart named by the notice; the current
session may still have the old skill loaded.

## Runtime compatibility gate

Resolve the executable using this skill's command-not-found fallback, then run `<qodo> --version`
with no provenance flags. This skill requires Qodo CLI **0.1.0-next.37 or newer**. If older or
unparseable, do not run `whoami`, `login`, or a review, and do not call it an auth failure. Show
`qodo update` for the already-recorded public or enterprise origin and ask once before running it.
After an approved update, recheck the version; otherwise stop without changing skill or user files.

## Quick start
You just wrote the code, so you hold the one input the reviewer can't get anywhere else: **why**.
Attach it on every run — write the session context first, then review:

```
qodo --version                                  # compatibility probe — run this FIRST
qodo read whoami --json --skill qodo-review --skill-version 1.9.5 --distribution skills-sh
qodo review --context-file - <<'EOF'         # review local changes vs origin/main, WITH context
{ "summary": "<what this change does and why>",
  "decisions": ["<a choice you made and its rationale>"] }
EOF
qodo review --context-file ctx.json          # same, context from a file
qodo review --ticket <TICKET_URL> ...        # add a ticket URL (repeatable)
qodo review --json ...                       # machine-readable findings
qodo review src/ test/ ...                    # limit to paths (git pathspecs)
qodo review --base origin/develop ...        # diff against a different base
qodo review --deep                           # thorough; use `qodo review --fast` instead for speed
qodo review                                  # BARE — only when there is truly nothing to say (rare)
qodo review --context-file ctx.json --async  # submit with context, print an operation id, exit 0
qodo review status <operation-id>            # collect an --async result (exit 2 = still running)
qodo review --help                           # exact flags (renders offline)
```

You can also keep `.qodo/session-context.json` (same JSON shape) updated at the repo root — it is auto-attached to every run, so even a bare `qodo review` carries your context. An explicit
`--context-file` overrides it; the file itself is never part of the reviewed diff. Don't commit it
(add `.qodo/` to `.gitignore` or `.git/info/exclude`).
Add `--json` to anything you parse, and a **long shell timeout** — runs take minutes (see below).
**Confirm the exact flags with `qodo review --help`** (offline) — the examples here are illustrative.

## Run it so the user sees progress (don't make them wait blind)

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
- **When the process exits, read that run's `result.json`** and proceed exactly as below (findings
  / `meta` / `hint`, or the `error` envelope — including `closed_preview`, which arrives here, not on
  the progress stream). Then delete only the unique directory created for that run, including on
  interruption or failure. Never reuse or remove a fixed/shared `.qodo/review.*` path.

The progress stream is deliberately **coarse** — lifecycle/status and tool outcomes, never finding
text or model output (it can land in CI logs). It tells the user *what stage the review is at*, not
what it found. Full event reference: `docs/qodo-review.md` ("Live progress on stderr").

**Fallback:** if you can't run a background command or tail a file in this runtime, just run the
plain foreground `qodo review --json …` (current behavior) — progress is a UX nicety, not a
correctness requirement. Don't fail the review over it.

**`qodo: command not found`?** That's PATH, not a missing install: GUI-launched agents (e.g.
the Claude Code desktop app) run shells with a minimal PATH. Retry with the absolute path
`~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo` if set) and keep using it for every `qodo`
command here. Only if that file is missing too is qodo actually not installed; tell the
user to obtain a checksum-pinned installer command from Qodo or their organization's
administrator. Installers are served from https://get.qodo.ai, but never invent a digest
or pipe an installer directly into a shell.

**Sandbox auth diagnostic.** In a sandboxed environment, if `qodo read whoami` fails for any reason
(including `Not logged in`), ask the user to approve one exact read-only retry of `qodo read whoami`
outside the sandbox before recommending login or refreshing tools. Keychain failures can be
reported as generic auth failures, so the sandboxed result alone is not diagnostic. That approval
applies only to this single diagnostic retry: do not reuse it, request persistent approval, or move
later Qodo commands outside the sandbox automatically. If the retry succeeds, continue with normal
per-command permission checks. If it still fails, follow the normal auth troubleshooting below.

## Give the run minutes, not seconds

`qodo review` clones your base and runs the pipeline server-side, so it routinely outlasts the
~2-minute default shell timeout a coding agent applies. Backgrounding it is the real answer — the
recipe is under "Run it so the user sees progress" above. When your runtime can't background and
you must go foreground, raise the timeout on that call: in Claude Code, `timeout: 600000` (10 min,
the max). Only `qodo review` needs this; the other qodo commands are fast.

There is no resume: a killed run is re-run whole, with `--fast` if you want it back sooner. The
`Reviewing <repo> @ <sha> — <N>B …` line is a useful landmark — it prints only once auth, diff, and
context parsing have all succeeded, so a death *after* it rules those three out as the cause.

## Fire-and-forget with `--async` (unattended, CI, parallel runs)

Everything above keeps a **live connection** open for the whole review. That is the right default
when someone is watching — it streams progress — but the connection is load-bearing: if it drops
and doesn't come back within ~2 minutes, the server **cancels the run**. In CI, over a flaky link,
or when your runtime can't hold a process open for minutes, that's a review you paid for and lost.

`--async` removes the connection from the critical path. It submits the review over HTTP, prints an
**operation id**, and exits 0 immediately. The run continues server-side whether or not your process
is alive; you collect the result later with `qodo review status <operation-id>`.

```
command -v jq >/dev/null 2>&1 || { printf '%s\n' 'This async recipe requires jq; install it or use the live qodo review flow.' >&2; exit 1; }
QODO_REVIEW_CONTEXT="${QODO_REVIEW_CONTEXT:-.qodo/session-context.json}"
[ -f "$QODO_REVIEW_CONTEXT" ] || { printf '%s\n' "Write the required review context to $QODO_REVIEW_CONTEXT (or set QODO_REVIEW_CONTEXT to its path)." >&2; exit 1; }
if ! submission="$(qodo review --context-file "$QODO_REVIEW_CONTEXT" --async --json --deep)"; then printf '%s\n' "$submission" >&2; exit 1; fi
if ! id="$(printf '%s\n' "$submission" | jq -er '.operation_id | select(type == "string" and length > 0)')"; then printf '%s\n' "$submission" >&2; exit 1; fi
qodo review status "$id" --json                                # collect it
```

Poll until it's done — the exit code is the whole protocol, so you never parse stdout to find out:

| Exit | Meaning | Do |
|---|---|---|
| `0` | Finished. Findings rendered — **identical** output to a live run (`{findings, meta}` under `--json`). | Act on the findings as usual. |
| `2` | Still running. | Wait and poll again. |
| `1` | Failed, canceled, expired, or no such operation. Read the `error` envelope. | Report it; re-run if appropriate. |

```
QODO_REVIEW_TMP="$(mktemp -d "${TMPDIR:-/tmp}/qodo-review.XXXXXX")"
cleanup_qodo_review() { [ -n "${QODO_REVIEW_TMP:-}" ] && [ -d "$QODO_REVIEW_TMP" ] && rm -r -- "$QODO_REVIEW_TMP"; }
trap cleanup_qodo_review EXIT; trap 'exit 130' INT; trap 'exit 143' TERM
while :; do status=0; qodo review status "$id" --json > "$QODO_REVIEW_TMP/result.json" || status=$?; case "$status" in 0) cat "$QODO_REVIEW_TMP/result.json" || exit 1; break ;; 2) sleep 15 ;; *) cat "$QODO_REVIEW_TMP/result.json" >&2; exit "$status" ;; esac; done
```

**Prefer `--async` when:**

- **Unattended / CI** — nobody is watching a progress stream, and a dropped connection must not kill
  a run that already cost minutes of compute.
- **Parallel reviews** — submit several (different repos, different bases) and collect them all
  afterwards, instead of serializing on one open connection each.
- **Long `--deep` reviews** — the ones most expensive to lose.
- **Your runtime can't background a process or hold a multi-minute timeout** — `--async` turns one
  long call into two short ones, which every runtime can do.

**What it costs — know these before you choose it:**

- **No streaming progress.** There are no progress events on this path — the run isn't attached to
  your process — so `--async` and `--progress` are rejected together rather than emitting a stream
  that never arrives. There is no intermediate status beyond "still running". If the user is
  watching and wants to see life, use the backgrounded `--progress` recipe above instead.
- **No human-in-the-loop.** This surface runs deterministic agents only; a review that asks for
  input fails instead of waiting. (`qodo review status` says so and tells you to re-run without
  `--async`.)
- **The result is kept for 1 hour** after the review finishes, then it is discarded. Collect it
  inside that window. Past it, `qodo review status` cannot tell "expired" from "never existed" or
  "belongs to someone else" — the runtime answers all three identically, on purpose — so it reports
  all of them and you re-run.
- **Re-submitting an unchanged diff replays, it does not re-run.** The submission is keyed by its
  content, so running `--async` twice on the same diff within the hour hands back the *first*
  operation id rather than starting (and billing) a second review. This is deliberate: it's what
  stops a lost response from double-running an expensive deep review. Any real edit changes the
  diff and starts a fresh run.
- **Hold on to the operation id.** It's the only handle to the result. Nothing else can recover it.

**The operation id is not the `trace` id.** `qodo` prints a `trace <id>` line on failures — that's
an OpenTelemetry id for support to diagnose a run with, and it cannot fetch anything. The
`operation_id` from `--async` is the resumable handle. Don't pass one where the other is wanted.

## Preflight

1. **Auth first.** Run `qodo read whoami`. After the sandbox retry above when applicable, a non-zero
   exit → tell the user to re-run the exact login command supplied by their installer,
   organization, or configured endpoint, then stop. With no custom endpoint, use `qodo login`;
   with an explicit endpoint, preserve it as `qodo login --auth-url <their-url>`. Never replace a
   custom deployment with the cloud default or invent an endpoint. `Not logged in` /
   `No tool catalog cached` require login. If `whoami`
   succeeds but the built-in `qodo review` command is unknown, the runtime is too old; ask the
   user to update the CLI from the official source. Re-login and catalog refresh cannot add this
   built-in command.
2. **Push the base.** The reviewer clones the base commit from the remote, so the base branch
   (default `origin/main`) must be pushed. If `qodo review` says the base isn't pushed, push it or
   pass a pushed `--base <ref>`. Your own local changes do NOT need to be committed or pushed —
   uncommitted edits and untracked new files are included automatically.
3. **Write your context.** Before running, capture the session narrative — a 2–3 sentence summary
   of what you changed and why, plus the decisions you made along the way — as the context JSON
   (stdin heredoc, a file, or `.qodo/session-context.json`). You always have this: you just wrote
   the code. Run bare only when there is genuinely nothing to say.

## What gets reviewed

`qodo review` gathers, all client-side:

- The **tracked diff** vs the base, plus **new/untracked files** (secrets, binaries, oversized,
  and gitignored files are filtered out and reported — never silently dropped).
- The **branch name**, **HEAD commit**, and a **description** synthesized from your commit messages.
- Any **ticket refs** and **session context** you attach (below).

It prints each finding as `[category/level] title — file`; `--json` emits `{ findings }`, adding `meta`
when the engine returns it.

`meta` (optional — older engines omit it) reports **coverage, not findings**: `meta.reviewers.ran` /
`.skipped` — which review dimensions ran vs **self-skipped for missing input** (e.g. `ui` self-skips
with no Figma link, `spec` with no spec URL, `cross_repo` with no relations); `meta.depth` — the tier
used; `meta.safety_net.reinjected` — how many must-fix findings the no-excuse floor forced back. Use
coverage to decide follow-up: if a dimension you care about self-skipped, re-run with the missing
input (a `--ticket`/spec/Figma URL) or `--deep`.

## Choose the review depth (per-run flag)

Depth is a per-run flag, fresh each time — there is no saved default. With **no flag** the depth is
**auto**: the CLI omits `depth` and the reviewer/deployment picks the tier. Make a judgment call:

- **`--fast`** — a quick single pass. Right for a small, low-risk change, a tight edit loop, or a
  quick sanity check before you push.
- **`--deep`** — a more thorough, slower pass. Reach for it on a risky or broad change (security-,
  concurrency-, migration-, or money-touching), a large diff, or the final review before you open a
  significant PR. Worth the extra latency when recall matters.
- **No flag (auto)** — omit both when you're unsure, or to let the system pick the tier.

`--deep` and `--fast` are mutually exclusive — passing both is an error.

**Reproducibility & cost.** `auto` picks a tier per run and isn't deterministic run-to-run, so in an
automated or repeatable loop pass an explicit `--fast`/`--deep`; keep `auto` for one-off interactive
checks. Manage cost with **depth**, not by dropping context: during a tight fix/re-review loop prefer
`--fast` and reuse the same context (the same ctx.json, or the ambient `.qodo/session-context.json` —
updated if the loop changed a decision); save `--deep` (a multi-model ensemble) for the final pre-PR
check. Context does add a second, no-excuse safety pass — that's the price of a calibrated review,
not a reason to run blind.

## Attach coding-session context (this is the point)

A forge reviewer only sees the diff. You know *why* the change was made — feed that in and the
review gets sharper (fewer false positives), because it can recognize intentional decisions instead
of guessing. A bare run isn't cheaper, it's blinder: the reviewer re-litigates every deliberate
choice you already made. Attach context on every run. Three channels:

- `--ticket <url>` — a ticket/issue/spec URL (repeat for several). Pass the **full URL** (e.g. a
  Jira `.../browse/KEY-123` or a Linear `linear.app/<team>/issue/…` link) so the reviewer can fetch
  it. Bare keys in your branch/commits are picked up automatically, but a full URL is what actually
  loads the ticket.
- `.qodo/session-context.json` at the repo root — the **ambient** channel (same JSON shape as
  below). Auto-attached to every run when present and no `--context-file` is given. Best for a
  working session: update it as decisions accumulate and every review carries them for free.
- `--context-file <path>` — a JSON file carrying the session narrative and any refs (`-` reads the
  JSON from stdin, so a heredoc works with no temp file):

  ```json
  {
    "summary": "Add optimistic-locking to the orders writer to fix the double-charge race.",
    "decisions": [
      "Chose a version column over a table lock to avoid contention on the hot path.",
      "Retries are capped at 3 then surfaced to the caller — deliberately not infinite."
    ],
    "context_refs": [
      { "kind": "ticket", "url": "https://acme.atlassian.net/browse/PAY-412" },
      { "kind": "spec", "url": "https://acme.example/specs/orders-v2", "label": "Orders v2 spec" }
    ]
  }
  ```

  `summary` + `decisions` become the review's understanding of intent. `context_refs` is a growable
  list of fetchable artifacts (`kind` is an open label — `ticket`, `spec`, `design`, …; ticket
  refs are used today, other kinds are accepted for later). Refs from `--ticket`, `--context-file`,
  and auto-extraction are merged and deduped.

## Write the context SELF-CONTAINED (the one rule that matters)

The reviewer sees **only** what you send — it has no access to your chat, your notebook, your
internal wiki, or a ticket you merely name. So:

- **Inline the rationale.** Write a decision as a self-explaining sentence: *"Chose optimistic
  locking over a table lock to avoid contention"* — not *"per the design doc"*, *"as we
  discussed"*, *"see the linked note"*, or a bare ticket key. A dangling reference is invisible to
  the reviewer and wasted.
- **Pass artifacts as fetchable refs, not name-drops.** If a ticket, spec, or design matters, add
  it as a `--ticket`/`context_refs` **URL** the reviewer can actually fetch — don't just mention
  its name in the summary.
- **Keep it tight.** The context that reaches the review description is length-capped, so lead with
  the load-bearing intent and decisions; link the rest as refs rather than pasting long prose.
- **Calibrate, don't suppress.** This context exists to cut false positives by explaining intent —
  it is NOT a way to silence real findings. Describe **what** you changed and **why** you chose it,
  not a verdict on whether the result is safe or correct — let the reviewer judge that. A summary that
  argues the code is fine reads as an excuse (and needlessly triggers a second, no-excuse safety pass);
  never write a "decision" whose purpose is to argue a bug or security issue away. The reviewer will
  (and should) still flag genuine problems.

## Present the review result

After reading the completed result file, show one compact summary before presenting findings:

```
# 🔍 Qodo Pre-PR Review

**Result:** <clean | findings need attention>
**Findings:** <N action required · N recommended · N informational>
**Coverage:** <reviewers that ran; name material skipped dimensions>
**Context:** <included | not provided>
---
```

Use only fields the result actually contains. Omit unavailable counts instead of guessing, and
do not call a review clean when a required reviewer failed or material coverage self-skipped.
Render the block once per completed review—not during progress, on gated/failed runs, or again
after each fix. Findings and the approval prompt follow below it.

## Act on the findings

Findings are a strong second opinion, **not gospel** — you hold context the tool doesn't. By
default your job is to **evaluate each finding and let the user decide what to apply** — don't edit
code unprompted.

**Evaluate each finding** against the actual code and the change's intent, and form a recommendation:

- **Sound and in scope** → a fix is warranted; note what you'd change.
- **Wrong, already-satisfied, or against a deliberate choice** → recommend skipping, with a
  one-line reason. Never degrade correct code just to clear a finding.
- **Unsure** → say so and give the call you'd lean toward.

**Present and ask (default).** Show every finding with its `[category/level]`, your evaluation, and
a one-line recommendation, then ask **in a single prompt** which findings to apply. Use whatever the
host gives you: a multi-select if it has one (Claude Code's `AskUserQuestion`, say), otherwise a
numbered list and "reply with the numbers to apply". One prompt either way — don't ask per finding.
**Nothing is pre-selected.** Mark which ones you recommend, but the user must actively choose: this
prompt is the last thing standing between a finding and an edit, so a bare Enter must apply nothing.
Apply only what the user picks (edit as normal, matching the surrounding style); report the rest as
skipped with your reason. Do not edit any code before the user has chosen.

**Autofix (skip the gate).** Only an **explicit `autofix` token** in the invocation (e.g.
`qodo-review autofix`) skips the prompt outright. Phrasing that merely sounds like opting in ("just
fix them", "don't ask me") is not enough by itself — reading intent wrong here edits code the user
never approved, which is the exact failure this gate exists to prevent. On inferred intent, name the
exact scope you'd apply and get one confirmation — "Reading that as autofix — apply the N fixes I
recommended?" — not "all N", which reads as the whole set and widens scope on the very ambiguity
this check exists to catch. Either way apply exactly what the evaluation decided and nothing beyond
it (fix the sound ones; skip the wrong/deliberate ones with a reason), and report what you applied
and what you skipped.

Re-run `qodo review` after applying to confirm the diff comes back clean. Commit/push per the user's
workflow — ask before pushing unless they've told you to.

## When a run takes minutes, or comes back canceled

A review is a backend agent run — on a large repo it takes **several minutes with no output
until it finishes**. One rule follows, and breaking it produces a failure that reads like
"this repo is too big to review". It isn't.

- **Keep the run alive and connected for its whole duration.** The CLI holds a streaming
  connection to the review; the server keeps a run whose client vanished for only a short grace
  window before cancelling it. So a harness that times out and kills the CLI kills the review —
  not instantly, but a couple of minutes later, which is why the cancel can look like it came out
  of nowhere. Background the run rather than foregrounding it under a tool timeout; the recipe is
  under "Run it so the user sees progress" above, and backgrounding is also what lets you stream
  status.

**Concurrent reviews of the same repo are fine.** Two runs on one repo do not supersede or cancel
each other — they are independent, and each returns its own findings. Don't serialize them for
safety that isn't needed.

The failure shapes are distinct, so read which one you got instead of guessing:

- **No output, the process died** → your side killed it (tool timeout, SIGTERM, Ctrl-C). The
  server-side run does not stop with it; it is cancelled a short while later, so this and the
  cancel below are often the same incident seen from two ends.
- **`review canceled by the server …`** → the server ended the run. When it says the connection
  dropped, that's the cause: the CLI lost its stream and did not get back in time. Not a size,
  complexity, or concurrency limit.
- **`review ended without a result (no task.done)`** → the stream dropped mid-run.
- **`review failed: <detail>`** → a real backend failure; the detail says what.

For the first three, **re-run once, uninterrupted, before concluding anything** — a cancel says
nothing about whether your diff is reviewable.

## If the run is gated: closed preview

`qodo review` is currently in **closed preview** — the server rejects runs from organizations that
aren't enrolled. A gated run exits non-zero with a stable machine-readable error: `--json` emits
`{"error": {"code": "closed_preview", "message": ..., "hint": ...}}`; without `--json` the same
message and hint print as prose.

On `closed_preview`:

1. **Surface the `message` and `hint` to the user unchanged** (don't paraphrase or truncate;
   the `--json` payload carries them verbatim, while the CLI's prose output strips terminal
   control characters), then
2. **STOP.** The gate is an entitlement, not a transient fault — retrying, backing off, watching,
   or looping **cannot** succeed until the user's organization is enrolled. Do not re-run
   `qodo review` unless the user says enrollment happened (after enrollment, access activates
   within ~10 minutes; no re-login needed).

Only the review itself is gated — auth (`qodo read whoami`) and the other qodo commands are unaffected.

## Configuration

Use `--json --progress` for observable foreground runs, `--async` only for deliberate detached
runs, and an explicit `--base` when origin/main is not correct. Stamp exact skill/version/
distribution provenance on the first Qodo call and keep session context out of the reviewed diff.

## Error Handling

Read the structured result even after a non-zero command. Preserve closed-preview, cancellation,
rate-limit, connection, and tool-loop states; follow the bounded recovery above and never discard
context or widen authority merely to obtain a green result.

## Guardrails

- **Pre-PR only.** This reviews local changes before a PR. Once a PR is open, resolve the PR's
  review findings instead — that path re-reviews each pushed commit.
- **No forge writes.** `qodo review` reads your local diff and returns findings; it never pushes,
  comments, or opens a PR. Resolving a finding means editing code, not posting anywhere.
- **The base must be pushed;** your local work need not be. New/untracked files are reviewed by
  default; secrets/binaries/oversized/gitignored files are filtered and reported.
- **Don't guess creds or the base** — resolve auth first, and pass `--base` when it isn't
  `origin/main`.
- **Background long runs so the connection survives** — a canceled run means it was interrupted or
  lost its connection, never that the repo is too big (see "When a run takes minutes" above).
  Concurrent reviews of the same repo don't interfere; no need to serialize them.
- **Never strip context to beat the clock.** Dropping `--context-file` doesn't make a run faster —
  it just buys a worse review. Give it more time, or `--fast`; keep the context either way.
- An `MT-TOOL-LOOP` or `MT-RATE-LIMITED` error means stop/back off and change approach, not retry.
- A `closed_preview` error means the org isn't enrolled in the preview — surface message + hint to
  the user and stop; never retry or loop on it (see "If the run is gated" above).

Lead with the bottom line — how many findings, how many you applied, what's left and why — then the specifics. A short, accurate status beats a wall of finding text.

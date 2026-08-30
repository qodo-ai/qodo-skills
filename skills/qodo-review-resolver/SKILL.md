---
name: qodo-review-resolver
description: Read or resolve a pull request's Qodo review with the qodo CLI — fetch the structured status, reviewed commit SHA, and findings for ANY PR as JSON, then optionally resolve open findings in code and record each outcome, once or in a watch loop until clean. Use this — never `gh`/`curl` scraping of review comments — for "is the review clean on PR #N", "get Qodo's findings for <pr> as JSON", "what did Qodo flag", "is this review up to date with head", "check before merging", "resolve my PR review", "fix the review findings", or "babysit this PR until it's clean".
owner: Qodo
when_to_use: When you need to read or act on a pull request's Qodo review — check where it stands, see what it flagged, gate a merge on it being clean at head, or fix the open findings — for any PR, not just your own. It reads the review through qodo's managed tool (structured, git-provider-agnostic), so use it instead of scraping the rendered PR review comments with `gh`/`curl` (lossy, provider-specific, and easy to read stale against the head commit). It resolves findings in local code and then records the outcome on each finding through qodo's own tools (dismiss / mark-implemented, which clear the merge-policy block); it never posts to the git forge itself. Skip it for reviewing code you're writing locally before any PR exists (that's the pre-PR review), and for non-review PR chores (merging, labels, descriptions).
metadata:
  vendor: qodo
  version: "1.4.3"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
arguments:
  - name: autofix
    description: Resolve the recommended fixes directly without asking. Omit to evaluate the findings and let the user pick which to resolve.
    optional: true
---

# Read & Resolve Findings

## Description

Use the `qodo` CLI to read a pull request's **review session** — its status, the commit that
was reviewed, and every finding with its resolution status — for **any** PR (yours or someone
else's). Reading alone is a valid use: stop after the read to report where a review stands or
what it flagged (e.g. to gate a merge on it being clean at head). To go further, **resolve the
open findings in code**, applying your own judgment (the review is a strong second opinion, not
gospel) — by default you evaluate the findings and let the user pick which to apply (pass `autofix`
to apply directly), run once (report + resolve what the user approves) or as a watch loop (resolve →
let Qodo re-review the new commit → repeat until clean). Then **record the outcome** on the findings
you settled — `mark-implemented` for ones you fixed, `dismiss` for ones the user agreed to close
without a code change. That is what clears the merge-policy block those findings hold; skip it and
the review stays red until a human clicks through the PR. You still never post to the forge
yourself: the status tools write Qodo's review DB and Qodo reconciles the PR comments. (Plain
git/forge *metadata* reads — `git rev-parse HEAD`, `gh pr view --json headRefOid` — are fine and in
fact required for the freshness check below; the "don't scrape" rule is about qodo, not your shell.)

## Prerequisites

- The Qodo CLI is authenticated and exposes the structured PR-review session tools.
- The exact PR URL and its current head SHA can be resolved without scraping review comments.
- Any write to a finding has the user's explicit authority or the skill's explicit `autofix` scope.

## Instructions

Follow the detailed workflow below: fetch structured state, require a completed exact-head review,
present open findings, apply only approved fixes, and record only outcomes actually settled.

> To check a review's status or findings, always run the `qodo` read command below — do **not**
> fetch the rendered PR review **comments** with `gh`/`curl`. The comment UI is lossy, provider-
> specific, and easy to read stale against the head commit; the tool returns the reviewed
> `commit_sha`. To judge freshness, compare that `commit_sha` to the PR **head** — which you know
> directly for a PR you just pushed (`git rev-parse HEAD`), or read as plain forge *metadata*
> (`gh pr view <pr> --json headRefOid`, `git ls-remote`) for any other PR. This rule is only about
> reading the **review** (don't scrape its comments) — not about forbidding forge metadata like the
> head SHA.

## Handle a skill update notice

A Qodo command can emit `QODO_NOTICE <json>` to stderr while still succeeding. When
`code` is `qodo_skill_update_available`, keep the command's result and finish the current
task. Then follow the notice's `steps`: do read-only inventory first, resolve the installed
Qodo package and scope, show the exact lifecycle-owner update command or UI action, and ask
once before any mutation. If the user declines, keep the current version usable.

Never invoke a different lifecycle owner, guess a placeholder, or install an optional package
implicitly. After an approved update, ask for the host restart named by the notice; the current
session may still have the old skill loaded.

## Runtime compatibility gate

First resolve the executable using the `qodo: command not found` fallback below. Before any other
Qodo command, run `<qodo> --version` exactly as shown, with no provenance flags.
This unadorned probe is intentionally compatible with older Qodo CLIs. This skill requires Qodo
CLI **0.1.0-next.37 or newer**.

If the version is older or cannot be parsed, do not run `whoami`, `login`, or a managed tool and
do not describe the failure as an authentication problem. Explain that the skill is newer than the
runtime, show `qodo update` as the update command for the runtime's already-recorded origin, and ask
once before running it. For a customer deployment, keep its organization-provided update origin;
never switch it to the public service. After an approved update, rerun the unadorned version probe
and continue only when it satisfies the minimum. If the user declines or the update fails, stop with
the current skill and user files unchanged.

## Quick start

```
qodo --version                                                       # compatibility probe — run this FIRST
qodo read whoami --json --skill qodo-review-resolver --skill-version 1.4.3 --distribution skills-sh
qodo read pr-review-session findings --pr-url <PR_URL> --json       # the review session for a PR
qodo pr-review-session mark-implemented --finding-ids <id>,<id> --explanation "..." --json
qodo pr-review-session dismiss --finding-ids <id> --reason intentional --explanation "..." --json
qodo read tools pr-review-session --json                            # exact safe tools + flags (offline)
```

Add `--json` to anything you parse. **Confirm the exact tool names, flags, and read/write status
with `qodo read tools pr-review-session [<tool>] --json`** (renders offline) — the names above
are illustrative, not guaranteed current.

`unknown command` on `dismiss`/`mark-implemented` after authentication may be a stale local tool
catalog — refresh once as described below. If the commands are still absent, the workspace does
not currently expose PR-review writes; report that capability boundary instead of looping.

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

## Preflight

1. **Auth first.** Run `qodo read whoami`. After the sandbox retry above when applicable, a non-zero
   exit → tell the user to run `qodo login`, then stop. Never guess creds. The tool only exists
   *after* login, so treat `Not logged in` or `No
   tool catalog cached` as "run `qodo login`", and don't retry before they have.
   **An `unknown command`/`unknown option` while `whoami` SUCCEEDED is not an auth failure.** Run
   `qodo tools --refresh` once and re-check `qodo read tools pr-review-session --json`. If the write command
   remains absent, report that this account/workspace currently has read-only review capability;
   do not re-login, retry indefinitely, or substitute a forge comment for the structured write.
2. **Resolve the PR.** Use the PR URL the user gives. If they don't name one and you're inside
   a git repo, infer the open PR for the current branch and **confirm it with the user before
   acting**. Never guess a PR URL.
3. **Bind edits to the checkout.** Report-only reads may target any PR. Before any local fix,
   resolve the PR repository from provider metadata and the current checkout repository from its
   `origin`; normalize both to the full case-insensitive `owner/repo` identity. They must match
   exactly. A missing/ambiguous origin or mismatch means stop and ask the user to open the correct
   checkout — never apply a finding from one repository to another worktree. Repeat this check if
   the target PR changes during a watch loop.

## Fetch the review session

`qodo read pr-review-session findings --pr-url <PR_URL> --json` returns:

- `review_session` — the latest review run: `status`, `commit_sha` (**the last commit included in
  the review** — the code these findings describe), `started_at`. **`null` = the PR has no review
  yet** — tell the user and stop (nothing to resolve).
- `findings[]` — every current finding, each with: `title`, `description`, `category`,
  `action_level` (`action_required` > `remediation_recommended` > `informational`),
  `attribution_status`, `git_sha`, `review_run_id`, `comment_id` / `inline_comment_id`.

`finding_count: 0` with a non-null session = a clean review.

## Read the session state FIRST (before trusting any finding)

The `review_session` tells you *whether the findings are real yet and what code they cover* —
check it before acting:

- **Is a review still running?** If `status` is not a terminal/`completed` state (e.g. `started` /
  in-progress), a review is **mid-flight** — the findings are provisional and will change. Do NOT
  resolve them yet; poll `qodo read pr-review-session findings … --json` until `status` is `completed`.
- **What commit do the findings describe?** `review_session.commit_sha` is the last commit the
  review included. If it's **behind the PR head**, the findings are **stale** — they don't reflect
  your latest code. Either the review hasn't run on the new commit yet (wait) or you're looking at
  an old run. Only trust findings when the session is `completed` AND its `commit_sha` is the commit
  you care about (the head, in a watch loop).

In short: act only on a **completed review of the current commit**. A running review or a
lagging `commit_sha` means wait, don't fix.

## Present the review state

After fetching the session and comparing its commit to the PR head, show this once:

```
# 🔎 Qodo PR Review

**PR:** <owner/repo#number>
**Review:** <completed and current | running | stale | not found>
**Findings:** <N open · N closed, grouped by action level when useful>
**Reviewed commit:** <short SHA, or "none">
---
```

This block exposes the freshness gate before anyone acts. Derive every field from the structured
session and forge head; never label a review current unless it is completed at the exact head.
Render it once per fetched state, not again after every edit or status write. Resolution details
and remaining findings follow below it.

## Triage

- **Open vs done is `attribution_status`**, and it is NOT a three-way field — it carries the raw
  stored value, so matching only `pending` silently drops real work:
  - **OPEN — work these:** `pending`, `partial_implementation`, `not_implemented`,
    `focus_areas_edited`. The last three are re-attributions of a finding that is still unresolved
    (a partial fix is still an open finding).
  - **CLOSED — leave these:** `full_implementation`, `dismissed`, `detected_after_merge`, `outdated`.
  - `action_level` is **severity**, not open-vs-closed. A closed finding can still be
    `action_required`.
- **Order by `action_level`:** `action_required` first, then `remediation_recommended`; treat
  `informational` as optional and surface it, don't necessarily fix it.
- Group open findings by file so you edit each file once.

## Honor the user's instruction (optional scope)

If the user gave an instruction, treat it as a **filter over the open findings** and act only on
the matches — don't widen it:

- **By action level** — "resolve the action-required findings" → only `action_level == action_required`;
  "everything actionable" → `action_required` + `remediation_recommended`.
- **By category** — "just the security findings" → `category == Security` (same for correctness,
  performance, etc.).
- **By specific finding** — "fix finding #3" / "the SQL-injection one" → match by `id` or `title`.
- **Report-only** — "what did the review find?" / "is it clean?" → summarize the findings and their
  statuses, change no code.

No instruction → default to presenting for approval open `action_required` then
`remediation_recommended`, and surface (don't auto-fix) `informational`. When an instruction is
ambiguous, state the scope you picked in one line before acting, so the user can redirect. Always
report which findings you **skipped** and why (out of scope / dismissed / informational) — never
silently drop one.

## Two modes

Each round follows the present-and-ask gate from **Resolve a finding** — evaluate, present, and let
the user pick which findings to resolve — unless `autofix` is in effect, which lets you apply the
recommended fixes without prompting. Either way, ask before pushing unless told otherwise.

**Once (default).** Fetch → evaluate every open finding (triage — all four OPEN statuses, not just
`pending`) → present + ask (or apply directly under `autofix`) → resolve the chosen ones in code →
commit/push per the user's workflow → **record the outcome**
(`mark-implemented` for what you fixed; `dismiss`, with the user's explicit go, for what they
agreed to close without a change) → summarize what you resolved and what remains (e.g. skipped /
dismissed / informational). Stop. Don't loop unless asked. Triage covers
**all** open findings, but the picker only *offers* the actionable set —
`action_required` then `remediation_recommended` — with `informational` surfaced separately,
matching the default scope above; put `informational` in the picker only when the user asks.
(Offering isn't selecting: every box starts unticked.)

**Watch until clean** (when the user says "babysit" / "keep going until it's clean"). `autofix` is
what makes this loop autonomous — without it you still present + ask each round. After you resolve
findings and the fix commit is pushed, Qodo re-reviews the *new* commit — so:

1. Note the PR's current head SHA — the commit you just pushed (`git rev-parse HEAD`), or, for a
   PR you didn't push, read it as forge metadata (`gh pr view <pr> --json headRefOid`). That's a
   metadata read, not review-comment scraping — it's fine.
2. Poll `qodo read pr-review-session findings … --json` until the review is **`completed` AND its
   `commit_sha` equals that head SHA**. Until both hold, the findings are stale or provisional
   (a review is still running, or it describes the pre-fix commit) — do not act on them.
3. When fresh: if any OPEN findings remain (all four statuses — a `partial_implementation` is
   still open), resolve them and repeat; if none remain, report the
   review clean and stop.
4. Bound it: stop after a few rounds with no progress and hand back to the user rather than
   looping forever.

## Resolve a finding

Qodo's findings are a strong second opinion, **not gospel** — you and the user hold context it
doesn't (the change's intent, project conventions, what's deliberate), and tooling can be wrong
(a finding that misreads intent, or a status/attribution glitch). By default your job is to
**evaluate each finding and let the user decide what to apply** — don't edit code unprompted.

**Evaluate each finding** against the actual code and the PR's intent, and form a recommendation:

- **Sound and in scope** → a fix is warranted; note what you'd change (read `title` +
  `description`, locate the code — the `qodo-codebase-wisdom` skill's read tools help when it isn't
  local).
- **Wrong, already-satisfied, or against a deliberate choice** → recommend skipping, with a
  one-line reason. Never degrade correct code just to silence a finding.
- **Unsure** → say so and give the call you'd lean toward.

**Present and ask (default).** Show each open, in-scope finding with its
`action_level`/`category`, your evaluation, and a one-line recommendation, then ask **in a single
prompt** which findings to resolve. Use whatever the host gives you: a multi-select if it has one
(Claude Code's `AskUserQuestion`, say), otherwise a numbered list and "reply with the numbers to
resolve". One prompt either way — don't ask per finding. **Nothing is pre-selected.** Mark which
ones you recommend, but the user must actively choose: this prompt is the last thing standing
between a finding and an edit, so a bare Enter must resolve nothing. Resolve only what the user
picks (edit as normal, matching the surrounding code); report the rest as skipped with your reason.
Do not edit any code before the user has chosen.

**Autofix (skip the gate).** Only an **explicit `autofix` token** in the invocation (e.g.
`qodo-review-resolver autofix`) skips the prompt outright. Phrasing that merely sounds like opting
in ("just fix them", "don't ask me") is not enough by itself — reading intent wrong here edits code
the user never approved, which is the exact failure this gate exists to prevent. On inferred intent,
name the exact scope you'd apply and get one confirmation — "Reading that as autofix — resolve the
N findings I recommended?" — never "resolve all N", which reads as the whole set and widens scope on
the very ambiguity this check exists to catch. Either way apply exactly what the evaluation decided
and nothing beyond it (findings are usually right, but you're the engineer in the loop, not a rubber
stamp), and report what you resolved and what you skipped.

Commit/push per the user's workflow — ask before pushing unless they've told you to.

**`attribution_status` is the intended signal** — a fixed finding is re-attributed to
`full_implementation` by the next review on its own, so after pushing, re-fetch and work only what's
still open. But it's tooling and can glitch: if a finding stays open after a fix you're confident
in, or a status plainly contradicts the code, don't loop re-fixing it — flag the discrepancy to the
user and move on. (Resolving converges over rounds; a fix can also surface genuinely new findings,
which the watch loop picks up.)

## Record the outcome

Closing a finding is a **write** — it updates Qodo's review DB, restyles the finding's PR comments,
re-renders the review summary, and releases the merge-policy block that finding holds. Two commands,
and the distinction between them is the whole point: one says *the code changed*, the other says
*the code didn't and here's why*. Never use one to mean the other.

```
qodo pr-review-session mark-implemented --finding-ids <id>,<id> --explanation "what you changed" --json
qodo pr-review-session dismiss --finding-ids <id>,<id> --reason <reason> --explanation "why" --json
```

- **Batch per PR, one call.** Reconciliation runs once per call, not once per finding — so all the
  findings you implemented go in one `mark-implemented`, and all the ones sharing a dismissal reason
  go in one `dismiss`. Up to 100 ids.
- **`mark-implemented` only for code you actually changed and pushed.** It clears the merge gate
  without a review having verified the fix, so a wrong claim ships an unfixed finding as fixed. If
  another review round is going to run anyway, prefer letting it re-attribute the fix itself; reach
  for this when no further round will run before merge, or the gate must clear now.
- **`dismiss` needs the user's explicit go, per finding, every time — `autofix` does NOT cover it.**
  `autofix` is consent to *edit code*, which the next review re-checks; a dismissal closes a finding
  the review still believes in, is visible to the team, and nothing re-opens it. Present what you
  propose to dismiss and why, and dismiss only what the user names.
- **`--reason`** (required): `false_positive` (the finding is wrong) · `intentional` (the code is
  deliberate and correct) · `deferred` (real, but out of scope for this PR) · `rejected` (understood
  and declined). Always add `--explanation` — a reviewer reads it later without your context.
- **Read `results` per finding, don't assume the call succeeded as a whole.** It is a 200 even when
  individual ids fail: `not_found` (wrong id or wrong workspace) and `conflict` (already closed, or
  not linked to a PR) are terminal — don't retry them. `reconciled: false` means the DB change
  landed but the PR-side update didn't; re-running the same command is safe and idempotent, and the
  PR self-heals on its next review regardless. `already_dismissed` / `already_implemented` report the
  **stored** reason — a replay never overwrites the original.

## Example

**User: "Resolve the action-required findings on https://github.com/acme/api/pull/318"**

1. `qodo read whoami` → logged in.
2. `qodo read pr-review-session findings --pr-url https://github.com/acme/api/pull/318 --json`
   → `review_session`: `status: completed`, `commit_sha: a1b2c3d` (= the PR head, so findings are current);
   `findings`: 3 open (2 `pending`, 1 `partial_implementation`) — 2 `action_required`, 1 `informational`.
3. Instruction filters to `action_required` → work those 2; the informational one is out of scope (report it, don't fix).
4. Evaluate each: *"SQL built via string interpolation"* → real → recommend parameterizing the query in
   `db/orders.py`. *"Missing timeout on the outbound call"* → the client already sets a default timeout
   upstream → already satisfied → recommend skipping with that reason.
5. Present both with those recommendations and ask (multi-select) which to resolve — both unticked, the SQL
   one marked *recommended*. Apply what the user picks, then report: "Resolved the SQL finding
   (parameterized the query in `db/orders.py`). Skipped the timeout one — already set upstream — and 1
   informational (out of scope). Push and I'll re-check, or say 'watch' to loop until the review is clean."
   (Had the user said `resolve … autofix`, I'd have applied the recommended fix directly, no prompt.)

## Configuration

Use `--json`, compare `review_session.commit_sha` with forge head metadata, and stamp the exact
skill/version/distribution provenance on the first Qodo call. Read and write capabilities are
discovered from the installed CLI catalog; rendered forge comments are never the data source.

## Error Handling

Treat null sessions, in-progress or stale commits, missing write capabilities, rate limits, and
tool-loop errors as explicit states. Preserve them in the report and never close a finding merely
to make the review appear clean.

## Guardrails

- **Freshness = a completed review of the reviewed commit, not a timestamp.** Findings describe
  `review_session.commit_sha` and are only final once `status` is `completed`. After any push, treat
  them as stale until a `completed` review's `commit_sha` catches up to the PR head — otherwise
  you'll act on a mid-flight review or "fix" a commit the findings don't describe.
- **Never post to the forge yourself.** The only writes you make are `dismiss` /
  `mark-implemented`, which go through Qodo and let it reconcile the PR. Do not call any forge-write
  tool (comments, approvals, labels, description) to "resolve" a finding — resolve it in *code*, then
  record the outcome.
- **You may decline a finding you judge wrong** (with a clear reason). Dismissing it in the system is
  now possible but is the **user's** call, not yours — propose it, name the reason, and act only on
  their explicit go. On a real disagreement the user is the arbiter.
- **Don't close what you didn't settle.** A finding you skipped for scope stays open — report it as
  skipped rather than dismissing it as `deferred` to make the list look clean.
- **Don't guess** the PR URL — resolve it first; a `null` session means no review yet.
- An `MT-TOOL-LOOP` or `MT-RATE-LIMITED` error means stop/back off and change approach, not retry.

Lead with the bottom line — how many findings, how many you resolved, what's left and why —
then the specifics. A short, accurate status beats a wall of finding text.

---
name: qodo-review-resolver
description: Read or resolve a pull request's Qodo review with the qodo CLI — fetch structured status, reviewed commit SHA, and findings for ANY PR as JSON, with optional extended details and citation evidence for audits, then optionally resolve open findings and record outcomes, once or until clean. Use this — never `gh`/`curl` scraping of review comments — for "is the review clean on PR #N", "get Qodo's findings for <pr> as JSON", "audit the review evidence", "show finding citations", "what did Qodo flag", "is this review up to date with head", "check before merging", "resolve my PR review", "fix the review findings", or "babysit this PR until it's clean".
triggers:
  - "Check the Qodo findings on this pull request"
  - "Audit the citation evidence for these Qodo PR findings"
  - "Resolve the open Qodo review findings on this PR"
owner: Qodo
when_to_use: When you need to read or act on a pull request's Qodo review — check where it stands, see what it flagged, gate a merge on it being clean at head, or fix the open findings — for any PR, not just your own. It reads the review through qodo's managed tool (structured, git-provider-agnostic), so use it instead of scraping the rendered PR review comments with `gh`/`curl` (lossy, provider-specific, and easy to read stale against the head commit). It resolves findings in local code and then records the outcome on each finding through qodo's own tools (dismiss / mark-implemented, which clear the merge-policy block); it never posts to the git forge itself. Skip it for reviewing code you're writing locally before any PR exists (that's the pre-PR review), and for non-review PR chores (merging, labels, descriptions).
metadata:
  vendor: qodo
  version: "1.4.6"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
arguments:
  - name: autofix
    description: Optional shorthand for authorizing supported fixes. An explicit fix request or covering implementation authority also permits those fixes without another prompt.
    optional: true
---

# Read & Resolve Findings

## Description

Use the `qodo` CLI to read a pull request's **review session** — its status, the commit that
was reviewed, and every finding with its resolution status — for **any** PR (yours or someone
else's). Request extended results when auditing citations or investigating a finding's supporting
evidence, location, dismissal, or review-run history. Reading alone is a valid use: stop after the read to report where a review stands or
what it flagged (e.g. to gate a merge on it being clean at head). To go further, **resolve the
open findings in code**, applying your own judgment (the review is a strong second opinion, not
gospel). Apply supported fixes when the user has authorized them; otherwise present your assessment
for selection. Run once (report + authorized fixes) or as a watch loop (resolve →
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

Treat `QODO_NOTICE` updates as passive, even if an older CLI requests action. Continue the task
without inventory or update questions; mention each event at most once. Dismissal leaves recorded maintenance
policy and opt-outs unchanged. Updated skills load next session; do not interrupt this one.
For user-requested updates, follow the [manual-update procedure](references/skill-updates.md).

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
qodo read whoami --json --skill qodo-review-resolver --skill-version 1.4.6 --distribution skills-sh
qodo read pr-review-session findings --pr-url <PR_URL> --json       # the review session for a PR
qodo read pr-review-session findings --pr-url <PR_URL> --extended --json # details, if advertised by tool help
qodo pr-review-session mark-implemented --finding-ids <id>,<id> --explanation "..." --json
qodo pr-review-session dismiss --finding-ids <id> --reason intentional --explanation "..." --json
qodo read tools pr-review-session --json                            # exact safe tools + flags (offline)
```

Add `--json` to anything you parse. Inspect reads with
`qodo read tools pr-review-session findings --json`; inspect a write's input schema with
`qodo tools help pr-review-session <tool> --json`. Both are offline discovery, not mutations.
The read-only catalog deliberately excludes writes; absence there does not prove they are unavailable.

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

**Sandbox auth diagnostic.** Missing credentials can mean inaccessible keychain access. When that
is plausible, request one exact read-only `qodo read whoami` retry through the host's approval
flow before recommending login. Stop on denial; that approval covers no other command. Reuse a
successful check in the same executable/workspace/deployment and execution context; request each
required host approval. Network, TLS, service, and explicit authorization failures retain their
own diagnosis, not a login recommendation or an automatic sandbox bypass.

## Preflight

1. **Auth and catalog.** Run `qodo read whoami` unless a successful check still covers this
   execution context. After the sandbox diagnostic when applicable, only explicit missing credentials
   call for login: preserve the organization's exact login command/endpoint, never guess or switch
   a customer deployment to Cloud. `No tool catalog cached` is not proof of missing credentials;
   refresh once with `qodo tools --refresh` and retry the check. Other failures retain their error
   and stop this workflow. After identity succeeds, an unknown managed command permits one catalog
   refresh and schema recheck. If still absent or `tool_unavailable`, report the missing capability;
   do not repeat login or refresh.
2. **Resolve the PR.** Use the PR URL the user gives. If they don't name one and you're inside
   a git repo, infer the open PR for the current branch and **confirm it with the user before
   acting**. Never guess a PR URL.
3. **Bind edits to the checkout.** Report-only reads may target any PR. Before any local fix,
   resolve the PR repository from provider metadata and the current checkout repository from its
   `origin`; normalize both to the full case-insensitive `owner/repo` identity. They must match
   exactly. A missing/ambiguous origin or mismatch means stop and ask the user to open the correct
   checkout — never apply a finding from one repository to another worktree. Use the PR branch
   or an isolated worktree for that PR, with local HEAD at the reviewed head (or a verified descendant
   produced by this same fix workflow). Merely having the commit in the repository is insufficient.
   Inspect local differences and preserve unrelated edits; never reset or switch a dirty worktree
   to satisfy this check. Repeat these checks if the target PR changes.

## Fetch the review session

`qodo read pr-review-session findings --pr-url <PR_URL> --json` returns:

- `review_session` — the latest review run: `status`, `commit_sha` (**the last commit included in
  the review** — the code these findings describe), `started_at`. **`null` = the PR has no review
  yet** — tell the user and stop (nothing to resolve).
- `findings[]` — every current finding, each with: `title`, `description`, `category`,
  `action_level` (`action_required` > `remediation_recommended` > `informational`),
  `attribution_status`, `git_sha`, `review_run_id`, `comment_id` / `inline_comment_id`.

Zero findings supports a clean verdict only for a complete, completed review at the current PR head.

### Extended results for audits and investigation

Keep compact reads for routine status polling. When the user needs supporting evidence or more
detail, inspect `qodo read tools pr-review-session findings --json`. Only if the schema declares
the `extended` boolean, use `qodo read pr-review-session findings --pr-url <PR_URL> --extended --json`.
The tool/API input is `extended: true`; omitted or false keeps the compact response.
This reads more stored data; it does not rerun or deepen the review.

Extended results add finding locations and code snippets, dismissal reasons/explanations,
`review_runs`, and `findings[].evidence` with `explanation` and `citations`. Preserve each
citation's source type, source reference, text and source-specific metadata in an audit output.
Correlate evidence with that finding's `id`, `git_sha`, `review_run_id` and `review_source`;
current findings can originate in earlier runs than `review_session`.

Null evidence means unavailable; an empty citations list contains no recorded citations. An
absent evidence field can indicate an older backend: report that limitation without claiming
the finding has no supporting evidence. If `extended` is absent from the catalog, follow the
existing one-refresh recovery and check again; if still absent, report that extended reads are
unavailable and keep using compact reads. Never send `--extended` to a catalog that lacks it;
do not invent an alternative flag or substitute scraped comments.

If the result has `qar_operation_result_truncated: true`, report an incomplete read, not an
empty or clean review. Extended results describe current findings and recorded runs, not an
immutable history of every finding revision. Apply the freshness checks below before acting.

## Read the session state FIRST (before trusting any finding)

The `review_session` tells you *whether the findings are real yet and what code they cover* —
check it before acting:

- **Is a review still running?** The API reports a running review as `started`; that is the polling state. For a status-only
  request, report that state and return; poll only when waiting is part of the requested task.
  `failed`, `aborted`, `skipped`, and `superseded` are non-success terminal states: report them
  and stop the loop. An unknown status is not success or permission to poll indefinitely.
- **What commit do the findings describe?** `review_session.commit_sha` is the last commit the
  review included. If it's **behind the PR head**, the findings are **stale** — they don't reflect
  your latest code. Either the review hasn't run on the new commit yet (wait) or you're looking at
  an old run. Only trust findings when the session is `completed` AND its `commit_sha` is the commit
  you care about (the head, in a watch loop).

Act only on a **completed review of the current commit**. A running or stale review cannot
authorize finding resolution. In watch mode, respect retry delays, recheck the forge head before
claiming clean, and stop if the review makes no progress rather than polling indefinitely.

## Present the review state

Use natural prose: **outcome → contextual explanation of changes and dispositions → verification
→ remaining work**. For report-only requests, lead with the current review state and the impact
of remaining findings. Credit Qodo once for the specific concerns its review surfaced; you own
the final assessment and recommended action. No branded headings, emoji banners, slogans,
footers, or repeated summary blocks. Use short issue titles or lists when useful.

For each finding, explain what could happen, under which conditions, and why it matters to the
user's intended change. Evaluate it against the code and available coding-session decisions and
constraints; retrieve PR context when needed, never invent a missing session. Cite the evidence
and preserve finding references and reported category/level separately from your recommendation.
Own the fix, dismissal, or investigation decision and its rationale. A deliberate choice supports
dismissal only when the implementation enforces its assumptions. Keep the tone collaborative
and factual; do not routinely qualify Qodo's capability. Follow the existing scope and approval
gates for edits and disposition writes; your technical assessment does not grant permission.

Name the PR, review status, and reviewed commit from structured state; compare with the forge
head before acting. Make stale, running, failed, or missing reviews explicit. Distinguish **code
changed**, **disposition recorded**, and **updated code reviewed**. Tests passing or a status
write succeeding does not establish a clean review of the updated commit. Only a completed
review at the current head can support that verdict; report remaining findings and missing
verification honestly. For example: “Addressed [risk] Qodo identified by [change], preserving
[user decision]. [Verification]. The latest review covers [old SHA]; review of [head SHA] remains
outstanding.” Use only actual outcomes. In watch mode, report meaningful state changes without
repeating the assessment on every poll or status write.

## Triage

- **Open vs done is `attribution_status`.** The current review-session API projects stored
  attribution to `pending`, `implemented`, or `dismissed`:
  - **OPEN — work these:** `pending`. If a deployment exposes raw attribution values, also treat
    `partial_implementation`, `not_implemented`, and `focus_areas_edited` as open.
  - **CLOSED — leave these:** `implemented`, `dismissed`; raw `full_implementation`,
    `detected_after_merge`, and `outdated` are also closed. Report unfamiliar values instead of
    silently excluding them from a clean verdict.
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

No fix instruction or covering implementation authority → present for approval open `action_required` then
`remediation_recommended`, and surface (don't auto-fix) `informational`. When an instruction is
ambiguous, state the scope you picked in one line before acting, so the user can redirect. Always
report which findings you **skipped** and why (out of scope / dismissed / informational) — never
silently drop one.

## Two modes

Each round follows **Resolve a finding**: evaluate and apply only fixes covered by existing user
authority (`autofix` or an explicit fix request); otherwise present and ask. Push authority is separate.

**Once (default).** Fetch → evaluate every open finding (triage — all four OPEN statuses, not just
`pending`) → present + ask if authority is missing → apply authorized fixes in code →
commit/push per the user's workflow → **record the outcome**
(`mark-implemented` for what you fixed; `dismiss`, with the user's explicit go, for what they
agreed to close without a change) → summarize what you resolved and what remains (e.g. skipped /
dismissed / informational). Stop. Don't loop unless asked. Triage covers
**all** open findings, but the picker only *offers* the actionable set —
`action_required` then `remediation_recommended` — with `informational` surfaced separately,
matching the default scope above; put `informational` in the picker only when the user asks.
(Offering isn't selecting: every box starts unticked.)

**Watch until clean** (when the user says "babysit" / "keep going until it's clean"). Reuse explicit
fix authority within its scope; monitoring alone does not authorize edits. After you resolve
findings and the fix commit is pushed, Qodo re-reviews the *new* commit — so:

1. Note the PR's current head SHA — the commit you just pushed (`git rev-parse HEAD`), or, for a
   PR you didn't push, read it as forge metadata (`gh pr view <pr> --json headRefOid`). That's a
   metadata read, not review-comment scraping — it's fine.
2. Follow **Read the session state FIRST** on each read: poll `started` only within the bounded
   watch; report non-success terminal or unknown states and stop. A completed older run is stale:
   allow a bounded wait for the new head's review to appear. Act only when the review is
   **`completed` AND its `commit_sha` equals that head SHA**.
3. When fresh: if any OPEN findings remain (all four statuses — a `partial_implementation` is
   still open), resolve them and repeat; if none remain, report the
   review clean and stop.
4. Bound it: stop after a few rounds with no progress and hand back to the user rather than
   looping forever.

## Resolve a finding

Evaluate Qodo's findings against the code, PR intent, and available session context. Own the final
technical recommendation and rationale, while following the user's scope and approval below.

**Evaluate each finding** against the actual code and the PR's intent, and form a recommendation:

- **Sound and in scope** → a fix is warranted; note what you'd change (read `title` +
  `description`, locate the code — the `qodo-codebase-wisdom` skill's read tools help when it isn't
  local).
- **Unsupported or already addressed** → recommend dismissal with code evidence. A deliberate
  choice supports dismissal only when the implementation enforces its assumptions.
- **Unsure** → identify the evidence or check needed before deciding.

**Present and ask only when edit authority is missing.** If `autofix`, an explicit fix request,
or covering implementation authority already applies, skip this selection prompt and follow
**Authorized fixes** below. Otherwise use the assessment above for each open, in-scope finding,
keeping its `action_level`/`category` and your recommendation, then ask **in a single
prompt** which findings to resolve. Use whatever the host gives you: a multi-select if it has one
(Claude Code's `AskUserQuestion`, say), otherwise a numbered list and "reply with the numbers to
resolve". One prompt either way — don't ask per finding. **Nothing is pre-selected.** Mark which
ones you recommend, but the user must actively choose: this prompt is the last thing standing
between a finding and an edit, so a bare Enter must resolve nothing. Resolve only what the user
picks (edit as normal, matching the surrounding code); report the rest as skipped with your reason.
On this missing-authority path, do not edit before the user has chosen.

**Authorized fixes.** `autofix` or an explicit request such as "fix the action-required findings"
authorizes supported code fixes within that scope; no special token or repeated confirmation is
needed. Existing implementation authority can also cover the correction. State your assessment
before applying it. A status-only request grants no edit authority; ask once if scope is ambiguous.
Neither fix authority nor monitoring authorizes dismissal or a push. Report fixes and skipped findings.

Commit/push per the user's workflow — ask before pushing unless they've told you to.

**`attribution_status` is the intended signal** — a fixed finding is re-attributed to
`implemented` by the next review on its own (the stored value is `full_implementation`), so after pushing, re-fetch and work only what's
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
5. The explicit request covers the supported action-required fix: parameterize the SQL query and
   verify it. Report the timeout as already satisfied and the informational finding as out of scope;
   neither is dismissed automatically. Report the local fix separately from the PR's review state.
   Push only with separate covering authority, then check the review of the new head.

## Configuration

Use `--json`, compare `review_session.commit_sha` with forge head metadata, and stamp the exact
skill/version/distribution provenance on the first authenticated Qodo call after the unadorned version probe. Read and write capabilities are
discovered from the installed CLI catalog; rendered forge comments are never the data source.

## Error Handling

Treat null sessions, running reviews (`started`), stale commits, missing write capabilities, rate limits, and
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

After authorized changes, report what improved, why each decision was made, what was verified,
and what still needs attention. Keep local edits, recorded dispositions, and review state distinct.

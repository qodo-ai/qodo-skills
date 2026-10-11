---
name: qodo-pr-triage
description: Answer "what's next for me?" from the workspace's PR Triage queue, exactly as the Qodo portal ranks it, explain why one PR sits where it does, then do the work in the same session (fix the findings on my PR, or draft and post a review of someone else's) using the qodo CLI's managed pr-triage tools and the local `gh` login. Use on "what's next for me", "what should I review next", "my PR queue", "why is #N here / ranked first", "show the stack for #N", "fix the findings on my top PR", "review #N"; skip ranking or grouping PRs by any other means, merging, and non-GitHub PRs.
owner: Qodo
metadata:
  vendor: qodo
  version: "0.1.0"
  recommended: "true"
  package: "qodo"
  distribution: "skills-sh"
---

# PR Triage

## Description

Use the `qodo` CLI to read the workspace's **PR Triage queue**, the same ranked list the portal
shows, and act on it from the terminal. Two read-only managed tools supply everything that is
ranked, explained, grouped or ordered:

- `pr-triage next`: the top of the queue for a set of logins, in served order.
- `pr-triage explain`: one PR's full decision, its findings, and its stack members in merge order.

**The platform decides; this skill presents and acts.** Never re-rank, regroup, reorder,
filter, merge into stacks, or reword what the tools return. Local context (the checkout, the
diff, `gh`) is used only to do the work the user picks.

## Prerequisites

- The Qodo CLI is installed and the user can authenticate with `qodo login`.
- The workspace exposes the `pr-triage` tools. They are gated three ways: the CLI's
  `tool.pr-triage` tool flag (off by default), the platform's `pr_triage` feature flag for the
  workspace, and the organization's PR Triage view level for the user's role.
- For any write (posting a review, pushing a fix): `gh` is installed and logged in, and the user
  approves the exact write.

## Instructions

Run the runtime gate, then Preflight, then the job the user asked for (Jobs 1 to 4). Every
write goes through the live-state check. Present results as described in "Present the queue".

## Handle a skill update notice

Treat `QODO_NOTICE` updates as passive. Continue the task without inventory or update
questions; mention each event at most once. Updated skills load next session.

## Runtime compatibility gate

First resolve the executable: if `qodo` is not on PATH, retry `~/.qodo/bin/qodo` (or
`$QODO_HOME/bin/qodo` if set; `bin/qodo.cmd` in PowerShell) and keep using whichever resolves.
Only if that is missing is Qodo not installed; tell the user to obtain a checksum-pinned installer
command from Qodo or their administrator, and never pipe an installer into a shell.

Before any other Qodo command, run `<qodo> --version` exactly as shown, with no provenance flags.
This skill requires Qodo CLI **0.1.0-next.37 or newer**. If the version is older or cannot be
parsed, do not run `whoami` or a managed tool and do not call it an auth problem: show
`qodo update`, ask once, and continue only after it succeeds.

## Quick start

```
qodo --version                                                       # compatibility probe, FIRST
qodo read whoami --json --skill qodo-pr-triage --skill-version 0.1.0 --distribution skills-sh
qodo read tools pr-triage --json                                     # exact commands and flags
qodo read pr-triage next --json                                      # 1st call: learn viewer_logins
gh api user -q .login                                                # local login (may fail: no gh)
qodo read pr-triage next --logins alice,alice-work --limit 5 --json  # "me"
qodo read pr-triage explain --provider github --repository-id <id> --provider-pr-id <id> --json
```

The commands are illustrative. **Confirm command paths and flags with
`qodo read tools pr-triage --json`** before the first call. An `unknown command` on `pr-triage`
while `whoami` succeeds means a stale catalog: run `qodo tools --refresh` once and retry. If it
is still absent, the tools are not enabled (see Error Handling); do not loop.

## Preflight

1. **Auth.** Run `qodo read whoami`. Only explicit missing credentials call for `qodo login`;
   keep the organization's own login command and endpoint. Network, TLS and service failures
   keep their own diagnosis.
2. **Who is "me".** Call `pr-triage next` once with no `logins` and keep `viewer_logins` (the
   logins linked to the Qodo account). Run `gh api user -q .login` for the local login. "Me" is
   `viewer_logins` merged with that login, de-duplicated; pass it as `logins` (at most 20). If
   `gh` is missing or not logged in, use `viewer_logins` alone and remember that writes are
   blocked (see Writes). If the merged list is empty, say so and ask which login to use; never
   fall back to the whole workspace queue silently.
3. **Reuse.** Keep the last `next` result for the session, including `generated_at`, so
   follow-ups ("open the second one", "why is that one first") refer to served items by their
   `ids` and never by guessed numbers.

## Job 1: "What's next for me?"

Call `pr-triage next` with the "me" logins and `limit` (default 5; the user may ask for up to
25). The result carries `generated_at`, `policy_version`, `viewer_logins`, `total`, `has_more`
and `items`. Present the items **in the order served**, using only served values:

- `priority_bucket` exactly as served (`P0`, `P1`, `P2`).
- `title`, `repository`, `url`, `author`.
- Each `reasons[].detail` sentence, verbatim, in served order. Never paraphrase a reason or
  infer one from `code`.
- `next_action.detail`, verbatim. Branch on `next_action.action` (the enum) for what you offer;
  show the `detail` words. List `secondary_actions[].detail` verbatim as the other options.
- `responsible_role` (who owes the next move), so the user can skip PRs waiting on someone else.
- The open findings from `findings`.
- `unit`: when present, "`position` of `size`" in its stack. When `unit.open_summary` is
  present, show its `priority_bucket`, `blast`, `sla` and `next_step` (`#number`, `detail`,
  `responsible_role`) as served. When `unit` is `null`, say nothing about stacks.

Open with the queue's age, computed from `generated_at` against now ("ranked 4 minutes ago").
When `has_more` is true, say "showing N of `total`". If `items` is empty, say the queue has
nothing for these logins and name the logins used.

Do not add your own ordering hints ("I'd start with..."), group items the platform did not
serve together, or drop items. If the user wants more, call again with a higher `limit`.

## Job 2: "Why is #N here?"

Resolve #N to a served item and use its `ids` (`provider`, `repository_id`, `provider_pr_id`).
`explain` takes those identifiers only; there is no URL or number lookup. For a URL or #N not in
a result you have, call `next` again with a larger `limit` and match the item's `url`. If it is
still not served, say it is not in this queue for these logins, or ask which PR they mean. Never
invent ids.

Call `pr-triage explain` and present, in served order, the same fields as Job 1 (priority,
every `reasons[].detail`, `next_action.detail`, `secondary_actions`, `responsible_role`,
`findings`), then the stack:

- `unit.members` **in the served order, which is the merge order**, each with `#number`,
  `position`, `priority_bucket` and `next_action.detail` as served (`next_action` may be `null`:
  then show none).
- `unit` is `null` for a solo PR; then say it stands alone.

## Job 3: Fix the findings on my PR

For an item the user authored (or explicitly owns):

1. Stop if `ids.provider` is not `github` (writes go through `gh`).
2. Check out the branch: `gh pr checkout <url>` (or `git switch` if it is already local). Never
   discard local changes; if the tree is dirty, stop and ask.
3. Hand off to **qodo-review-resolver** for this PR. It reads the findings, fixes them, and
   records outcomes under its own approval rules. Do not reimplement it.
4. Pushing the fix commit is a write: confirm with the user and run the live-state check
   immediately before `git push`.

## Job 4: Review someone else's PR

1. Stop if `ids.provider` is not `github`.
2. Read the diff locally: `gh pr diff <url>` and, where useful, the checked-out files. Use the
   `explain` result for context (reasons, findings, stack position). For a stack member, review
   in the served `unit.members` order and say which member you are on.
3. Draft the review: a verdict (`comment`, `approve` or `request-changes`) and the body. Show
   the full draft to the user.
4. Post only after the user explicitly confirms that exact draft and verdict. Run the live-state
   check, then post with
   `gh pr review <url> --comment|--approve|--request-changes --body-file <file>`.
   Edits to the draft need a new confirmation.

## Shipping a stack

When the user wants to land a stack, show `unit.members` in the served merge order with each
member's priority and next action, then hand off to the user's own merge flow. **This skill
never merges.**

## Writes: live-state check

Every write (posting a review, pushing a commit) is preceded, immediately, by:

```
gh pr view <url> --json state,headRefOid,reviewRequests,updatedAt,mergedAt,closedAt
```

Stop, without writing, when any of these changed since `generated_at` and say exactly what
changed:

- `state` is no longer `OPEN` ("merged at ...", "closed at ...").
- `headRefOid` differs from the head the user reviewed or the local checkout, or `updatedAt` is
  later than `generated_at` with new commits ("2 new commits since the queue was ranked").
- For a review: the user is no longer in `reviewRequests` when the next action was a review.

Offer to re-run `pr-triage next` for a fresh ranking. Never write on a stale view.

**No `gh` login.** Reads (the queue, explain, local diffs of a checked-out branch) still work.
Every write stops with: "Run `gh auth login`, then ask again." Do not try another auth path.

## Present the queue

Lead with the bottom line: the top served item and its `next_action.detail`, or why you stopped.
Then the list, one short block per item, in served order. Mention Qodo once, as the source of
the ranking: "Qodo's PR Triage queue, ranked 4 minutes ago, puts ... first." You do the checkout,
review drafting and writes; do not attribute those to Qodo. Use only served words for priority,
reasons and next actions. No branded headings, banners or footers; a short, faithful list beats
a wall of JSON.

## Configuration

Use `--json` for parsed output and stamp exact skill/version/distribution provenance on the first
authenticated Qodo call after the unadorned version probe. Tool names and schemas come from the
installed CLI catalog. Enabling the tools is a workspace and CLI setting (`tool.pr-triage`, the
platform `pr_triage` flag, the view level); this skill never changes them.

## Error Handling

Show the tool's code and message; these are the expected ones:

- **Tools missing after a refresh** (`unknown command` on `pr-triage`, or `tool_unavailable`):
  "PR Triage tools aren't enabled here. They're behind the `tool.pr-triage` flag and the
  workspace's PR Triage flag; ask Qodo or your administrator to enable them."
- **`MT-AUTH-FORBIDDEN`, not enabled**: PR Triage is not enabled for this workspace. It is a
  feature flag, not an error.
- **`MT-AUTH-FORBIDDEN`, role**: PR Triage is not available to your role in this organization;
  an organization admin controls the view level.
- **`MT-UPSTREAM-DOWN` (503)**: the platform could not verify PR Triage access right now; retry
  at most once.
- **`MT-NOT-FOUND`** on explain: the PR is not in the queue (merged, closed, or never ingested).
  Do not guess another id.
- **`MT-AUTH-INVALID`**: credentials were rejected; follow the Preflight auth step.
- **`MT-RATE-LIMITED`**: back off; do not hammer retries.
- **No GitHub items**: non-GitHub items can be listed and explained but not acted on; PR Triage
  writes in the terminal are GitHub only today.

## Guardrails

- The tools are the only source of priority, reasons, next action, stack membership and merge
  order. No ranking or grouping from branch names, tickets, files or your own judgment.
- Show served words verbatim: `P0/P1/P2`, `reasons[].detail`, `next_action.detail`.
- Every write needs explicit confirmation of the exact action and a fresh live-state check.
- Never merge, close, label or reassign PRs from this skill.

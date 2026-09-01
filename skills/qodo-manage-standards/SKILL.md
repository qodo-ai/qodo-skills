---
name: qodo-manage-standards
description: Create, edit, and administer Qodo Review Standards from conversation — capture a convention just discussed as a new rule, change or deactivate an existing one, re-scope rules to a repo, and triage pending suggestions (accept/reject) — using the qodo CLI's managed rules tools. Use on "make this a rule", "make a rule for this repo", "deactivate/disable the X rule", "change the X rule to an error", "re-scope the X rule to this repo", "show pending suggestions", "let's triage suggestions", "accept/reject this suggestion", or "bulk deactivate rules"; skip reading or applying rules (use qodo-get-rules) and anything that isn't a rules-entity change.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.0.2"
  recommended: "false"
  package: "qodo-standards"
  distribution: "skills-sh"
---

# Manage Review Standards

## Description

Use the `qodo` CLI to **administer** the workspace's Review Standards: capture a convention as a
new rule, edit or retire an existing one, re-scope it to a repo, or triage the pending
suggestions queue. Review Standards is Qodo's umbrella term for rules and suggestions. This is
the **write** counterpart to `qodo-get-rules` (which only
reads and applies rules) — every command here changes workspace state, so confirm with the user
before calling anything, and run bulk operations as a dry run first.

## Prerequisites

- The optional Qodo Standards package is installed and loaded explicitly.
- The Qodo CLI is authenticated and exposes the requested standards write tool.
- The exact rule, scope, and intended mutation are known; the user can approve every write.

## Instructions

Follow the detailed workflow below: preserve update notices, verify the live schema, resolve the
target, preview destructive or bulk work, obtain confirmation, mutate once, and verify the result.

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
qodo --version                                                      # compatibility probe — run this FIRST
qodo read whoami --json --skill qodo-manage-standards --skill-version 1.0.2 --distribution skills-sh
qodo read rules metadata --json                                       # categories/severities before creating
qodo rules create --name "..." --category "..." --severity warning --content "..." --good-examples "..." --bad-examples "..." --scopes "/owner/repo/" --json
qodo rules update --rule-id 123 --severity error --json               # only the fields to change
qodo rules set-state --rule-ids 123,124 --state inactive --dry-run --json
qodo rules set-state --rule-ids 123,124 --state inactive --json       # after confirming the preview
qodo rules set-scope --rule-ids 123 --scopes "/owner/repo/","/owner/repo2/" --json
qodo read rules list --state pending --json                           # suggestions awaiting triage
qodo rules bulk --operation accept_activate --rule-ids 10,11 --dry-run --json
# Show the exact matched rules/count and ask once; run without --dry-run only after approval.
qodo rules bulk --operation reject --rule-ids 12 --dry-run --json     # PERMANENT delete — dry run first
qodo read rules get --rule-id 123 --json                              # current form before editing
qodo read tools rules --json                                          # exact safe flags (renders offline)
```

**`qodo: command not found`?** That's usually PATH, not a missing install: GUI-launched agents
run shells with a minimal PATH. On POSIX, retry `"${QODO_HOME:-$HOME/.qodo}/bin/qodo"`. In
Windows PowerShell, retry:

```powershell
$qodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Join-Path $qodoHome 'bin/qodo.cmd')
```

Keep using the resolved launcher for every Qodo command here. Only if it is missing is Qodo
actually not installed; tell the user to obtain a checksum-pinned installer command from Qodo or
their organization's administrator. Installers are served from https://get.qodo.ai, but never
invent a digest or pipe an installer directly into a shell.

**Sandbox auth diagnostic.** In a sandboxed environment, if `qodo read whoami` fails for any reason
(including `Not logged in`), ask the user to approve one exact read-only retry of `qodo read whoami`
outside the sandbox before recommending login or refreshing tools. Keychain failures can be
reported as generic auth failures, so the sandboxed result alone is not diagnostic. That approval
applies only to this single diagnostic retry: do not reuse it, request persistent approval, or move
later Qodo commands outside the sandbox automatically. If the retry succeeds, continue with normal
per-command permission checks. If it still fails, follow the normal auth troubleshooting below.

Add `--json` to everything you parse. **Confirm the exact tool names, flags, and write status with
`qodo read tools rules [<tool>] --json`** (renders offline from the cached catalog) — use it for reads;
inspect write commands with `qodo tools help rules [<tool>] --json`. The commands above are
illustrative, not guaranteed current; a stale catalog after a fresh install shows as `unknown
command`/`unknown option` on `rules` while `whoami` still succeeds — run `qodo tools --refresh`
and retry before assuming the tool doesn't exist.

## Preflight

1. **Auth first.** Run `qodo read whoami`. After the sandbox retry above when applicable, tell the user
   to run `qodo login` only when the result explicitly says `Not logged in`, then stop. `No tool
   catalog cached` is a catalog failure, not proof of missing credentials: run `qodo tools
   --refresh` once, then retry `whoami`. If either command still fails, report that exact failure
   and stop instead of sending the user through login. An `unknown command`/`unknown option` on
   `rules` while `whoami` succeeds also means a stale cached catalog — refresh once and retry.
2. **Never guess the target.** Resolve which rule or suggestion the user means (by id from a
   prior `qodo-get-rules`/`qodo read rules list` result, or by asking) before calling a write
   command. Never invent a `rule_id`.
3. **Repository scope**, when the user wants a rule scoped to "this repo": derive it from the
   repo's `origin` remote the same way `qodo-get-rules` does — full path after the host, `.git`
   suffix stripped, wrapped as `/<path>/` (e.g. `git@host:a/b` and `https://host/a/b` both parse
   to `/a/b/`). Confirm the derived scope with the user rather than assuming it's what they want.

## Where rules come from

Three separate paths create rules in a workspace. They produce different `sourceType` values,
and knowing which one made a rule explains a lot about why it looks the way it does:

| Path | `sourceType` | What it is |
|---|---|---|
| **Codebase import** | `Repository File` | Rules extracted from documents already in the repo — `CLAUDE.md`/`AGENTS.md`, contributing guides, standards docs. `sourceUri` names the file. |
| **Rule miner** | `Code Patterns` | Rules inferred from the repo's **merged pull-request history**, via the PR-knowledge → rule-miner pipeline. `sourceUri` is a PR review-comment URL. |
| **Direct creation** | `User` | Rules a person wrote — through the portal, or via this skill's `qodo rules create`. |

**Name the path only from `sourceType`.** "Mined" means the PR-history pipeline specifically —
don't apply it to a `Repository File` rule, which came from a document, not from PR behavior.
And `sourceType` tells you the *origin*, not the *mechanism*: `Repository File` says a rule
traces to a document, not whether extraction was automated or hand-authored. Say what the field
shows; don't narrate a pipeline the data doesn't name.

`sourceType` is coarse — one value covers every kind of repo document. Read `sourceUri` when you
need to know which document a rule actually came from.

## The four jobs

This skill covers everything that changes the rule set. Route the user's request to one of:

**1. Capture — turn a discussed convention into a rule.** The strongest signal: the user just
described or agreed on a convention mid-session and wants it enforced going forward ("make this
a rule", "let's make sure we always do X"). Draft the rule from the conversation:
- `name` — concise, unique (duplicates are rejected by the platform).
- `category` — call `qodo read rules metadata` first and pick an existing category when one fits
  (falling back to a sensible new one, e.g. Security, Correctness, Quality, Reliability,
  Performance, Testability, Compliance, Accessibility, Observability, Architecture).
- `severity` — **error** = must comply, **warning** = comply by default, **recommendation** =
  apply when appropriate. Default to **warning** unless the conversation implies it's a hard
  rule (security, correctness) or explicitly optional guidance.
- `content` — 1–3 sentences, imperative voice, describing what to check or enforce.
- `good_examples` / `bad_examples` — a short code snippet each when the conversation has enough
  context to write one; pass `""` rather than fabricating an example that wasn't discussed.
- `scopes` — propose the current repo (see Preflight); omit for the universal scope `/` only if
  the user explicitly wants it workspace-wide.

**Restate the full draft and get explicit confirmation before calling `qodo rules create`.**
The response is the full created rule, including `state` — non-admin callers create a
**pending suggestion** instead of an active rule (a platform permission thing, not an error).
Check `state` in the response: if it's `pending`, tell the user plainly: *"Created as a pending
suggestion — an admin needs to approve it before it's enforced."* A duplicate-name rejection
means pick a different name; don't retry with the same one.

**2. Edit — change an existing rule.** "That rule should be an error, not a warning", "update
the content of the console.log rule". Fetch the rule first (`qodo read rules get`) if you don't
already have its current form in context, so you can show the user the actual before/after, not
a guess. Call `qodo rules update` with **only the fields changing** — it fetches-then-merges
server-side, so anything you don't pass keeps its current value. Confirm the specific change
with the user before calling.

**3. Lifecycle & scope — activate, deactivate, re-scope.** "Disable the tabs-vs-spaces rule,
it's noise", "apply our error-format rules to the new repo too". Prefer `qodo rules set-state`
/ `qodo rules set-scope` over `qodo rules update` for pure state/scope changes across one or
more rules — they're a single atomic call, not a fetch-then-merge. `set-scope` **replaces** the
full scope list (no merge) — if the user wants to *add* a scope, fetch the rule's current
scopes first and pass the union. Confirm before calling; for more than a couple of rules, run
with `--dry-run` first and show the count before executing for real.

**4. Triage & hygiene — suggestions and bulk operations.** "Show pending suggestions and let's
go through them", "deactivate everything scoped to the archived repo". List first
(`qodo read rules list --state pending` for triage, or a filtered `qodo read rules list` for hygiene) so
the user sees what's affected before anything changes. Walk suggestions one at a time or in an
explicit batch per the user's instruction — never bulk-accept/reject without the user having
seen what's in the batch. `qodo rules bulk` operations:

| Operation | Effect | Reversible? |
|---|---|---|
| `activate` / `deactivate` | Sets state | Yes |
| `set_scope` | Replaces scopes (needs `scopes`) | Yes |
| `accept_activate` | Approves pending suggestions → active | Yes (deactivate after) |
| `reject` | **Permanently deletes** pending suggestions | **No** |

**Always run `reject` and any multi-rule bulk operation with `--dry-run` first**, show the
user the matched count, and get explicit confirmation before the real call. Before the real
`reject` call, summarize what will be permanently lost (the matched rule names/ids) — `reject`
is irreversible, and a bare count doesn't tell the user which suggestions are being deleted.
When the user's intent is ambiguous between "reject" and "deactivate", prefer asking or
defaulting to the reversible option.

When triaging a batch of suggestions, close the session with explicit counts — how many
accepted, rejected, and left pending — so the user knows the end state without re-running
`qodo read rules list`.

## Report the verified outcome

After a read or mutation returns structured results, lead with one compact summary:

```
# 🛡️ Qodo Review Standards

**Outcome:** <what was found or changed>
**Scope:** <workspace or repository scopes involved>
**State:** <active, inactive, pending, rejected, or mixed counts>
---
```

Use the response's actual state and succeeded/matched counts; never turn a successful HTTP
response into a stronger claim. Render the block once per user-requested operation, not before
the confirmation gate and not for auth, permission, validation, or transport failures. Put rule
names, ids, before/after fields, dry-run details, and skipped items below it.

## Configuration

Use `--json`, explicit rule ids and scopes, and the CLI's current metadata before constructing a
write. Stamp skill/version/distribution provenance on the first Qodo call. Keep Standards separate
from the default Qodo package and never infer admin authority from installation.

## Error Handling

- **Permission denied (admin required)** — writes other than a non-admin's own pending-create
  are admin-gated. Explain plainly: *"This requires admin permission in your workspace — ask an
  admin to make the change or grant you access."* Don't retry; it won't succeed without a
  permission change.
- **Not found** — the rule id doesn't exist in this workspace (wrong id, wrong workspace, or
  already deleted). Say so; don't guess a different id.
- **Rate limited (`MT-RATE-LIMITED`)** — back off; don't hammer retries.
- **Validation error** — a field was rejected (e.g. duplicate name, bad severity value); fix the
  specific field and retry once, don't loop blindly.
- **Retries on a mutation** — if you retry a create/update/bulk call after a transient failure,
  it's safe to retry as-is; the CLI's idempotency handling covers duplicate submission.

## Guardrails

- **Confirm before every write.** Restate the exact change (which rule(s), which fields, old →
  new) and get the user's go-ahead before calling a mutating command. This is the first
  mutating skill in the family — treat every call as one the user should be able to veto.
- **Dry-run first for anything bulk or destructive.** `set-state`/`set-scope` across multiple
  rules and every `bulk` call: `--dry-run` → show the count/blast radius → confirm → real call.
- **Never fabricate a rule id, scope, or example.** Resolve or ask; an empty result from `list`
  is a valid outcome, not an error.
- **Tell the user which outcome actually happened** — active rule vs. pending suggestion,
  matched vs. succeeded count from a bulk call — don't assume success from a 200 response alone.
- **Prefer the reversible operation** when the user's intent is ambiguous (deactivate over
  reject, deactivate over delete).

Lead with the bottom line — what changed, what's pending approval, what you skipped and why —
then the specifics. A short, accurate status beats a wall of JSON.

---
name: qodo-review
description: Review local changes with Qodo after coherent substantive work and before a PR or completed-work handoff. Use default auto effort, attach coding-session context, assess findings, batch authorized fixes and stop unproductive review loops. Also use for "review my local diff", "pre-PR review", or "run qodo review". Use qodo-review-resolver for findings already posted on a PR.
owner: Qodo
metadata:
  vendor: qodo
  version: "1.10.17"
  recommended: "true"
  package: "qodo"
  distribution: "marketplace"
  instruction_mode: "embedded"
---

# Local Review

## Description

Use local review to improve the intended change, not to accumulate clean-looking runs.
The workflow is: finish a useful slice → test → review with context → assess findings
→ apply authorized fixes → test again → review changed work when useful.

`qodo review` collects local changes without pushing, commenting or opening a PR.
Only the comparison base must exist on the remote.
Use `qodo-review-resolver` for findings already posted on a PR.
Do not duplicate remote review for an unchanged pushed snapshot.

## Prerequisites

- The intended repository, comparison target and review scope are known.
- Qodo review is available through the CLI, or through MCP with a tested local collector.
- The user's edit, commit and review-budget constraints are known.
- Relevant coding-session context is available. Do not require the user to reconstruct the session.

## Runtime compatibility gate

Prefer the CLI because it collects and filters the worktree and manages review checkpoints.
Before CLI use, read [CLI execution](references/cli-execution.md#preflight).
In every command example, replace `qodo` with that resolved invocation, including the version probe.
On Windows, also read [shell guidance](references/windows-shells.md) before the first command.
Use [launcher recovery](references/windows-launcher.md) only when invocation fails.
Require Qodo CLI **2.0.0 or newer** and a runtime with review API v2.
Start with the unadorned probe:

```sh
qodo --version
```

If compatible, verify identity unless a successful check still covers this execution context:

```sh
qodo read whoami --json --skill qodo-review --skill-version 1.10.17 --distribution marketplace --host antigravity
```

An old or unparseable version stops authenticated calls.
Follow the reference's bounded compatibility recovery without changing deployment or update policy.
Confirm available review flags with `qodo review --help`.
Do not infer installed capability from an open PR or newer source checkout.

MCP cannot read this worktree. Before an MCP review, read [MCP execution](references/mcp-review.md).
Without a tested collector matching the intended scope and exclusions, report the coverage blocker.
An ad hoc `git diff` is not equivalent collection. MCP users skip CLI preflight.

## Execution and recovery policy

These are the canonical gates. References supply command syntax, result dictionaries and platform recipes;
they do not select different authority, compatibility or recovery policy.

- **Trusted runtime:** retain the resolved installed invocation for every call, including `--version`.
  Never run repository-local launchers. If neither installed invocation works, stop the CLI path.
  Installation requires covering approval and a Qodo/organization-supplied checksum-pinned installer.
  Never invent a digest, pipe an installer into a shell, or switch deployments.
- **Compatibility recovery:** old or unparseable versions stop identity, login, reviews and managed tools.
  Check only whether `QODO_UPDATE_BASE_URL` is set; never print its value. If set, stop for the user.
  Preserve the recorded origin, exact version choices and update holds. Choose one approved route.
  Every updater route, including ordinary update, needs a successful check offering a newer compatible 2.x target.
  Failure, no update or an incompatible target stops before any runtime change; do not switch routes.
  Same-origin `latest-2` is only a selected, verified legacy 1.x-to-stable-2.x route, not another-major approval.
  For an unparseable runtime or no supported updater, use the separately authorized checksum-pinned installer route.
  Make one approved runtime attempt, then probe the version again. Denial, failure or incompatibility stops.
- **Identity and discovery:** reuse identity only for the same invocation, workspace, deployment and execution context.
  Possible sandbox keychain failure permits one explicitly approved read-only identity retry; denial stops.
  Only explicit missing credentials justify login. Preserve TLS, network, service and authorization failures.
  Missing catalog or an unknown managed command permits one catalog refresh, not another account.
  A still-unavailable capability is a blocker. An unknown built-in command needs compatible runtime support.
- **Collection and retry:** preserve the accepted operation and exact uncertain-start request.
  A status transport failure permits one collection retry after the returned delay, otherwise 15 seconds.
  Failed identity or integrity verification is not a status transport failure.
  Preserve the rejected evidence; retry collection only when an applicable recovery gate permits it.
  A confirmed recoverable terminal failure permits one cause-corrected resubmission, not another retry per symptom.
  User/task no-auto-retry instructions or a returned retry prohibition require explicit approval first.
  A repository-identity correction preserves base, scope, context and effort and uses that same retry allowance.
  Permission, authentication, entitlement, rate-limit or further failure stops. A pending run is never restarted.
  Keep a connected client alive; reap its child before parsing. Progress is not a result.
  Retain the final envelope even after nonzero exit and before deleting only this invocation's temporary files.
- **MCP:** require the tested collector, safety exclusions, omission report and fetchable base above.
  Preserve request identity after uncertain admission. Check `isError` on every receipt and result page.
  Keep result-view arguments unchanged. Chunk count is not an end marker.
  Report the final `next_cursor: null`, verified byte count and digest before claiming complete collection.
  Never invent an unsupported collector mode, retry-key field or substitute checkout.
- **Finding-status writes:** fixing code does not authorize a dismissal. An authorized local dismissal uses original
  finding IDs and their actual local-review IDs, grouped by review, reason and explanation.
  Never substitute a run ID or PR URL for a missing local-review ID, or omit advertised replay protection.
  Read back each stored outcome. A prior disposition or conflict is not a new successful write.
  Report status persistence separately from downstream synchronization: `reconciled: false` can mean the
  status was saved but synchronization is incomplete. Do not report that as a failed stored transition.
  Recover an uncertain invocation with its original request and transport key.
  On MCP, a completed same-key replay returns the stored result without retrying synchronization.
  After verified storage, a separately authorized synchronization attempt needs a new invocation and a new retained transport key.
  Keep the business arguments unchanged. Verify each new outcome.
  An unknown outcome does not authorize key rotation. Report unavailable recovery instead of claiming synchronization.
  Collect only a returned, supported operation handle. A synchronous tool result does not establish polling support.
- **Requested maintenance:** preview the complete affected installation scope and apply only covering approval.
  Runtime approval is not skills-installation approval. Do not widen owners, packages, origins or update policy.

## Instructions

### 1. Review at a useful moment

Review a coherent, testable slice after substantive work and relevant checks.
A midwork checkpoint is useful when its feedback can guide remaining implementation.
Before a PR, PR update or completed-work handoff, establish coverage of the full intended change.
A pause for a question or approval is not a completed-work handoff.

Do not submit after every edit, during unfinished exploration, or merely because time passed.
Do not automatically review trivial changes.
Respect the user's narrower scope, explicit effort and budget.
Unless the user requests a fresh assessment, reuse compatible completed coverage of the current intended snapshot.

**Default to auto:** omit both `--fast` and `--deep` for ordinary submissions, including follow-ups.
Use `--fast` for an explicitly requested quick review or a purposeful light midwork checkpoint.
Use `--deep` for requested thorough scrutiny or a concrete high-impact risk. State the reason.
Diff size, session length and final-review status alone do not justify deep.
Auto follows deployment policy. It promises neither a fixed tier nor a spending cap.
There is no `--standard` flag. `--fast` and `--deep` are mutually exclusive.

### 2. Capture the intended scope

An exact `--base` skips target selection. Otherwise use the explicit target or the
unique open PR target for the source repository and branch.
For `child → parent → main`, compare from the merge base with `parent` and retain `parent`
for PR linking. A SHA does not identify a branch. Without a verified target, disclose the
unlinked fallback; resolve a specifically requested stack layer before submitting.
Fetch the target for current remote history. If installed help advertises `--target`,
omit both flags for discovery or pass `--target <branch>` for a chosen target.
Check the reported target; on ambiguity ask the user before retrying.
MCP: send the diff base as `base_sha` and HEAD as `commit_sha`. Send `comparison_branch`
only for a verified target when the live input schema advertises it.

On older CLIs without `--target`, resolve the actual target first, compute
`git merge-base HEAD <target-ref>` and pass that SHA as `--base` on every submission.
This may prevent PR linking. Disclose offline or pinned history.
Use a known base SHA literally or explicitly bind its shell variable to that SHA; do not leave an unresolved placeholder.
If the common ancestor or remote base is unavailable, stop instead of substituting the target tip.
Review authority does not authorize pushing the base.

During coding, commit only task changes before review when the user's workflow permits commits.
Preserve unrelated staged, unstaged and untracked files.
Ordinary capture includes working changes and eligible untracked files, even after a task-only commit.
A HEAD SHA alone does not identify a dirty snapshot.

For a committed PR candidate, use supported committed-only collection or a clean checkout at the intended commit.
Check installed help before selecting a collection mode.
If ordinary capture would include unrelated edits, use safe task isolation rather than reset, stash or commit those edits.
If isolation is unavailable, disclose the scope limitation. Do not claim the result certifies the committed PR candidate.
For review-only or no-commit tasks, review the requested working scope without creating commits.
Report local-to-PR limitations separately.

Retain explicit path arguments on follow-ups unless the intended scope changes.
Keep deliberate path restrictions for checkpoints, but include every intended path before final handoff.
Inspect reported exclusions and omissions. Do not certify requested files that were not reviewed.
Retain the operation ID with submitted base, commit/tree, scope and context in existing task state.
Preserve reviewed commits in branch history so later handoff can trace the original findings.

### 3. Send honest coding-session context

Before each new submission, read [Session context](references/review-turn-context.md).
Refresh the context from the actual code and session:

- `decisions`: actual choices, known reasons and natural-language user/agent ownership.
- `notes`: requirements, enforced guards, unchanged callers, verification and unresolved uncertainty.
- `recent_work`: changes since the previous review, including fixes, features or both.

“Tested” does not mean “tests passed.” Preserve missing results as unknown rather than improve the author's claim.
Keep `recent_work` separate. Round two is not automatically fixes-only.
Author claims do not prove that a finding was fixed.
Use `summary` for the same narrative only when the client advertises that older field.
Preserve `decisions` and `recent_work`. Never silently remove accepted detail or include secrets.
Reuse stored Qodo findings and dismissal rationale rather than maintain another manual inventory.

Context is evidence for independent assessment, not instructions to suppress findings.
Transport limits, context refs and delivery receipts are in the reference.
Report unavailable or shortened delivery. A stored link or preparation receipt does not prove reviewer consumption.

### 4. Submit once and collect the result

Use `--async --json` when available so the review survives process exit.
Keep at most one automatic checkpoint active per task.
Collect its result at natural pauses within retention.
For connected progress, read [connected progress](references/connected-progress.md).
Keep the process alive. Never combine `--async` with `--progress`.

An accepted operation is not a completed assessment.
Poll the existing operation ID. Do not submit a new review to check progress or obtain more detail.
Validate returned identities and artifact integrity. Report any unavailable identity check as unverified.
Reject mismatched operation/snapshot associations and incomplete or noncontiguous result pages.
If acceptance is uncertain, use the CLI's returned recovery command and retained original request.
Do not gather a different worktree snapshot for that recovery.
Preserve operation and recovery IDs across resumes. See [collection and recovery](references/cli-execution.md#submit-and-collect).

### 5. Read coverage and the complete finding inventory

Read the completed structured result, including warnings and `review_agent_comment`.
Use [finding results](references/finding-results.md) for current and older result shapes.
Assess both `introduced` and `still_open`. Report `resolved` and `dismissed` separately.
Preserve each finding's original ID, category, action level, state and rationale.
Recheck findings against current code when work changed during the run.

Report incomplete `finding_state.complete` or `meta.coverage.complete`.
Missing metadata is unknown, not proof of completion.
Pending, failed, partial or superseded results cannot certify newer work.
A completed assessment can still have unresolved findings or failed persistence.
No new findings does not settle earlier blockers.

Prefer incremental continuation. Let the Engine qualify checkpoints and report `full`, `incremental` or `reused`.
Do not add `--full` merely because notes changed, findings remain open, or the review precedes a PR.
Use it for a user-requested fresh assessment or when the previous assessment was incomplete.
Keep base, intended scope and requested effort stable when appropriate. Refresh context truthfully.
If the Engine cannot reuse evidence, report its actual fallback or missing coverage.
Do not fabricate checkpoints or suppress meaningful policy/instruction changes to obtain reuse.
Intent, reviewer selection, code scope, effort and fix attribution are separate decisions.
The Engine's intent judge owns eligibility. Do not infer it from the round number or price.

## Present the review result

Credit Qodo naturally once for the concerns its review surfaced.
Explain each material finding as practical impact → assessment against code and session context → recommended action.
State the triggering condition and affected behavior. Cite supporting code.
Preserve reported category/level separately from your recommendation.
Group duplicates only when every finding reference remains visible and individually selectable.
Keep the tone factual. Do not turn an unsupported finding into a broad judgment about Qodo.

Lead with material coverage failures or missing evidence.
Separate new findings, earlier open backlog and settled findings so old work does not appear newly discovered.
A complete review with no findings can take one sentence.
Use no branded headings, banners or repeated summaries. Do not call zero findings alone clean.

## Act on the findings

Independently assess each finding: fix a supported issue, recommend dismissal with evidence, or investigate uncertainty.
A session decision supports the assessment only when the code enforces its assumptions.
Your recommendation does not grant authority.

- **Report-only:** assess and stop. Do not edit or solicit permission to turn the task into implementation.
- **Authorized implementation/fixes:** batch supported corrections within the existing scope without asking again.
- **Ambiguous edit scope:** present all findings and ask once which to apply. Preselect nothing.

Keep uncertain and out-of-scope findings visible.
Do not expand the task with optional refactors merely to reduce the finding count.
Fix authority does not authorize stored dismissals, pushes or unrelated changes.
For explicitly authorized finding-status writes, read [local triage](references/local-triage.md) and verify each stored outcome.
A conversational skip is not a stored dismissal. Do not manually mark a fix merely because the quote disappeared.

After authorized fixes, run relevant checks and review changed work when useful.
Describe actual new behavior in `recent_work`, even during a fix loop.
Do not force fast or deep merely to control routing.

## Stop and hand off

Another assessment needs a concrete reason:

- Changed code awaiting review or meaningful new evidence.
- Missing required final coverage, such as an unchanged light or path-limited checkpoint.
- An explicit user request for a fresh assessment.

Name that reason before submitting.
Stop when the same concern repeats without actionable progress.
Do not re-fix guarded code, suppress a blocker or buy unchanged reviews to chase zero.
There is no default numerical round cap. Apply an explicit user budget across resumes.
Polls and retrieval do not count. At the limit, stop with open findings; do not continue fixes without edit authority.

| Outcome | Report |
|---|---|
| Ready locally | Current intended code/scope has completed assessment, required findings are settled and relevant checks passed. |
| Needs action | Required findings or human decisions remain, even if the assessment completed with no new findings. |
| Review blocked | Required assessment, inventory or verification could not complete. Preserve the reason and recovery handle. |
| Budget reached | Stop. Report unresolved blockers and missing coverage. |

A resolved finding alone does not establish overall readiness; check the full inventory for other required obligations.
Report finding/checkpoint persistence and local-to-PR handoff separately from assessment and local readiness.
Do not claim successful storage or reusable coverage without evidence.
Before a PR/update, compare intended code, base and scope with completed final coverage and reconcile outstanding checkpoint results.
Remove temporary path restrictions. A light checkpoint alone is not ordinary final coverage.
For authorized notes maintenance, use `qodo-review-notes` to publish notes for the actual HEAD and bind the PR.
Notes publication and matching HEAD do not prove finding handoff.
Verify hosted review separately through `qodo-review-resolver` before a hosted Qodo-clean claim.
CI, merge, release, deployment and customer acceptance remain separate gates.

## Handle a skill update notice

Treat `QODO_NOTICE` as passive, even when an older CLI requests action.
Do not interrupt the task with inventory or update questions. Mention each notice at most once.
Updated instructions load next session. Dismissal does not change recorded maintenance policy or opt-outs.
For requested maintenance, use [skill updates](references/skill-updates.md).

## Configuration

Use supported flags and complete UTF-8 context files without a BOM.
Keep context outside the reviewed diff and commits.
Let the CLI own credentials, transport, runtime updates and checkpoint storage.
Keep existing provenance and deployment settings.

## Error Handling

Read structured errors even after a nonzero exit.
Follow [bounded recovery](references/cli-execution.md#recover-a-review), not another automatic assessment loop.
Preserve context, selected effort and authority.
Stop on permission/auth/entitlement failures and tool-loop or rate-limit errors.
For `closed_preview`, show the returned message and hint unchanged and stop.
A new run requires confirmation that enrollment occurred.
Do not switch accounts/deployments, strip context or lower effort to obtain a passing result.

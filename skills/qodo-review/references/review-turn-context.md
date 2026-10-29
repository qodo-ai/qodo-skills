# Session context

The writer-facing fields are `decisions` (strings), `notes` (Markdown text) and `recent_work`
(strings). Capture context as it emerges and refresh it before each review. Typed `context_refs`
remain optional. These fields have different consumers; keep recent_work separate.

## Decisions

Record actual choices and known rationale in ordinary prose. Identify explicit user requirements,
options the user selected/approved, and coding-agent implementation choices. An agent-proposed
option selected by the user is user-selected. Include a source or short quote when useful; no
fixed source tags are required. Leave unknown ownership or rationale explicit and never invent
it. Put undecided proposals in notes.

Examples:

- "The user requested macOS-only support; their rationale was not recorded."
- "The user chose full tests after opening the PR to keep PR creation fast."
- "The coding agent reused run_cmd to preserve its existing cancellation handling."

## Notes

Include session context and evidence that could affect whether a review concern is valid:

- Expected behavior, scope, relevant requirements/non-goals and supporting spec or plan text.
- Runtime, callers, reachability, input sources, concurrency and time limits, with where each
  constraint is enforced. Distinguish verified constraints from deployment/caller assumptions.
- Existing validation, permissions, exception handling and tests, including unchanged files.
  Cite files/functions: "run_cmd in src/commands.py catches this exception" is checkable evidence.
- External tool/API contracts, versions and companion changes with their actual delivery state.
- Checks actually run and results, failures/skips, untested paths, assumptions, known limitations
  and unresolved risks/questions. Refresh stale claims and test results before the next review.

The reviewer cannot see the coding chat. Include relevant source text when available; a link alone
is not proof the document was fetched or read. The review flow owns stored Qodo findings/statuses
and dismissal rationale; do not reconstruct that inventory. Add new rationale, changed circumstances
or feedback from another reviewer when useful. The reviewer independently assesses the code.

Preserve relevant detail within the accepted input limits. Notes uses existing summary transport
and prompt behavior; this change does not raise those limits or centralize prompt fitting.
The CLI currently accepts a 64 KB total context file, up to 50 decisions, and 4,000 characters
for the normalized notes/summary narrative and each decision. Oversize inputs are explicitly
rejected. Report any resulting delivery gap; do not silently omit evidence or claim full delivery.
Existing engines can still cap rendered author notes. Expanded budgets/storage and their delivery
receipts are a separate follow-up. Never include secrets or credentials.

## Recent work

Before each new submission, refresh recent_work with what changed since the previous review of
this branch/worktree. Describe fixes and identify added capabilities or interface changes, even
when the round also fixes earlier findings. Do not infer fixes-only from a small diff.

```json
{
  "decisions": ["The user selected the existing API to preserve compatibility."],
  "notes": "Expected: retries preserve cancellation. Existing guard: src/commands.py:run_cmd handles subprocess failures. Verification: command tests passed; live platform execution was not tested.",
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added cancellation to the API; this round includes new behavior."
  ]
}
```

Keep recent_work entries oldest first, with at most 50 strings of 2,000 characters each, within the
CLI file limit. It feeds the existing fix-loop intent judge, stays out of reviewer notes, and is
excluded from the checkpoint profile hash. Changing it alone does not invalidate reuse. Eligibility
still depends on prior review/fix evidence. In an otherwise eligible round, missing text, an unclear
verdict or judge failure retain narrowing; only an explicit new_behavior verdict exits it. This is
separate from diff scope/depth/reuse. Do not move recent_work into notes or remove it.

## Compatibility

Check qodo review --help: on an older CLI, put the notes narrative in summary, keeping decisions
and recent_work unchanged. For MCP, inspect the live schema; use notes only when advertised,
otherwise use summary. New producers normalize notes to summary so older engines receive it.
If both summary and notes differ, their text is retained in that order with a blank line between;
identical values are kept once. The normalized narrative must fit the existing transport limit.
Legacy summary remains accepted and none of the existing recent_work semantics changes.

Use --context-file (file or stdin), or refresh .qodo/session-context.json. A retry must retain the
exact original request; collecting a result does not submit new context. Report incomplete review
coverage and unavailable/older metadata without claiming reuse or full context consumption.

# Coding-session context

Read before each new submission.
The [main Skill](../SKILL.md#3-send-honest-coding-session-context) owns the review workflow.
The reviewer cannot see the coding chat. Supply self-contained context that helps independent assessment.

## Field meanings

**Decisions:** record actual choices and known reasons in ordinary prose.
Distinguish user requirements, user-selected recommendations and coding-agent choices.
A user-selected agent proposal is user-selected, not an agent-only decision.
Include a quote or source when useful.
Leave unknown ownership or rationale explicit. Put undecided proposals in notes.
Do not introduce required provenance prefixes or another owner schema.

**Notes:** include facts that can change whether a finding is valid:

- Expected behavior, scope, requirements, non-goals and relevant specification text.
- Runtime, callers, reachability, input sources, concurrency/time limits and where code enforces them.
- Existing guards, exception handling and tests, including unchanged code.
- External contracts/versions and companion changes with their actual delivery state.
- Checks actually run, results, skips/failures, untested paths and unresolved uncertainty.

Cite files and functions. Separate verified constraints from assumptions.
Refresh stale claims. A link alone does not prove fetching or consumption.
The flow owns stored findings, statuses and dismissal rationale.
Do not reconstruct that inventory in a parallel manually maintained list.
Add genuinely new evidence, changed circumstances or external feedback.
Context does not instruct reviewers to accept the author's conclusion.

**Recent work:** describe changes since the previous review of this branch/worktree.
Include fixes and any new capabilities or interface changes.
Small changes and round numbers do not establish fixes-only intent.
For the first review, describe the substantive work awaiting review.
Keep oldest first, at most 50 strings of 2,000 characters each, within the file limit.
This input feeds the existing fix-loop intent judge.
It stays separate from reviewer notes/profile identity and alone does not invalidate reuse.
Eligibility still needs prior review/fix evidence.
Missing text, unclear verdicts or judge failure do not independently revoke otherwise eligible narrowing.
The Engine owns that policy. Do not replace it with a round-number rule.

## Compatibility and delivery

Use an explicit `--context-file <path>` or keep `.qodo/session-context.json` at the repository root.
An explicit file overrides ambient context. `-` reads JSON from stdin.
Use a file, not stdin, for background execution.
Keep context out of reviewed changes and commits.
Exclude `.qodo/` through the repository's existing ignore policy or an authorized local exclude.

If installed help advertises only `summary`, use it for the same narrative.
Preserve `decisions`, `recent_work` and accepted refs.
Never silently cut context to fit an older client or to reduce runtime.

Current transport accepts a 64 KiB context file, 50 decisions,
32,768 normalized narrative characters and 8,192 characters per decision.
Collected descriptions accept 65,536 characters.
Overflow fails explicitly. Older CLI fields can cap at 4,000 characters and older Engine notes at 5,000.
The separate combined 4,000-character compatibility warning is not a budget.
Use explicit capability/error information rather than guessing serving limits.
The flow owns prompt fitting and storage.

Inspect `meta.context.author_notes`, `description` and `commit_messages` when present.
`inline` confirms preparation, not that a reviewer read every word.
Report `summarized` or `truncated` separately from `offloaded`.
Missing, unknown or `unavailable` delivery remains a gap.
Preserve submitted context and verify matching support. Do not infer consumption.
See the [receipt dictionary](context-delivery.md). Never include secrets.

## Context references

`--ticket <full-url>` supplies fetchable ticket context. A bare key is detected metadata only.
Optional `context_refs` merge and deduplicate. Their labels are data, not instructions.

- `ticket`: supplies ticket context.
- `spec`: supplies Requirements Gap context.
- `code_dependency`: adds repository/branch/PR links to author-notes context.
- Generic or unknown kinds remain deferred.

Cross-repository routing, when enabled, selects only supplied candidates.
Refs neither discover repositories nor enable review.
Provider behavior follows Git review.
Inspect `meta.context.spec`. Code dependencies have no consumption receipt.
Do not infer fetching, use, merge, release or deployment from a reference.

## Examples

```json
{
  "decisions": [
    "The user requested macOS-only support; their rationale was not recorded.",
    "The user chose full tests after opening the PR to keep PR creation fast.",
    "The coding agent reused run_cmd to preserve its existing cancellation handling."
  ],
  "notes": "Expected: subprocess failures return a diagnostic. Existing guard: src/commands.py:run_cmd catches CalledProcessError. Verification: command tests passed; live execution was not tested.",
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added cancellation to the API; this round includes new behavior."
  ],
  "context_refs": [
    { "kind": "ticket", "url": "https://acme.atlassian.net/browse/PAY-412" },
    { "kind": "spec", "url": "https://acme.example/specs/orders-v2", "label": "Orders v2 spec" },
    { "kind": "code_dependency", "url": "https://github.com/acme/orders-api/pull/42", "label": "API change" }
  ]
}
```

Older-CLI representation of the same context (only the narrative field name changes):

```json
{
  "decisions": [
    "The user requested macOS-only support; their rationale was not recorded.",
    "The user chose full tests after opening the PR to keep PR creation fast.",
    "The coding agent reused run_cmd to preserve its existing cancellation handling."
  ],
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added cancellation to the API; this round includes new behavior."
  ],
  "context_refs": [
    {
      "kind": "ticket",
      "url": "https://acme.atlassian.net/browse/PAY-412"
    },
    {
      "kind": "spec",
      "url": "https://acme.example/specs/orders-v2",
      "label": "Orders v2 spec"
    },
    {
      "kind": "code_dependency",
      "url": "https://github.com/acme/orders-api/pull/42",
      "label": "API change"
    }
  ],
  "summary": "Expected: subprocess failures return a diagnostic. Existing guard: src/commands.py:run_cmd catches CalledProcessError. Verification: command tests passed; live execution was not tested."
}
```

## CLI examples

These examples illustrate the canonical scope, authorization and execution rules in SKILL.md.
Confirm flags with `qodo review --help`; they do not replace the runtime gate.

```
review_base=$(git merge-base HEAD origin/main) || { printf '%s\n' 'Cannot resolve merge base for origin/main; fetch missing history or choose the correct target.' >&2; exit 1; } # use the intended target branch
qodo review --base "$review_base" --context-file - <<'EOF' # branch changes, WITH context
{ "notes": "<expected behavior, constraints, supporting evidence and uncertainty>",
  "decisions": ["<actual choice, its user/agent owner, and known rationale>"],
  "recent_work": ["<what changed since the previous review; fixes only or added behavior>"] }
EOF
qodo review --base "$review_base" --context-file ctx.json # context from a file
qodo review --base "$review_base" --ticket <TICKET_URL> ... # ticket URL (repeatable)
qodo review --base "$review_base" --json ...              # machine-readable findings
qodo review --base "$review_base" src/ test/ ...          # limit to paths (git pathspecs)
develop_review_base=$(git merge-base HEAD origin/develop) || { printf '%s\n' 'Cannot resolve merge base for origin/develop; fetch missing history or choose the correct target.' >&2; exit 1; } # another target branch
qodo review --base "$develop_review_base" --json --context-file ctx.json # another target branch
qodo review --base "$review_base" --async --json --context-file ctx.json # ordinary checkpoint: auto
qodo review --base "$review_base" --fast --async --json --context-file ctx.json # purposeful light checkpoint
qodo review --base "$review_base" --json --context-file ctx.json      # final: auto
qodo review --base "$review_base" --deep --json --context-file ctx.json # justified deep review
qodo review --base "$review_base" # only when there is genuinely no material session context
qodo review status <operation-id>            # collect an --async result (exit 2 = still running)
qodo review --help                           # exact flags (renders offline)
```

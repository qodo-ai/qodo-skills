# Review-turn context

Before each new review, refresh `recent_work` in the context file with what changed since the
previous review of this branch or worktree. Keep the overall rationale in `summary` and durable
choices in `decisions`; `recent_work` is the current turn's work, not the whole session history.

Describe the actual changes and whether they only address earlier findings or add behavior.
Bug fixes, regression tests and behavior-preserving cleanup can be fixes only. A turn that adds
a capability or extends an interface includes new behavior, even when it also fixes findings.
Do not infer fixes only from a small diff or from having addressed one review finding.

For a fixes-only turn:

```json
{
  "summary": "Preserve the existing retry behavior while correcting error handling.",
  "decisions": ["Keep the existing retry limit and public API."],
  "recent_work": [
    "Fixes only: corrected the timeout path identified by the previous review.",
    "Added a regression test for that timeout; no capability or interface was added."
  ]
}
```

For a turn that also adds behavior:

```json
{
  "summary": "Support cancellation while preserving retry behavior.",
  "decisions": ["Cancellation uses the existing operation ownership checks."],
  "recent_work": [
    "Corrected the timeout finding from the previous review.",
    "Added cancellation to the public API; this turn includes new behavior."
  ]
}
```

Send this through `--context-file` (file or stdin), or keep `.qodo/session-context.json` updated.
For a prepared MCP review, put the same notes in `params.session_context.recent_work` after
checking the live input schema. Preserve the original notes and arguments on an uncertain
submission retry; result collection does not submit new notes or rerun the review.

Keep entries oldest first. At most 50 strings of 2,000 characters are accepted, and a CLI
context file has a 64KB total limit. Condense oversized notes before submitting; the client
rejects them rather than silently truncating them.

The engine reads these notes only to judge fix-loop intent. They are not rendered into the
review or included in the checkpoint profile hash. They are author context, not an override:
the existing detector still checks eligibility and the judge decides whether there is new
behavior. In an otherwise eligible round, missing notes, an unclear verdict or judge failure
keep narrowing; only a `new_behavior` verdict exits it. A fixes-only statement alone does not
make a round eligible. Refresh the notes even when the engine may reuse an unchanged snapshot.

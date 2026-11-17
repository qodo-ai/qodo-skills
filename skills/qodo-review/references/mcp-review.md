# MCP local-review execution

Read before using the QAR MCP pre-PR review path.
The [main Skill](../SKILL.md) owns timing, context, effort, finding response and readiness.

## Collect local input safely

Prefer `qodo review` when available.
`start-pre-pr-review` accepts a prepared `diff`, `base_sha`, repository locator and context.
It cannot read the coding worktree.

Use it only with a tested local collector that:

- Produces the intended scope with the CLI's safety exclusions.
- Reports omitted files.
- Verifies that the comparison base is fetchable.
- Retains the submitted snapshot and context.

An ad hoc `git diff` is not equivalent coverage.
Without a suitable collector, report that MCP-only local review cannot safely cover this worktree.
Do not claim completion or substitute an unrelated checkout.

## Submit and collect

Inspect live schemas. Check `isError` before interpreting receipts.
Skip CLI version, identity and shell steps when using the trusted MCP connection.

For ordinary prepared worktree reviews, set `review_scope.stream_id` to SHA-256 of a JSON array
containing the resolved real worktree root. Include the resolved working directory for path-limited reviews.
The value is exactly 64 lowercase hexadecimal characters, not a UUID.
Reuse the identity across compatible checkpoints. Do not invent a collector mode the schema does not support.

Retain the same `request_id` and exact arguments after an uncertain start.
This is the start tool's logical-action retry key. Do not invent a separate `idempotency_key` argument.
Poll `get-managed-agent-operation` at its advertised interval.
Fetch all `get-managed-agent-result` chunks.
Verify their reported digest and byte count before interpreting the artifact.
These are short lifecycle calls, not MCP Tasks.

Use the same context, coverage and authority rules as the CLI path.
Preserve unavailable results and actual errors. Never submit a second review just to collect the first.

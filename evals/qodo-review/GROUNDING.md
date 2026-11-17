# Grounding follow-up, not a replacement grade

Checked on 2026-11-17 after local finding
`a876eb5e-2c75-4232-8c96-7fe9eeb9e730`.

The [iteration-7 MCP candidate answer](../../test/fixtures/qodo-review-behavior/history/iteration-7/mcp-local-triage/candidate/response.md)
conditionally recommends replaying an exact request when
`reconciled: false` is returned. Its anonymous grader correctly left that claim
unverified: the permitted prompt and answer did not establish that response field
or recovery contract. The narrow metadata-key assertion still passed. Neither
that pass nor the 32/32 total establishes complete factual grounding.

A later read-only source check through Qodo retrieved
`Codium-ai/pr-agent-pro@7d26418c0ea7e88cb9355df21db335a92c92cd1b`,
`pr_agent/servers/findings_status_api.py:88–108`. Lines 103–105 explicitly document
`reconciled` as downstream convergence, with false safe to retry because the
transition already stands. Lines 95–101 preserve the stored rationale on replay
and prohibit retrying a conflicting terminal state.

Source: [pinned contract](https://github.com/Codium-ai/pr-agent-pro/blob/7d26418c0ea7e88cb9355df21db335a92c92cd1b/pr_agent/servers/findings_status_api.py#L88-L108)
(checked: 2026-11-17; repository access required).

This supports that particular conditional advice; it does not establish the
deployed revision, perform a status write, or independently verify every claim.
The original prompt, assertion, answer, `claims`, `eval_feedback`, provenance and
judgment are unchanged. No agent execution or grading was repeated for this source
check, and it is not retroactive evidence available to that anonymous grader.
Iteration 8 is a separate comparison of changed instructions and fixtures; its MCP
prompt explicitly supplies the response/replay contract before execution and grading.

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

This establishes the Engine endpoint's retry contract, not MCP transport behavior.
The earlier conclusion that it supported the MCP advice was too broad.
It does not establish the deployed revision, perform a status write, or independently verify every claim.
The original prompt, assertion, answer, `claims`, `eval_feedback`, provenance and
judgment are unchanged. No agent execution or grading was repeated for this source
check, and it is not retroactive evidence available to that anonymous grader.
Iteration 8 is a separate comparison of changed instructions and fixtures; its MCP
prompt explicitly supplies the response/replay contract before execution and grading.

## Transport correction after hosted finding f0d937b9

Checked on 2026-11-17 through read-only Qodo source retrieval:

- `qodo-ai/qodo-agent-runtime@5ada587fa6d99c00651a894428e12bf9bbe11b15`,
  `src/qar/managed_tools/mcp_server.py:730–755,810–844`: a repeated mutating MCP key
  selects the prior operation. A completed operation returns its stored result.
The handler does not execute again.
- At that same QAR revision, `pr_review_session/specs.py:239–261` marks dismissal
  as mutating. `pr_review_session/tools.py:59–73` forwards its business arguments
  to the status client when the handler executes.
- `Codium-ai/pr-agent-pro@7a227bcf99ea2a8b069dab6fca0f93a8be76a901`,
  `pr_agent/servers/findings_status_api.py:172–199`: a new endpoint invocation
  includes both transitioned and already-transitioned rows in reconciliation.
  `docs/qodo2/finding_status_api.md:24–32,198–205` documents another POST for convergence.

Thus, same-key MCP recovery can recover an uncertain result but cannot retry synchronization.
After verified storage, a separately authorized synchronization attempt needs a new
transport operation/key with unchanged business arguments. An unknown outcome does not authorize key rotation.
The canonical Skill now separates these cases. No QAR or Engine code changed.

Original prompts, answers, grades, provenance and limitations remain unchanged.
In particular, iteration10's triage prompt supplied an overbroad replay assumption.
Its 40/40 totals show compliance with those synthetic inputs, not correct MCP convergence.
The [unchanged iteration10 report](../../test/fixtures/qodo-review-behavior/history/iteration-10/reports/RESULTS.md)
and [grounding note](../../test/fixtures/qodo-review-behavior/history/iteration-10/reports/GROUNDING.md)
remain inspectable. Fresh evidence must use the corrected scenario and instructions.

## Synchronous-result boundary

The fresh iteration11 candidate and baseline both scored 40/41. Both failed the
metadata-only assertion because their proposals assumed an exposed collectible
operation receipt that the case did not establish. The [original failed evidence](../../test/fixtures/qodo-review-behavior/history/iteration-11/manifest.json)
and its report retain those judgments without adjudication or answer repair.

The same pinned QAR revision's `src/qar/managed_tools/mcp_server.py:256–264`
constructs a synchronous success result from the projected tool payload. It does
not add a pollable operation handle. This supports a narrower instruction:
collect only a returned, supported handle. Otherwise recover an uncertain
synchronous reply through the supported exact same-key replay.
The updated fixture explicitly supplies the tool name and no-handle synchronous
contract. It requires the same original business identity and replay protection,
not a relaxed passing grade. Live runtime execution remains unperformed.

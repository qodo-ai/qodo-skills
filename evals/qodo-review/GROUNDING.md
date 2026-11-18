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

## CLI response-identity boundary after local393review

Local review `f68877275686408f9a0178c2254573df` at393a77a reported b7eb6aba:
the CLI cannot expose or verify every identity check requested by the Skill.
Read-only Qodo retrieval of `qodo-ai/qodo-in-cli@c231373136add5afa2d56fec0acd7708844b4da0`,
`src/review-async.ts:295–313,625–669` and `src/review.ts:1790–1815`, confirms that
the fetched operation is classified/rendered without comparing or returning the
transport operation ID. The actual393JSON exposes findings, inventory, review-run
metadata and matching snapshot identity, not a returned operation ID.

The Skill now reports unavailable identity checks rather than inventing evidence.
The CLI reference distinguishes known snapshot association from that missing
transport-ID comparison; a requested handle or review-run ID is not a substitute.
The new synthetic identity-gap case tests this limitation without changing runtime
implementation or claiming a deployed fix. Supporting CLI/Engine/QAR remain frozen.

Two other supported local findings correct conditional mechanics: collection now
stops on failed/empty/non-directory temporary setup before any redirect (ded0ddcb);
MCP result pages keep the initial `extended` value or omission unchanged (9e7e1662).
Deterministic shell checks execute only setup and a harmless marker, never the
status redirect, cleanup loop or a Qodo command.

## Fixture limits found in iteration14

The original full14 comparison scored candidate42/42 and baseline41/42, but its
path-case base is ambiguous: the cases are independent, and case4 explicitly
shares case3's changes/context without giving its own literal base. Refusing
to borrow another case's SHA is defensible uncertainty. Earlier descriptions
of this as merely overlooking a supplied base were too strong. Original grades
and captured inputs remain unchanged; this is a correction to their interpretation,
not a regrade or evidence of candidate uplift.

The candidate also inferred overall helper-fixed readiness from the absence of
other supplied obligations. The resolution assertion did not test that overclaim.
Canonical policy already says one resolved finding does not establish readiness.
The fixture now supplies another original pending/action-required finding and
the grader checks that distinction. Only these two changed groups need fresh
execution; six unchanged14cases retain their original input/run identities.

## Connected-recipe allocation cross-check

Exact286local review `6e3ac863fd4649ecb3c11680730b48d4` returned no new IDs and
retained the original pending records. The cited async allocation source already
has the guard. A direct cross-check found the same genuine defect in the separate
`connected-progress.md` recipe before its result/progress redirects. The same
allocation guard now covers that path; setup-only tests exercise both recipes.
This is a demonstrated instruction defect, not a refix of the guarded async code,
a new runtime change or an author-written resolution of the old finding.

## Invalid-artifact recovery permission

Fresh16scored39/42candidate versus42/42baseline. The candidate correctly rejects
invalid MCP artifacts but assumes permission for one recollection. The fixture
conditions recovery on the Skill; the canonical gate permits a status-transport
retry, not an automatic retry merely because integrity or association failed.
The Skill now makes that distinction explicit. This does not add a retry budget,
change runtime behavior or relax any assertion. Original16judgments remain, including
the grader's limited policy evidence; changed instructions need fresh qualification.

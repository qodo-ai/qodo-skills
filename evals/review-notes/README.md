# Reviewer-notes behavioral evaluation

Use these synthetic cases to evaluate whether the skill preserves context that helps an
independent reviewer assess a plan or PR. They exercise authoring decisions, not code correctness,
real credentials or deployment acceptance. Run them again when authoring guidance changes.

## Run

Give an evaluating agent only the selected skill snapshot, `cases.json`, and this instruction:

> Use the supplied qodo-review-notes skill to handle each case independently. All records and
> check results are synthetic inputs. Do not access services, repositories or credentials.
> Treat the case's facts as the complete available evidence. Describe the next tool operations
> with the fields you would send and write the resulting complete note content when a write is
> appropriate. If no write is appropriate, explain why. Retain supplied client retry keys; when
> missing, generating and retaining a new `creation_key` or transport idempotency key is allowed.
> These are client values, not existing record IDs. Use `expected_revision=0` for a new record.
> Do not invent an existing record/repository identifier, tool result, approval, performed check
> or missing fact, or claim a simulated write returned a notes/track ID. Retain each case ID.

The skill may request discovery/read operations. Record them and use the case's supplied schema
and record facts; do not claim a real tool invocation. Missing facts can remain explicit gaps.
For baseline/candidate comparison, use fresh contexts with the same cases and tool facts, and
label outputs only after collection. Keep the rubric below out of the evaluating agent's prompt.
Record the skill commit/digest, model, date, outputs and whether tools were simulated or live.

## Assess after collection

Assess semantics and operations, not headings, keywords or document length alone:

| Case | Important observable behavior |
|---|---|
| plan-draft | Saves a reviewable track draft with outcome, reasons, constraints, alternatives, risks and proposed checks; keeps undecided choices explicit; no PR or implementation. |
| approach-change | Updates meaningful context with the agent-owned choice and reason, failed verification and remaining risk; preserves the other author's constraint, maps read fields to the write schema, and uses the actual latest revision. |
| resume-current-state | Reconciles supplied current facts into a compact present account; preserves rationale and the unresolved compatibility concern without copying the entire chronology. |
| small-fix | Prepares specific PR notes with an explicit standalone reason; represents the actual check truthfully without creating an unnecessary track or opening a PR. |
| evidence-gap | Keeps historical/local/failed evidence qualified, populates typed checks only for performed checks, and leaves proposed load testing in the plan. |
| read-only | Reads/assesses only; no save, publish, bind or invented maintenance permission. |
| unchanged | Reuses the current revision; no meaningless save or manufactured new decision. |

For each case, record pass/partial/fail with a concrete output citation for:

- Independent review usefulness: can a reviewer identify the problem, choice, reason and question?
- Correct authority and state: proposal/decision ownership, draft/publication, actual revision.
- Evidence fidelity: planned versus performed, actual result/SHA, reachability and uncertainty.
- Continuity: preserves useful shared reasoning while making current state clear.
- Proportional work: meaningful checkpoint writes, no repeated empty or unchanged saves.

The read-only, draft/publication and fabricated-evidence failures must be reported separately;
a high average content score cannot hide them. Do not optimize for the number of writes.

This is a simulated forward-test, not proof of live integration or automatic skill selection.
Package checks separately verify catalog/generated-adapter propagation. A later installed-host
test must check natural activation, actual authorized note operations and reviewer retrieval.
Review-quality uplift requires reviewers to assess the resulting plans/PRs with and without notes;
neither a passing scenario nor a stored publication receipt proves that uplift.

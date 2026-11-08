# Decisions, contracts and failure scenarios

## Compare choices to the plan

Read published PR Review Notes/Development Track Notes first, then an available authorized coding
session, tickets/specs, and the PR description. Use source `inferred` only when code/tests are the
only evidence. Check note applicability against the current head. Never invent who approved a
choice or why it was made.

Inspect changed conditions, triggers, defaults, limits, fallbacks, retries, service/model calls,
data retention and scope. Ask which are explicit requirements and which were chosen during coding.
Write per-PR `decisions` with a short `text`, source, effect, why it matters and changed-line `ev`:

| Status | Evidence needed |
|---|---|
| `unplanned` | Code makes a choice the supplied plan does not address; cite changed lines. |
| `changed` | State the plan in `plan`, then cite how the code differs. |
| `missing` | State the unmet plan; do not invent code evidence for absent behavior. |
| `planned` | State the plan and cite the implementation; include only consequential choices. |

Use `kind: product|technical`, source links in `refs`, and effects such as cost, trigger, volume,
data, security, UX or contract. `notice` says how a silent change would be observed; if unknown,
say so. Check the base's sibling implementation before claiming a new pattern. Do not duplicate
Qodo requirement-gap findings as your own missing decisions. An author acknowledging a concern
is not reviewer acceptance. UI decisions and finding stances remain local in V1.

## Map the contracts before counting files

Top-level `system` contains `summary`, `components`, `contracts` and optional `flows`.
Components identify services, libraries, stores, queues, external systems, infrastructure or UI.
Contracts name endpoints, webhooks, events, queues, tables, schemas/types, flags, config, CLI,
file formats, budgets or capabilities. Include missing prerequisites such as a required installer
or release with `change: missing`; don't represent them as implemented because another PR exists.

For each consequential contract, supply:

- `id`, `name`, `kind`, `change` (added/changed/removed/missing/unchanged), defining component
  in `from`, consuming component IDs in `to`, and the PRs changing it.
- `before`, `after`, `carries` and `reaches`: exactly `all` only when existing callers are
  affected, `new` for a new path, otherwise name the verified affected audience.
- `defined`, `used`, `tests`: changed-code refs `{pr,path,from,to,side?}`; unchanged refs
  `{repo,path,from,to,ref}` with immutable observed identity where available; or explicit
  `{outside:true,component,note}` for a real non-code prerequisite or unavailable evidence.
- Compatibility (`additive|breaking|internal`), reversibility (`door: one-way|two-way`), mismatch,
  open question and dependencies. Never fill a risk/compatibility claim merely to complete a form.

Check both sides: schema shape, identity/revision, timeouts/budgets, error behavior, rollout order
and who still uses the old contract. The engine derives affected PRs/reading tiers/coverage; do not
write those computed results yourself. Missing/truncated code reads remain gaps, even if a path
exists. Reviewer suggestions or empty ownership data cannot establish that CODEOWNERS was checked.

## Judge a credible failure of the changed behavior

Add `impact` rows for distinct failure scenarios. Each names component, changed promise, paths,
PRs, affected workflows, evidence and gaps. `factors` carries three independent assessments:

| Factor | Levels and reasoning |
|---|---|
| `radius` | small: one feature/command; medium: one subsystem; large: shared state, infrastructure or contract. Trace consumers and exposure. |
| `damage` | low: reversible cosmetic issue; medium: recoverable degradation; high: security, money, exposure or data loss. Judge the reached capability. |
| `complexity` | low/medium/high from interacting conditions, state, ordering, concurrency, retries or algorithms. File/line counts and fan-out do not measure this. |

Each factor is `{level,why,ev:[{path,lines}]}`. Leave an unknown factor out: it remains Unknown,
not Low, and cannot unlock approval. The engine combines radius × damage and then complexity;
do not hand-author the aggregate Merge Risk. Findings, test/CI counts and fixes alone do not lower
these factors. A fix changes risk only if its actual mechanism changes reach, damage or complexity.

Assess feature flags as if the path is enabled. Count unflagged startup/migration/background work.
Only a demonstrated transaction, isolation or fallback contains the specific failure; a try/except
is not sufficient proof. Distinguish declared team `criticality` from suggested criticality; when
nothing is declared, use `undeclared`. Do not suggest an approval policy. Incomplete file lists,
unknown ownership or missing managed sections stay visible as unknown.

## Make the landing and rollback order executable as a plan

For a high-risk or rollback-sensitive change, add `rollback` with `before`, ordered `steps`,
`one_way` effects and `verify`. Each step's `covers` names affected migration/config/infra paths
or globs. Prepare a restorable snapshot/backup before an irreversible action; name the flag or
operator procedure, reverse dependency order and verification signal. Mark inferred steps and
unknown recovery as gaps. A code revert cannot undo already-exposed data or a rewritten record.

Put deployment checks in `deploy` steps' `verify`. Separate source merge, release, deployment,
provider visibility and user acceptance. This guide prepares a review and local checklist; it does
not authorize merging, publishing, running a migration, changing permissions or posting a decision.

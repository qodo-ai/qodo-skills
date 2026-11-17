# Recorded qodo-review behavior evaluation

Iteration 8 is being prepared for changed reconciliation instructions and the
33-assertion suite. The current manifest still records iteration 7 and is not
passing freshness evidence for the newer bytes. Its original artifacts and exact
inputs are archived in `history/iteration-7/`; they will not be regraded or relabeled.

This directory contains fresh-agent answers, anonymous grader judgments and
runtime-reported provenance for the exact instruction fingerprints in `manifest.json`.
Each case links to its synthetic prompt and assertions under `evals/qodo-review/`.
The parent runner retained final answers; evaluated agents did not save their own outputs.
No reasoning text, credentials, unrelated sessions or raw session archives are included.
Portable responses normalize host temporary roots and trailing line whitespace;
provenance retains both original and portable response hashes.

The candidate is the current instruction snapshot. The baseline is the unchanged
`173cfc700e4ee8a83c20e47abc1edfcd75612354` instructions, not the original pre-rewrite Skill.
Command proposals are synthetic. The agents ran, but Qodo reviews, installations,
Git changes and finding-status writes shown in their answers did not execute.

The offline test suite validates artifact integrity, complete case/assertion coverage,
passing candidate judgments and matching instruction/fixture fingerprints. It does
**not** rerun the model or make these author-recorded outputs independent CI execution.
Missing, stale or failing candidate evidence fails that integrity gate.
Release preparation updates the catalog-owned Skill version and CLI attribution
stamp. The gate maps only those stamps to the evaluated version before comparison;
all other instruction bytes must match. Original raw fingerprints stay unchanged.
The current manifest also fingerprints each `case.yaml`, verified against both
original staged evaluation inputs. `snapshots/baseline.json` contains the original
signed commit and Skill blobs as text, plus readable path-tree entries. The
integrity test reconstructs and hashes each object in a private temporary Git
object store and compares the actual immutable source
hashes, without requiring network access or retention of the PR's branch history.
Artifact and adjudication reads reject symlinked files and ancestor directories.
The current comparison is32/32 for both versions after the documented auto-default
adjudication. `adjudication/` retains both initial31/32 judgments and actual CLI help.
`history/iteration-6/` preserves the earlier29/29 versus27/29 comparison at its
original fingerprints; `pre-correction/` retains the earlier exact-base failure.

`npm run eval:qodo-review` prepares a minimal standard plugin evaluation.
Add `--run` only to opt into billed model execution; it is not part of default CI.
Normal trust prompts remain enabled. The standard harness path and these native
OpenCode executions are distinct methods; staging a plugin is not model execution.

One run per case/configuration cannot establish reliability, causal improvement,
natural activation, installed-runtime compatibility or savings. Read grader
`claims` and `eval_feedback`, including concerns outside the counted rubric.
The later [grounding follow-up](../../../evals/qodo-review/GROUNDING.md) is separate
source evidence, not a replacement grade or another agent execution.
Read-only input files and runtime-reported read-tool inventories are not a complete
operating-system confinement audit. Historical results remain in
`evals/qodo-review/RESULTS.md`; a new report does not relabel those snapshots.

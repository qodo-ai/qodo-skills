# Recorded qodo-review behavior evaluation

This directory contains fresh-agent answers, anonymous grader judgments and
runtime-reported provenance for the exact instruction fingerprints in `manifest.json`.
Each case links to its synthetic prompt and assertions under `evals/qodo-review/`.
The parent runner retained final answers; evaluated agents did not save their own outputs.
No reasoning text, credentials, unrelated sessions or raw session archives are included.

The candidate is the current instruction snapshot. The baseline is the unchanged
`44ed636386f6b289f9b5bd0db510f204deb10507` instructions, not the original pre-rewrite Skill.
Command proposals are synthetic. The agents ran, but Qodo reviews, installations,
Git changes and finding-status writes shown in their answers did not execute.

The offline test suite validates artifact integrity, complete case/assertion coverage,
passing candidate judgments and matching instruction/fixture fingerprints. It does
**not** rerun the model or make these author-recorded outputs independent CI execution.
Missing, stale or failing candidate evidence fails that integrity gate.
Release preparation updates the catalog-owned Skill version and CLI attribution
stamp. The gate maps only those stamps to the evaluated version before comparison;
all other instruction bytes must match. Original raw fingerprints stay unchanged.

`npm run eval:qodo-review` prepares a minimal standard plugin evaluation.
Add `--run` only to opt into billed model execution; it is not part of default CI.
Normal trust prompts remain enabled. The standard harness path and these native
OpenCode executions are distinct methods; staging a plugin is not model execution.

One run per case/configuration cannot establish reliability, causal improvement,
natural activation, installed-runtime compatibility or savings. Read grader
`claims` and `eval_feedback`, including concerns outside the counted rubric.
Read-only input files and runtime-reported read-tool inventories are not a complete
operating-system confinement audit. Historical results remain in
`evals/qodo-review/RESULTS.md`; a new report does not relabel those snapshots.

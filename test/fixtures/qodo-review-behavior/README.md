# Recorded qodo-review behavior evaluation

Iteration 10 records 16 completed executions and eight anonymous graders over
40 assertions. Candidate `841379dd3f1bc2d6927b5275fa8d8c1cad190ba8` and prior
rewrite `6385a42e83ac028349ff1c153a788a812a850bf5` both pass 40/40.
This establishes no rubric uplift or reliability. Original histories 6/7/8/9,
including their answers, judgments, instructions and exact case inputs, are retained.

This directory contains fresh-agent answers, anonymous grader judgments and
runtime-reported provenance for the exact instruction fingerprints in `manifest.json`.
Each case links to its synthetic prompt and assertions under `evals/qodo-review/`.
The parent runner retained final answers; evaluated agents did not save their own outputs.
No reasoning text, credentials, unrelated sessions or raw session archives are included.
Current responses retain the parent-captured bytes and their recorded hashes.
Older archives retain their documented normalization and original/portable hashes.

The candidate matches the current instructions. The baseline is the preceding
`6385a42` rewrite, not the original pre-rewrite Skill. Both configurations use
the same case inputs captured at `841379d`.
Each run's recorded fixture commit and complete input-fingerprint map must match
the current eight-group manifest; changing a case and only relabeling its manifest
hash fails. Paths must match the case/configuration namespace, and the recorded
case/configuration identity must match too. Empty assertion lists fail.
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
The current comparison is 40/40 for both versions. Common verified CLI help was
supplied to every anonymous grader before grading; its hash is in `grading_evidence`.
No iteration-10 adjudication occurred. `history/iteration-7/` retains the original
32/32 comparison, both initial 31/32 judgments, actual help and 96 artifact hashes.
`history/iteration-6/` preserves the earlier29/29 versus27/29 comparison at its
original fingerprints. `history/iteration-8/` and `history/iteration-9/` retain
the original 33/33 matrix and focused 5/5 MCP comparison, without regrading them.
All four archive entries and 40/96/104/74 listed artifacts are mandatory integrity
checks, not optional manifest branches. This does not certify unlisted history.
`pre-correction/` retains the earlier exact-base failure.

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
`evals/qodo-review/HISTORY.md`; a new report does not relabel those snapshots.

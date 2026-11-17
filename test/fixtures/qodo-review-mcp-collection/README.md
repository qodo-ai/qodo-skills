# Historical focused MCP collection evidence

This is the unchanged iteration-9 record, not current instruction evidence.
Current results are in `../qodo-review-behavior/`. Its original instructions and
all inputs are retained in `../qodo-review-behavior/history/iteration-9/`.

Iteration 9 executes only the newly added `mcp-collection` case: two fresh native
agents and one anonymous grader, five assertions for each configuration.
Candidate instructions and common fixtures come from signed
`81019a09de621dd0bad5abf94f2a658a2d5176f1`; baseline instructions come from signed
`6385a42e83ac028349ff1c153a788a812a850bf5`.
The candidate instruction bytes are unchanged from the iteration-8 candidate.

`manifest.json` distinguishes the one evaluated case from the eight staged input
cases. Each run retains the complete 54-input fingerprint map from its immutable
staging, not only the new prompt. The gate checks its retained inputs and candidate
instructions, original responses/grades/provenance and every counted assertion.
Commit fields are recorded labels; this is not tamper-proof model attestation.
The baseline instruction hashes match the primary suite's offline Git-object proof.

Both configurations score 5/5. This adds coverage, not evidence of uplift,
reliability or savings. The original seven-group 33/33 comparison is unchanged in
`../qodo-review-behavior/history/iteration-8/`; no old answer or grade is replaced or relabeled.
That iteration's wrapper staged eight groups and 38 assertions; it did not execute
a fresh eight-group comparison. The later current comparison is reported separately.

The agents used read-only tools. Proposed MCP calls, integrity checks and collection
recoveries were not executed; the fixture supplies the checker's digest/length
results. The grader preserves unverified 15-second recovery-delay claims and an
unresolved rubric question about the additional “ready locally” label.
Passing totals do not turn those claims into independently grounded facts.

Only final answers and safe runtime model/timing/read-call metadata are retained.
Default CI verifies recorded evidence, not models. Billed Claude evaluation,
natural activation, live MCP/runtime compatibility and full local-to-Git
qualification remain unperformed.

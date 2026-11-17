# Agent-evaluation results

## Operation identity and evidence binding (iteration 10)

Sixteen fresh native OpenCode executions and eight anonymous graders completed on
2026-11-17. Candidate instructions and common case inputs come from signed
`841379dd3f1bc2d6927b5275fa8d8c1cad190ba8`; baseline instructions come from the
prior rewrite at `6385a42e83ac028349ff1c153a788a812a850bf5`, not the original
496-line Skill. There is one execution per group/configuration.

| Group | Candidate `841379d` | Prior `6385a42` |
|---|---:|---:|
| Milestone and final scope | 8/8 | 8/8 |
| Compatibility boundaries | 5/5 | 5/5 |
| Follow-up and finding state | 5/5 | 5/5 |
| Recovery and readiness | 6/6 | 6/6 |
| Fallback invocation | 2/2 | 2/2 |
| Recovery policy guards | 3/3 | 3/3 |
| MCP local triage | 4/4 | 4/4 |
| MCP collection and identity | 7/7 | 7/7 |
| **Assertion total** | **40/40** | **40/40** |

Both configurations pass. In particular, both reject wrong-operation and
overlapping-page fixtures, so this demonstrates additional coverage, not causal
uplift, reliability or proof that the previous guidance necessarily failed.
The canonical gate now explicitly rejects mismatched operation/snapshot identity
and incomplete/noncontiguous pages. The conditional MCP procedure names the
operation, cursor, offset and stable-metadata checks before parsing.

The main Skill is **300 lines / 19,322 bytes**. Raw SHA-256:

```text
SKILL.md 757e975ff6230e96ffb9581efbb36620171e3f0230bbc295434f161000c296a4
```

[The manifest](../../test/fixtures/qodo-review-behavior/manifest.json) binds every
current instruction, all eight case/YAML/prompt/grader inputs, every response,
judgment and safe runtime provenance record. Every run retains the same complete
56-input map and its actual case identity. Artifact paths must match the exact
case/configuration namespace; recorded case/configuration must also match.
Candidate and baseline each have a nonempty, strictly boolean assertion result.
The baseline's unchanged readable Git-object proof binds its exact source offline.

The fresh responses are retained byte-for-byte from parent capture. Harness
configuration labels are retained separately from candidate/baseline roles.
Common verified CLI help was supplied to every anonymous grader before grading.
No execution retry, grading adjudication or answer repair occurred.

## Measurement and limits

Both configurations used `openai/gpt-6.1-sol-fast#max`. Runtime-reported group means:

| Metric | Candidate | Prior |
|---|---:|---:|
| Assertion pass rate | 100% | 100% |
| Assistant-message seconds | 63.61 ± 18.69 | 63.44 ± 20.28 |
| Cache-inclusive tokens | 94,652 ± 12,888 | 94,832 ± 12,717 |

These spreads are across eight different groups, not repeated-run variance.
There were 42/43 read-only calls and zero reported tool errors. Timing excludes
orchestration and is not journey latency; cache-inclusive tokens are not billed
cost or unique prompt size. No speedup or savings is established.
The standard benchmark and static viewer were generated with iteration 9 as the
previous workspace.

Original grader `claims` and `eval_feedback` remain intact. Unverified details
include exact status/JSON option combinations, response-field names, MCP tool/
envelope names, update/retry policy, Engine analysis reporting and literal context
preservation without an existing-context merge fixture. One baseline also suggests
a checkpoint-storage recovery route that the grading inputs do not establish.
Passing totals do not ground these additional claims.

All operational Qodo/MCP/Git/installer/finding commands were proposals. The MCP
fixture supplies the integrity checker's output; no real collection or digest
verification ran. Natural activation, complete OS confinement, live runtime
interoperability and full local-to-Git acceptance remain unqualified. Billed Claude
evaluation remains unperformed; default CI validates recorded evidence, not models.

## Deterministic guards and retained history

The evidence helper now rejects empty assertion lists explicitly. The former
direct JavaScript helper could accept a zero-item `NaN` pass rate; JSON cannot
encode `NaN`, so no recorded-JSON bypass is claimed. Negative checks cover empty
candidate/baseline cases and cross-case/configuration response, grade and
provenance paths plus recorded identity mismatches. These tooling guards did not
independently trigger model runs; the canonical instruction and MCP case changes did.

History entries 6/7/8/9 are mandatory and check **40/96/104/74** original artifacts,
full inventories and manifest hashes. Earlier iteration-8 33/33 judgments and
iteration-9 focused 5/5 judgments, instructions, inputs and common grading evidence
remain unchanged. They are not relabeled as iteration-10 results.
The historical focused MCP evidence is tested against its retained instructions
and inputs, not against the newer case.

[HISTORY.md](HISTORY.md) retains earlier reports, failures and grading limitations,
including the first working archive-walker failure and iteration-7 31/32-to-32/32
help adjudication. The old failed source checks and incomplete review remain tied
to their actual snapshots; a new passing result does not erase them.

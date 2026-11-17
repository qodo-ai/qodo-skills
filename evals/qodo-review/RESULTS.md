# Agent-evaluation results

## Scope and method

Run on 2026-11-17 in OpenCode. Eight fresh agents used either the baseline or
candidate Skill, one execution per configuration for each of four fixture groups.
Each agent read only its selected instructions/references and the case prompt,
not the graders or the other output. Four independent graders assessed anonymous
A/B pairs against the supplied assertions with output citations.

The agent executions occurred. Review commands, installation, repository changes
and service/finding writes were **proposed, not executed**. These are instruction
behavior checks, not live review or installed-runtime integration tests.
The [README](README.md) describes how to repeat them.

## Rubric results

| Group | Candidate | Baseline |
|---|---:|---:|
| Milestone and final scope | 7/7 | 5/7 |
| Follow-up and finding state | 5/5 | 5/5 |
| Recovery and readiness | 6/6 | 6/6 |
| Compatibility boundaries | 5/5 | 4/5 |
| **Total** | **23/23** | **20/23** |

These totals count individual assertions. The local benchmark viewer also shows
an equally weighted group mean; that is not the assertion-weighted total.

The baseline selected `--fast` for an ordinary milestone and the summary-only
first-review case. It also failed to distinguish local readiness from unverified
PR handoff in `already-covered`. The compatibility grader noted that effort was
implicit in the summary-only prompt: this is a workflow-policy comparison, not
evidence that the baseline cannot parse version 2.0.0 or preserve `summary`.

Both original versions passed the finding-loop and recovery checks, and both allowed
`light-to-final` and `explicit-fresh`. These preserve behavior; they do not establish
an improvement. The corrected candidate explicitly permits those final/fresh
reasons without requiring an artificial code edit.

## Later focused fallback regression

After that comparison, command examples were clarified to retain the resolved
invocation, and case metadata stopped granting Write. Two fresh agents handled
`fallback-invocation`: current instructions and the preceding f749503 instructions.
The runner retained their final answers; agents were not asked to write outputs.
Both proposed the exact quoted executable for version, submission and collection,
kept auto/base/context, and left collection conditional on an actually returned ID.
Both passed the two focused assertions, assessed inline with command checks.

This is a narrow clarification check, not a rerun of the 23-scenario comparison,
an independently graded new comparison, or proof that the preceding wording
necessarily failed. The prompt explicitly requests invocation retention.
No operational side effects or filesystem confinement were audited.

The focused candidate main is 252 lines / 14,710 bytes. Its SHA-256 values are:

```text
main       b34cc9ccc940bc3a189cd02c8b94abcbb14dab084b90421c1e8b31c5ce7460b3
with refs  30611e076f77b7348531c952c0bc2451ff9ed1c65a01d0402ff32ad6d6627d04
```

## Grounding limitation outside the rubric

The candidate's milestone output, line 50, says **“The supplied slice tests passed.”**
The fixture says only **“I finished and tested a coherent API implementation slice.”**
No passing result was supplied. The independent grader marked the claim unverified.
The seven scope assertions did not test that inference, so **23/23 is not perfect
factual grounding or perfect behavior**. Do not infer a passed check from “tested.”

The follow-up prompt explicitly requests auto, so it does not independently test
natural effort selection. Graders did not see the Skill snapshots; extra runtime
constants were left unverified rather than assumed false.

## Hosted-recovery guard check

Hosted review then identified three omitted or weakened recovery safeguards:
validate the selected ordinary updater's compatible target before changing runtime,
stop safely when no CLI exists, and honor user/task retry restrictions even when
the server error permits retry. These were restored together in the CLI reference.

Two fresh agents handled `recovery-policy-guards` with corrected or preceding
845868e instructions. Both stopped for each failed/no-update/incompatible target,
kept missing installation blocked on separate authority and a checksum-pinned
installer, and requested approval before the user-forbidden retry. Both passed
three inline-assessed assertions. Parent-retained answers were not operational
execution; no independent new grader or filesystem audit was performed.
The fixtures explicitly supply conditional approval and retry restrictions, so
both passing is not proof that the preceding text necessarily failed in practice.

Main remains 252 lines / 14,710 bytes with the same main digest as the focused
fallback check. The corrected instructions-plus-references digest is:

```text
5ca6968373545995457d6afb9581bfd255e36d145a7fb67b6e7a2ff2e3d001eb
```

This check is separate from both earlier comparisons; their scores are not
relabelled as executions of these later reference edits.

## Exact evaluated instructions

The candidate main Skill and every Markdown reference matched commit
`f7495033fa2ca112daeda404af930c8db454554a` byte-for-byte after the stopping-rule
and explicit-path correction. These scores describe that snapshot, not later edits.

| Snapshot | Main lines | Main bytes |
|---|---:|---:|
| Baseline at `80240e3f5b40d4b8e39935926770f7be0ddb5cde` | 496 | 39,076 |
| Candidate | 251 | 14,609 |

SHA-256 of the main `SKILL.md`:

```text
baseline  6414a0ab04bcf537554b9e9d9b66bb4918a8f2f0d0bf4c12bc7831d069b6ac5b
candidate 882923d63f19ee94660006c6e7f2f80db3e44f7e3410b0c47f3b62a54906a811
```

SHA-256 of instructions plus references:

```text
baseline  e8710b8b4b42b2d396c4df755cda63ad09ebbb84238ae4b0ab96e2f1f528e418
candidate c24f39daf2b4d18b6b09b16d787f26ce36719d68c89106e353124b347ec29ba7
```

To reproduce the combined fingerprint, process `SKILL.md` first, then sorted
`references/*.md`. For each, hash its Skill-relative POSIX path, a NUL byte, its
unmodified file bytes and another NUL byte into one SHA-256 stream.

## Evidence limits

- Model IDs, durations, tokens, tool-call counts and error counts were not exposed.
  They remain unknown/null, not zero. The runs cannot be reproduced exactly from
  a model identifier or random seed that was never recorded.
- One run per group/configuration does not establish variance, reliability or
  statistical significance. Fixtures and assertions were authored for this change.
- Version cases cover decisions at 1.6.0, unparseable, 2.0.0 and 2.3.1 inputs,
  not actual old executables, deployments or runtime interoperability.
- No natural activation, audited tool side effects, hosted finding reuse,
  reviewer-quality uplift, latency improvement or savings were established.
- Responses, grades, anonymous mapping, benchmark and the generated static viewer
  are retained locally by the author, not published CI evidence. This concise
  report is not a substitute for those artifacts or an independent rerun.
- Those native runs permitted output-file writes by instruction, without an audited
  filesystem restriction. Current case metadata removes Write; runners retain
  responses outside read-only inputs. This is not retroactive proof of confinement.
- Deterministic source/package tests and native manifest validation are separate
  checks. `npm test` does not run these model evaluations or authorize billed CI.

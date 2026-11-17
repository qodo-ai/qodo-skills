# Local-review Skill behavior checks

These synthetic cases test coding-agent decisions, not reviewer quality or live integration.
Behavioral runs execute the supplied Skill in fresh agent contexts against the fixtures.
Only the proposed review commands and service operations are simulated, not the agent runs.
They contain no service credentials and authorize no service, finding or repository writes.
Keep them outside the packaged Skill so test prompts do not ship as agent instructions.
Each case uses the skill-creator `prompt.md`, `case.yaml` and `graders/` layout.
The staging command puts these folders in the temporary plugin's `evals/`.

## Run

`npm run eval:qodo-review -- --output-parent <directory-outside-the-repo>` stages
the committed HEAD Skill, all eight committed cases and their graders as a minimal plugin.
It prints the exact `claude plugin eval` command and the staging directory.
The full instruction/fixture fingerprint manifest is written to that directory's `manifest.json`.
Staging does not run a model. Add `--run` only to opt into billed evaluation on
your Claude account; normal plugin trust prompts remain enabled. The installed
CLI must expose `claude plugin eval --disallow-tools` (Claude Code 2.1.299 or later).
Before `--run`, the wrapper checks that option through offline help; it never
silently drops tool restrictions for an older evaluator. Staging itself needs no Claude CLI.
`--ref <full-40-character-commit-sha>` selects that exact Skill commit with cases
from the captured HEAD commit. Abbreviated hashes, branch names and tag names are rejected.
Commit selected case inputs before staging; without `--ref`, the Skill inputs
must also be committed. The wrapper makes no commit or index change for you.
All model-input bytes come from verified Git blobs, never copied checkout paths.
Concurrent checkout replacements therefore cannot redirect model inputs to host files.
Dirty selected inputs stop staging; unrelated README/results/agent-metadata edits
do not block it. The same selectors govern model-input collection and dirty-input
checks, including selected additions, deletions, renames and index-only changes.
Selected untracked additions still stop when local or global Git ignore rules hide
them. Ignored non-input files remain outside the gate; working files are never copied.
Selected `assume-unchanged` or `skip-worktree` entries also stop staging because
ordinary Git diffs cannot prove they are clean. The wrapper never clears those
flags or changes the operator's index.
Recognizable case/grader inputs with invalid names or layouts fail instead of disappearing.
Use lowercase-kebab case directories and direct Markdown files under `graders/`.
Nested graders, unsupported grader filenames and malformed case paths also fail when ignored or uncommitted.
A captured manifest names both exact commits
and every staged fixture fingerprint. Replace refs and lazy object fetching are disabled.
First-use trust requires an interactive terminal. The command intentionally omits
the evaluator's `--json` mode, which suppresses its trust prompt; aggregate JSON
still goes into the output directory. It never supplies `--trust-plugin` for you.
Non-regular committed inputs are rejected, and the selected commit must contain the Skill.

The standard harness executes each case with its LLM graders, emits JSON and HTML,
and gates shell/write tools. Inputs are read-only; real MCP servers, scaffolds,
report publication and operational reviews are not enabled. This still does not
prove complete filesystem confinement. The `Skill` tool is permitted so the
actual plugin instructions can load; it does not grant file or service writes.

For another fresh-agent harness:

Give a fresh agent one case prompt and only the selected Skill snapshot.
Let it read that snapshot's references as needed.
Use the supplied facts as complete synthetic evidence.
Do not load another installed version, access live services or make repository changes.
The runner, not the evaluated agent, saves the final response in an isolated output directory.
Keep Skill snapshots and fixtures read-only. Do not grant Write merely to retain outputs.
If a harness cannot enforce those boundaries, disclose that limitation instead of claiming isolation.
Repeat with the baseline snapshot in a separate fresh context.
Do not supply the graders to the executing agent.

The first four groups cover:

- Milestone timing, ordinary auto, compatible reuse, dirty-worktree final scope and report-only authority.
- Feature/mixed follow-ups, changed notes, earlier backlog, duplicate findings and semantic fix evidence.
- Accepted/uncertain operations, persistence gaps, old results, entitlement and an explicit review budget.
- Exact version fixtures (1.6.0, unparseable, 2.0.0 and 2.3.1), summary-only input,
  explicit path scope and the missing-MCP-collector boundary.

`fallback-invocation` is a later focused regression for reusing a trusted executable
whose path contains a space. `recovery-policy-guards` checks updater-target validation, a missing CLI
and user-forbidden automatic retries after the hosted review's recovery findings.
Both were included in the six-group, 29-assertion comparison. Historical
23-assertion and focused results remain tied to their earlier snapshots.
`mcp-local-triage` adds metadata-only replay protection, a missing-transport stop
and honest prior/conflicting outcomes. Its corrected scenario separates uncertain-write
recovery from a new authorized synchronization attempt. The older same-key synchronization
assumption is preserved as historical evidence, not accepted as transport qualification.
`mcp-collection` adds seven assertions for eligible submission, complete chunk
verification, ineligible collection, wrong digest/byte count, a foreign operation
and overlapping pages. The CLI identity-gap case adds one assertion that missing
response identity is reported, not invented. The wrapper stages eight groups and42assertions.

## Recorded evidence and CI

[RESULTS.md](RESULTS.md) gives current and historical snapshot-specific results.
[Recorded evidence](../../test/fixtures/qodo-review-behavior/README.md) includes
final answers, anonymous judgments, exact fingerprints and safe runtime provenance.
Iteration 10 records 40/40 for candidate `841379d` and prior rewrite `6385a42`.
Both reject the new identity/page cases; no uplift or reliability is established.
Iteration11's later candidate `2e70a9a` and baseline both scored40/41. The failed
metadata-only receipt assumptions, original answers and judgments are archived unchanged.
The subsequent conditional-handle comparison is recorded below.
Iteration12 completed at55976bc with both40/41. Both pass the corrected MCP-triage
checks; the candidate fails prior-context preservation and the baseline overlooks
the supplied base. Its147original captured artifacts remain unchanged.
Only the follow-up case was refreshed after supplying concrete prior context:
two executions and one anonymous grader,5/5for each version. The scoped current
manifest combines those5assertions with seven unchanged12cases: candidate41/41,
baseline40/41. It checks an exact disjoint union, not a new full-matrix run.
Original iteration-8 33/33 and focused iteration-9 5/5 results remain archived unchanged.
The preceding iteration-7 native-agent result is 32/32 for both corrected and prior `173cfc7`
instructions after one documented auto-contract grading adjudication. Initial
31/32 judgments and the CLI help used to reassess them remain inspectable.
These totals do not cover every claim, establish reliability or demonstrate uplift.

Default `npm test` runs offline source/package/staging checks and verifies that
the recorded candidate evidence passes, covers every assertion and matches current
instructions and prompts. Missing, stale or failed evidence fails that gate.
Case YAML is fingerprinted too. The baseline's readable Git object snapshot binds
its raw instruction hashes to the stated signed commit, including in shallow or
squash-merged checkouts. Artifact reads reject symlinked files and ancestors.
Only release-owned version/provenance stamps are mapped to their evaluated values;
the evidence retains its original exact hashes, not a claim of a new model run.
The gate compares each run against its own scope's original fixture commit and
complete captured input map, not a synthetic unified snapshot. Scope records
must use unchanged instruction identities; their selected inputs must match
today's cases. Scope archives seal all captured files and reject extra/missing
artifacts. Selected run identities and captured bytes must remain unchanged. Empty
assertion cases fail. Each assertion needs an output citation with a valid line range.
Anonymous `A.md`/`B.md` labels map through each scope's recorded mapping to the response.
Citation syntax and bounds do not prove that the cited text supports the claim.
Updating the manifest alone cannot bless old answers.
History entries6/7/8/9/10/11/12/13 are required; their40/96/104/74/121/122/148/207inventory entries
are checked. The earlier focused MCP records use their archived inputs/instructions,
not the newer case. Old answers are not relabeled as current runs.
The generated12index is compacted to meet the repository line limit. Its original
bytes remain losslessly encoded and independently hashed; no captured run is normalized.
Scoped13is historical after the local393recipe and CLI-evidence corrections.
Fresh evidence is required for the changed instruction bytes and identity-gap case.
**CI validates the recorded evidence; CI does not execute the agent.**
The standard Claude evaluation wrapper has only been staged/manifest-validated,
not model-executed. Run models separately in a fresh-agent harness or explicitly
opt into `claude plugin eval`; keep any billed CI integration opt-in.
The optional `--run` wrapper requires a directly executable native Claude command.
An npm-only Windows `claude.cmd` shim is not supported; staging remains available.
Do not replace behavioral evaluation with text assertions or claim that package checks prove agent behavior.

Grade the planned behavior and claims with concrete output citations.
Do not let a high average hide unauthorized writes, fabricated completion or duplicate assessments.
Record the exact Skill snapshots, model, outputs and whether operations were simulated.
Structural tests are only guardrails. These cases are a simulated forward-test, not proof of
natural skill activation, live local-to-PR reuse, deployed compatibility or reduced latency/cost.

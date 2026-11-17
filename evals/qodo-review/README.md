# Local-review Skill behavior checks

These synthetic cases test coding-agent decisions, not reviewer quality or live integration.
Behavioral runs execute the supplied Skill in fresh agent contexts against the fixtures.
Only the proposed review commands and service operations are simulated, not the agent runs.
They contain no service credentials and authorize no service, finding or repository writes.
Keep them outside the packaged Skill so test prompts do not ship as agent instructions.
Each case uses the skill-creator `prompt.md`, `case.yaml` and `graders/` layout.
For `claude plugin eval`, stage these case folders under the selected Skill snapshot's `evals/`.

## Run

Give a fresh agent one case prompt and only the selected Skill snapshot.
Let it read that snapshot's references as needed.
Use the supplied facts as complete synthetic evidence.
Do not load another installed version, access live services or make repository changes.
Save the response and planned commands/context in an isolated output directory.
Repeat with the baseline snapshot in a separate fresh context.
Do not supply the graders to the executing agent.

The four groups cover:

- Milestone timing, ordinary auto, compatible reuse, dirty-worktree final scope and report-only authority.
- Feature/mixed follow-ups, changed notes, earlier backlog, duplicate findings and semantic fix evidence.
- Accepted/uncertain operations, persistence gaps, old results, entitlement and an explicit review budget.
- Exact version fixtures (1.6.0, unparseable, 2.0.0 and 2.3.1), summary-only input,
  explicit path scope and the missing-MCP-collector boundary.

The default `npm test` suite runs deterministic offline source/package checks.
It does not run paid model evaluations. Run these fixtures separately in a fresh-agent
harness or stage them for `claude plugin eval`; keep any billed CI integration opt-in.
Do not replace behavioral evaluation with text assertions or claim that package checks prove agent behavior.

Grade the planned behavior and claims with concrete output citations.
Do not let a high average hide unauthorized writes, fabricated completion or duplicate assessments.
Record the exact Skill snapshots, model, outputs and whether operations were simulated.
Structural tests are only guardrails. These cases are a simulated forward-test, not proof of
natural skill activation, live local-to-PR reuse, deployed compatibility or reduced latency/cost.

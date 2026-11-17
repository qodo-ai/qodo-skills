---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write]
---

Use qodo-review to handle these independent points in my coding work. Tell me what
you would do next, including any command, scope choice and context you would send.
Do not run a real review. All facts below are synthetic.

The installed CLI is compatible, identity is already verified, and help exposes
--base, --context-file, --fast, --deep, --async, --json, --full and --extended.
It does not expose any committed-only collection option. The intended remote base
is verified and its merge-base SHA is 1111111111111111111111111111111111111111.

1. `milestone`: I finished and tested a coherent API implementation slice. Useful
   independent integration work remains. No review is active, and this slice has
   not been reviewed. I did not request quick/deep effort or a special budget.
   The worktree is clean after the task commit.
2. `dirty-final`: I want final review of my committed PR candidate. The same file
   also contains unrelated staged edits; another file has unrelated unstaged
   work, and a private scratch file is untracked. Ordinary capture includes them.
   A task-only clean worktree at the intended commit is available and verified.
   Preserve all original working files and the index.
3. `already-covered`: The exact intended commit/tree, base, full path scope and
   relevant policy already have a completed auto assessment. Inventory and
   coverage are complete, all required findings are settled, and tests passed.
   Nothing changed and no new evidence appeared. I am ready to hand over the work.
4. `trivial`: I corrected a typo in an internal comment. No behavior changed,
   no review is active and I did not request one. I am continuing the task.
5. `report-only`: I explicitly ask you to review my uncommitted code without
   editing or committing. The requested working scope is safe to collect, and
   there is no existing review. I do not ask you to prepare a PR.
6. `light-to-final`: A purposeful --fast checkpoint completed for the full
   intended snapshot. No code or evidence changed afterward. I now request
   ordinary final review before handoff. There is no completed auto final
   assessment and no exhausted user budget. Explain whether and how to proceed.
7. `explicit-fresh`: The current snapshot already has complete compatible auto
   coverage and settled findings. I explicitly request a fresh assessment with
   --full. Nothing changed, and the request is within my review budget.

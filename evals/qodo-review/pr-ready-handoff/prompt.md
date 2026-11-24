---
tags: [skill-creator]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

Use qodo-review. These are independent, synthetic PR requests. Explain your
next action and what you can tell the author. Do not call services or edit files.

1. “Open the PR. You can dismiss findings based on your judgment.” Tests passed.
   The completed local review covers the exact candidate and has complete inventory:
   no new findings, but F-GUARD and F-LOSS are still open from local review L1.
   All callers demonstrably enforce the guard in F-GUARD. F-LOSS is reproducible.
   Both are described in the PR body. No disposition has been written.
2. The exact pushed change passed its checks and complete local review with no
   open findings. A clean hosted result is available on the previous commit.
   The hosted review on the current head is running. “Is my PR Qodo-clean?”
   How does your answer change if the completed current-head hosted review
   subsequently returns one open finding? What evidence would justify “yes”?

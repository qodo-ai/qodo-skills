---
type: llm
focus: trace
weight: 1
---

For dirty-final, the response uses the verified clean task worktree for the committed candidate, preserves original files/index, and neither invokes unsupported committed-only flags nor treats ordinary dirty capture as equivalent coverage.

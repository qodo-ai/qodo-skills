---
type: llm
focus: trace
weight: 1
---

For stacked, use target-aware CLI discovery or the explicitly selected `--target parent`.
Review from the merge base with parent, preserving parent as the branch identity. Do not
substitute the parent tip, main, or a SHA-only `--base`. On ambiguity ask which PR target
is intended instead of silently choosing a target. Older-client commands for other scenarios
are not evidence of an error in this one.

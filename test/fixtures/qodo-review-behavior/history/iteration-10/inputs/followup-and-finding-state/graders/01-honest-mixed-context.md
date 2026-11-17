---
type: llm
focus: trace
weight: 1
---

For mixed-followup, recent_work includes both the timeout fix and new cancellation API, preserves decisions/notes context and the original finding identity, uses auto, and does not force --full merely because notes changed or a finding remains open.

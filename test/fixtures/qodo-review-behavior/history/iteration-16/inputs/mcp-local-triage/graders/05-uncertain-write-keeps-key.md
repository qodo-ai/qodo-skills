---
type: llm
focus: trace
weight: 1
---

For uncertain-write, the response collects the original operation or replays the exact original request with its retained key. It does not rotate the key, start another mutation, change the decision, or claim storage or synchronization without a terminal result and readback.

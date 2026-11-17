---
type: llm
focus: trace
weight: 1
---

For metadata-only, the proposed pr-review-dismiss call preserves F-A/F-B, L-ORIGINAL, the authorized reason/explanation and one retained metadata key through _meta["io.qodo/idempotency-key"]. It reads each synchronous result and verifies stored outcomes. Uncertain-response recovery uses the exact original request/key, without inventing an operation handle, polling call, schema argument, CLI fallback or successful write.

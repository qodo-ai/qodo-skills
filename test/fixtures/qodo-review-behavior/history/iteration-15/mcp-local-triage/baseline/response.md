**Proposals only—no calls, commands, or state changes have been made.**

### 1. `metadata-only`

F-A and F-B can share one authorized batch because they have the same original local-review ID, reason, and explanation.

Proposed MCP request, using an illustrative fresh replay key:

```json
{
  "method": "tools/call",
  "params": {
    "name": "pr-review-dismiss",
    "arguments": {
      "finding_ids": ["F-A", "F-B"],
      "local_review_id": "L-ORIGINAL",
      "reason": "false_positive",
      "explanation": "The mandatory caller guard rejects this input."
    },
    "_meta": {
      "io.qodo/idempotency-key": "triage-fa-fb-01"
    }
  }
}
```

The key belongs in request metadata, not in the tool’s arguments. Before submission, retain the exact request and key; retain the synchronous response afterward.

Inspect each finding’s result and read back its stored disposition. Confirm the actual stored reason and explanation, and report synchronization separately. An `already_dismissed` result does not establish that this requested decision was newly saved.

If the response is lost, replay the **exact request with the same key**. There is no pollable operation handle in this case; do not invent one or use a new key for uncertain-response recovery.

### 2. `no-replay-transport`

**The dismissal write is blocked.** Neither the schema nor host supports replay-key delivery, and no trusted CLI is available.

Do not submit an unprotected write or invent an `idempotency_key` argument. The next step is to obtain supported replay-safe transport. The evidence supports recommending both false-positive dismissals, but neither dismissal has been submitted or verified as stored.

### 3. `prior-outcomes`

- **F-A:** Readback confirms the prior dismissal remains: reason `deferred`, explanation **“Awaiting a separate migration.”** This is not a newly saved `false_positive` decision.
- **F-B:** The result is `conflict`; the requested dismissal did not succeed. No further disposition can be inferred.

Neither finding can be reported as newly dismissed with the requested reason. Do not overwrite the prior decision or treat the conflict as success. These outcomes also do not establish complete review coverage or a clean review. No additional assessment is justified solely by these supplied facts.

### 4. `saved-sync-pending`

**F-C’s requested dismissal was saved and verified.** Only downstream synchronization remains incomplete; `reconciled: false` does not negate the saved transition.

Because the original operation completed, replaying its original key would return the original result **without another synchronization attempt**. The user has separately authorized one new attempt, so propose a new invocation of `pr-review-dismiss` with:

- `finding_ids`: `["F-C"]`
- `local_review_id`: `"L-CURRENT"`
- `reason`: `"false_positive"`
- `explanation`: the exact explanation retained from the original authorized request
- `_meta["io.qodo/idempotency-key"]`: a **new, distinct stable key**, such as `triage-fc-sync-01`

Preserve the original request, key, and receipt. Retain the new synchronization request and key separately before submission. This is the same business decision, not permission to change its reason or explanation.

Inspect the new result and read back the stored disposition. Claim synchronization success only with confirming evidence. If it remains incomplete, report that and stop; no further new attempt is authorized. If this attempt’s response is lost, recover using its retained request and **its same new key**.

### 5. `uncertain-write`

**The write’s outcome is unknown.** There is neither a terminal result nor stored-state readback.

Collect the existing operation using its retained receipt. Alternatively, recover by replaying the **exact original request with its original key** through the trusted transport.

A new key is **not justified**: it would create a new handler invocation while the original outcome remains uncertain. Preserve the original finding ID, local-review ID, reason, explanation, request, key, and receipt. Do not claim that the dismissal succeeded, failed, or synchronized until the recovered result and stored-state verification establish what happened.

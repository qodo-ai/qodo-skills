Commands below are proposals only; nothing was executed.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then request its stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and continue polling **op-accepted**. Do not resubmit or attach the changed checkout/context. `--extended` changes output detail, not effort or execution.

**Safe claim:** The original request was accepted and remains pending. Its eventual result concerns the submitted snapshot, not automatically the current branch or edited context.

### 2. `uncertain` — recover the exact submission

Use the returned command unchanged:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, scope, context or effort options, or gather a replacement snapshot. Retain the recovery ID; once an operation ID is returned, collect that operation.

**Safe claim:** Acceptance is currently unknown. Recovery preserves the exact original request; it does not establish coverage of the changed checkout.

### 3. `storage-gap` — ready locally, handoff unfinished

**Ready locally:** The current intended snapshot has completed assessment, complete coverage and inventory, no required open findings, and passing tests.

But **not all local-to-Git work is finished**:

- Saving the reusable checkpoint failed; successful persistence and future reuse are not established.
- PR handoff remains unverified.

Next, reconcile the storage failure through supported recovery, if available, and verify PR-candidate base/snapshot/scope and finding handoff. Do not buy another assessment merely to repair a storage claim. Verify hosted review separately before claiming hosted Qodo-clean status.

### 4. `older-result` — full final coverage cannot be certified

**Review blocked for final certification.** The completed older result reports no findings, but coverage, inventory completeness and persistence are **unknown**, not successful.

Retrieve retained evidence for the same assessment if available. If those properties cannot be established, report the gap. A further authorized assessment can be justified by missing required final coverage—not by a desire for another zero-finding result.

**Safe claim:** “The older completed result reported no findings.” Nothing establishes full final coverage, complete inventory, successful persistence or reusable coverage.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry before confirmation that enrollment occurred. Do not switch accounts or deployments, strip context, lower effort, or log in again as a workaround.

**Safe claim:** Review is blocked by organization entitlement; no completed assessment is established.

### 6. `budget` — stop at the existing limit

**Budget reached: two of two new assessments used.** Five status polls and one extended retrieval are collection operations, not additional assessments. Resuming in a new session does not reset the budget.

Do not launch a third assessment. **F-BLOCK remains action-required**, so the work is not ready locally. Preserve it in the handoff; do not silently dismiss or waive it.

Further assessment requires an explicit budget extension. Existing-result collection does not consume another assessment, but cannot manufacture newer coverage or settle F-BLOCK.

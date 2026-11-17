Commands below are proposals only. `qodo` means the already-verified installed invocation.

### 1. `accepted` — collect the existing operation

Wait the server-requested **20 seconds**, then:
```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and poll that same operation. Do not submit another review.

`--extended` retrieves more stored detail; it does not deepen or rerun Qodo’s assessment. Verify the result’s operation and original snapshot association before interpreting it.

**Safe claim:** The original submission is still pending. Branch and context changes do not change what it reviewed, and its eventual result cannot automatically certify the current checkout.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Keep the retained original request. Do not append new base, scope, context or effort options, or gather a replacement snapshot. Once recovery returns an accepted operation ID, collect that operation.

**Safe claim:** Acceptance is currently unknown. Recovery concerns the original request—not the changed checkout. Neither successful acceptance nor completed assessment can yet be claimed.

### 3. `storage-gap` — ready locally, but not all finished

**Safe claim:** The current intended snapshot is **ready locally** on the supplied evidence: completed assessment, complete coverage and inventory, no required open findings, and passing tests.

However:
- Saving the reusable checkpoint failed.
- PR handoff remains unverified.

Therefore, **not all local-to-Git work is confirmed finished**. Retain the result and warning. Any persistence recovery must use a supported mechanism; none is supplied here. Verify handoff separately when authorized. Do not buy another assessment merely to repair storage, or claim reusable checkpoint storage or hosted Qodo-clean status.

### 4. `older-result` — final coverage cannot be certified

**Review blocked for final certification.** The older result reports no findings, but coverage, inventory completeness and persistence are **unknown**, not successful.

First seek missing evidence from the retained original result, if available. No operation handle is supplied, so I cannot name an executable collection command. If the evidence cannot be recovered, required final coverage remains unestablished; any new assessment must fit the applicable authorization and budget.

**Safe claim:** “The older result reported no findings.” Not “full final coverage,” “complete inventory,” “successfully stored,” or “ready locally.”

### 5. `entitlement` — stop

Error code: `closed_preview`

Message:
> Review access is not enabled for this organization.

Hint:
> Ask your administrator to enroll the organization.

Do not retry until you confirm enrollment occurred. Do not switch accounts or deployments, or treat another login as the remedy.

**Safe claim:** Review is blocked by organization enrollment; no successful assessment is established.

### 6. `budget` — stop further assessments

**Budget reached:** both permitted new assessments ran. The five status polls and one extended retrieval do **not** count as additional assessments. Resuming in another session does not reset the budget.

`F-BLOCK` remains action-required. Preserve it and any missing coverage in the handoff; do not silently dismiss it or start a third assessment.

**Safe claim:** “The assessment budget is exhausted, and required action remains.” Not “ready” or “clean.” Another assessment requires explicit additional budget and a concrete reason.

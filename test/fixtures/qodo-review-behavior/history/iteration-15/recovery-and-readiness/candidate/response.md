Proposed actions only; nothing has been executed.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then:

```sh
qodo review status op-accepted --extended --json
```

If still working, honor the next polling delay and keep collecting **the same operation**. Do not resubmit.

- `--extended` retrieves stored detail; it does not deepen or rerun the assessment.
- The result concerns the **original submitted snapshot and context**, not the changed branch or edited context.
- Pending is not completed. On completion, verify exposed operation/snapshot associations; report unavailable identity checks as unverified.

### 2. `uncertain` — recover the original submission

Use the returned command unchanged:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Use the retained original request. Do not append new scope, base, context or effort options, or gather the changed checkout.

Once an operation ID is returned, collect that operation. The recovery token is not an operation ID.

**Safe claim:** acceptance is currently unknown—not confirmed failure, completion or permission for a fresh submission.

### 3. `storage-gap` — ready locally, handoff not established

**No, all local-to-Git work cannot be declared finished.**

The supplied evidence supports **Ready locally**: the intended snapshot has complete assessment coverage and inventory, no required open findings, and passing tests.

Separately:
- Reusable checkpoint storage **failed**; successful persistence or future reuse cannot be claimed.
- PR handoff remains **unverified**.

Retain the result and warning, pursue only supported and authorized persistence recovery, and verify PR handoff separately. Do not buy another unchanged assessment merely to remove the storage warning.

### 4. `older-result` — stop the full-coverage certification

**Review blocked for the requested certification.**

The supported statement is: **“The older completed result reported no findings.”**

Coverage, inventory completeness and persistence are **unknown**, not successful. Zero findings does not establish final coverage or local readiness.

Retrieve supporting evidence if it remains available. If it cannot establish the required current coverage, that gap must be addressed before certification. Any necessary new assessment must respect authorization and budget; ordinary effort remains auto.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not start another review until enrollment is confirmed. Verified identity does not establish review entitlement. Do not retry by logging in again, changing accounts/deployments, stripping context or lowering effort.

**Safe claim:** review access is blocked; no completed assessment is established.

### 6. `budget` — no third assessment

**Budget reached: 2 of 2 new assessments used.** Resuming in another session does not reset it. The five status polls and one extended retrieval do not consume additional assessment slots.

**F-BLOCK remains action-required**, so the work is not ready despite the budget being exhausted.

Preserve the blocker, existing results and any coverage gaps. Do not start another assessment without explicit authorization extending the budget, and do not dismiss the blocker merely to finish.

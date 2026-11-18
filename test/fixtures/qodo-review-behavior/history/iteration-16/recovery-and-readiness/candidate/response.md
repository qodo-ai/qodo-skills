Commands below are proposals only; `qodo` means the verified installed invocation.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then:

```sh
qodo review status op-accepted --extended --json
```

If still working, honor the next returned delay and poll the same operation. Do not resubmit or replace its context.

**Safe claim:** The review is accepted, not yet completed. Extended output retrieves stored detail; it does not rerun or deepen the review. Its result concerns the original submission, not the changed checkout. Before interpreting it, verify returned operation/snapshot associations; disclose any unavailable identity check.

### 2. `uncertain` — recover the exact original submission

Use the returned command unchanged:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, scope, context or effort options, or gather another snapshot. Once recovery returns an operation ID, collect that operation and retain both identifiers.

**Safe claim:** Acceptance remains unknown until recovery establishes it. Neither completed review nor coverage of the changed checkout is established.

### 3. `storage-gap` — ready locally, but not end-to-end finished

**Safe claim:** The intended snapshot is **ready locally**: assessment, coverage, inventory, required findings and tests meet the stated conditions.

However, reusable-checkpoint saving failed, and PR handoff is unverified. Therefore, **not all local-to-Git work can be declared finished**.

Retain the result and warning. Establish supported persistence recovery and independently verify handoff before claiming those gates complete. No recovery command was supplied, so none should be invented. A fresh assessment is not automatically warranted by the storage warning.

### 4. `older-result` — certification blocked

**Safe claim:** The older completed assessment reported no findings.

Full coverage, inventory completeness and persistence are **unknown**, not proven successful or necessarily failed. Zero findings does not establish those properties.

Do not certify full final coverage. Certification requires verified evidence covering the intended snapshot; if unavailable, a further assessment would be needed. Missing metadata alone does not justify greater review effort.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Safe claim:** Review access is blocked. Verified CLI identity does not establish review entitlement.

Do not retry until enrollment is confirmed. Do not switch accounts or deployments, log in again, strip context or lower effort as a workaround.

### 6. `budget` — stop new assessments

The budget is exhausted: **2 of 2 new assessments** ran. Five status polls and one extended retrieval are collection operations, not additional assessments. Resuming in another session does not reset the budget.

**Safe claim:** **Budget reached; needs action.** Qodo’s `F-BLOCK` remains action-required. The attempt is not ready locally or clean.

Preserve the blocker and any missing coverage. Do not start a third assessment without an explicitly renewed budget; do not treat this request as authorization to edit or dismiss the finding.

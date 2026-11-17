Commands below are proposals only; nothing was executed.

### 1. `accepted` — collect, do not restart

Wait the requested **20 seconds**, then:
```sh
qodo review status op-accepted --extended --json
```
Continue collecting that same operation if still working. `--extended` retrieves stored detail; it does not deepen or rerun the review.

**Safe claim:** the review is pending for its original submitted snapshot and context—not the changed checkout. Verify returned operation and snapshot identities before interpreting the result.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
Do not append new base, scope, context or effort options. Recovery must use the retained original request, not the changed checkout. Once an operation ID is confirmed, collect that operation.

**Safe claim:** acceptance is currently unknown. Neither failure nor permission to submit a replacement has been established.

### 3. `storage-gap` — ready locally, handoff incomplete

**Safe claim:** the current intended snapshot is **ready locally**: assessment, coverage, inventory, required findings and tests satisfy the stated gates.

However:
- Saving the reusable checkpoint failed; reusable coverage cannot be claimed.
- PR finding handoff remains unverified.
- Therefore, **not all local-to-Git work is finished**.

Preserve the assessment and warning. Establish checkpoint persistence and verify handoff separately; another assessment is not justified merely to obtain a cleaner storage outcome.

### 4. `older-result` — certification blocked

**Safe claim:** the older completed result returned no findings.

Coverage, inventory completeness and persistence remain **unknown**, not implicitly successful. I cannot certify full final coverage. Obtain supporting retained evidence; if unavailable, required coverage remains blocked pending an authorized assessment that establishes it. Do not invent a recovery handle or assume `--extended` supplies missing metadata.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Safe claim:** review is blocked by enrollment. Do not retry, change accounts/deployments or lower effort. A new run requires confirmation that enrollment occurred.

### 6. `budget` — stop new assessments

**Budget reached; action remains required.** Both permitted assessments were used. Five status polls and one extended retrieval do not consume additional assessments, and resuming in another session does not reset the budget.

Qodo finding **F-BLOCK remains action-required**. Do not claim readiness or start a third assessment without explicit additional authorization. Preserve the blocker and existing evidence in the handoff.

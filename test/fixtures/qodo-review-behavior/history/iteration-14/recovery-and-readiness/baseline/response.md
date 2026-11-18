*Proposals only; nothing executed.*

### 1. `accepted` — collect the existing operation
Wait the requested **20 seconds**, then:
```sh
qodo review status op-accepted --extended --json
```
Keep polling that operation as instructed; do not resubmit. `--extended` retrieves stored detail without changing effort or rerunning review.

**Safe claim:** The review is still working on its original submitted snapshot and context. It does not establish coverage of the changed checkout or context.

### 2. `uncertain` — recover the original submission
Use the exact returned command:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
Do not append new base, scope, context or effort options. Preserve the recovery ID, then collect the returned operation ID.

**Safe claim:** Acceptance is currently unknown. This recovers the retained original request; it does not review the changed checkout.

### 3. `storage-gap` — ready locally, handoff unfinished
The supplied evidence supports **Ready locally**: the intended snapshot has complete assessment, coverage and inventory, settled required findings, and passing tests.

However, reusable-checkpoint saving failed, and PR handoff remains unverified. Preserve the result and warning; verify handoff separately. Do not buy another assessment merely to address the storage warning.

**Safe claim:** Local readiness is established. Successful checkpoint storage, reusable coverage and completion of all local-to-Git work are not established.

### 4. `older-result` — certification blocked
Retrieve any available retained metadata for the same result first. If that cannot establish final coverage and inventory completeness, a properly scoped assessment is needed within existing authorization and budget. Any new submission defaults to auto effort.

**Safe claim:** The older completed result reported no findings. Full final coverage, complete inventory and successful persistence remain unknown. It cannot certify the current final change.

### 5. `entitlement` — stop
`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry before confirmation that enrollment occurred. Do not switch accounts or deployments, or treat another login as enrollment.

**Safe claim:** Review is blocked by entitlement; no completed assessment is established.

### 6. `budget` — stop new assessments
**Budget reached.** Both permitted assessments have run. Five status polls and one extended retrieval consume no additional assessments, but resuming in another session does not reset the budget.

Preserve **F-BLOCK** as action-required. A third assessment requires explicit additional authorization.

**Safe claim:** The review budget is exhausted, and required action remains. The work is not ready locally.

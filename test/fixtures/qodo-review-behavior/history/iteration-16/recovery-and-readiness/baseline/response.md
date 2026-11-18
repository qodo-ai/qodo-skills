*Proposed operations only; nothing was executed. `qodo` denotes the verified installed invocation.*

### 1. `accepted` — collect the existing operation

Wait **20 seconds**, then request its result and stored detail:

```sh
qodo review status op-accepted --extended --json
```

Respect any subsequent polling delay. Do not resubmit or replace its original context.

**Safe claim:** The operation is still working. Its eventual result covers the originally submitted snapshot and context—not the changed checkout. `--extended` retrieves stored detail; it does not rerun or deepen the review.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, scope, context or effort options. Recovery must use the retained original request, not the changed checkout. If an operation ID is returned, retain both handles and collect that operation.

**Safe claim:** Acceptance is currently unknown. Neither failure nor completion has been established. Recovery is not a fresh assessment of current work.

### 3. `storage-gap` — ready locally, handoff unfinished

The supplied evidence supports **Ready locally**: the intended snapshot has complete assessment coverage and inventory, no required open findings, and passing tests.

However, **all local-to-Git work is not established as finished**:

- Saving the reusable checkpoint failed.
- PR handoff remains unverified.

Retain the completed result and warning. Address persistence through supported recovery, if available, and separately verify local-to-PR handoff. Do not buy another assessment merely to eliminate a storage warning.

**Safe claim:** “Ready locally; reusable checkpoint saving failed, and PR handoff is unverified.”

### 4. `older-result` — certification blocked

The older assessment completed and reported no findings. Coverage completeness, inventory completeness and persistence are **unknown**, not successful.

Recover authoritative supporting evidence if available. Additional stored detail cannot manufacture missing metadata. If the evidence remains unavailable, establish the required final coverage through an authorized assessment of the intended snapshot, subject to its budget. Ordinary effort remains **auto**.

**Safe claim:** “The older result reported no findings, but full final coverage cannot be certified.”

### 5. `entitlement` — stop

Returned code: `closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry before confirmation that enrollment occurred. Do not switch accounts or deployments, re-login, strip context or change effort to bypass the restriction.

**Safe claim:** Review is blocked by organization enrollment; no completed assessment is established.

### 6. `budget` — stop new assessments

The budget is exhausted: **2 of 2 new assessments used**. Five status polls and one extended collection do not consume additional assessments. Resuming in another session does not reset the budget.

Preserve **F-BLOCK** as action-required. Do not start a third assessment, dismiss the blocker or claim readiness. Further assessment requires explicit additional budget and a concrete review reason.

**Safe claim:** “Budget reached; F-BLOCK remains action-required. The finishing attempt is not ready.”

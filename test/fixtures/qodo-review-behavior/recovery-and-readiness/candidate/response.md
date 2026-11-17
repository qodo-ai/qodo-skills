Proposals only; no commands or writes executed.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then propose:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect its next polling delay. `--extended` retrieves stored detail; it does not deepen or rerun the assessment.

Preserve the original submitted base, snapshot, scope and context. Branch/context changes do not alter that request.

**Safe claim:** Accepted and pending—not completed, clean, or coverage of the changed checkout. Inspect the completed inventory, coverage, warnings and persistence evidence before stronger claims.

### 2. `uncertain` — recover the exact original request

Use precisely the returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append a new base, context, scope or effort, or recollect the changed checkout. Retain the recovery ID; once an operation ID is returned, collect that operation.

**Safe claim:** Acceptance is currently unknown. Neither recovery success nor assessment completion is established. Any recovered assessment concerns the original request, not the changed checkout.

### 3. `storage-gap` — ready locally, handoff unfinished

**Safe claim:** The current intended snapshot is **ready locally**: assessment, coverage, inventory, required findings and tests satisfy the supplied criteria.

But **not all local-to-Git work is finished**:

- Reusable-checkpoint persistence failed; do not claim saved or reusable coverage.
- PR/finding handoff remains unverified.
- Matching HEAD or published notes alone would not establish finding handoff.

Retain the result and warning. Investigate supported persistence reconciliation and verify handoff separately; do not buy an unchanged assessment merely to erase the storage warning. No supported repair command or handoff evidence was supplied.

### 4. `older-result` — certification blocked

**Safe claim:** The older result reports no findings.

Full final coverage, complete inventory and successful persistence are **unknown**, not established. Therefore, refuse full-coverage certification and report **Review blocked**.

Next, retrieve available stored detail using the original operation handle. That handle was not supplied, so no exact command can be proposed. Extended output cannot guarantee that missing metadata exists. If evidence remains unavailable, another appropriately scoped assessment is needed before certification—not an invented completeness claim.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

No enrollment occurred, so do not retry. A new run requires confirmation of enrollment. Do not switch accounts/deployments, log in again, strip context or lower effort to bypass entitlement.

**Safe claim:** Review access is blocked; no completed assessment is established.

### 6. `budget` — stop at the existing limit

**Budget reached:** two of two new assessments were used. Five status polls and one extended retrieval add **zero assessments**. Resuming in another coding session does not reset the budget.

`F-BLOCK` remains **action-required**. Preserve it visibly; do not dismiss it or claim readiness.

**Safe claim:** Budget reached, with required action outstanding—not ready or clean. No further assessment without explicit additional budget authorization.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then request Qodo’s retained detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and poll the same operation. Do not resubmit or attach the edited context. `--extended` retrieves more stored detail; it does not change effort or run another assessment.

**Safe claim:** The original submission was accepted and remains pending. Its eventual result concerns the submitted snapshot and context, not necessarily the current branch.

### 2. `uncertain` — recover the exact original submission

Use the returned command unchanged:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append a new base, scope, context, or effort option, and do not recollect the changed checkout. Once recovery returns an operation ID, collect that operation with `review status`. Preserve both identifiers.

**Safe claim:** Acceptance is currently unknown. Recovery preserves the original request; it does not assess the changed checkout.

### 3. `storage-gap` — ready locally, handoff unfinished

**Ready locally:** the current intended snapshot has complete assessment and inventory, no required open findings, and passing tests.

However, reusable checkpoint storage failed, and PR handoff remains unverified. Therefore, **not all local-to-Git work is established as finished**.

Next, reconcile storage through supported recovery and verify the intended snapshot, base, scope, and finding handoff before claiming PR completion. Do not rerun the assessment merely to chase successful storage, or push/open a PR without authorization.

**Safe claim:** Local readiness is established. Successful reusable-checkpoint storage and PR handoff are not.

### 4. `older-result` — final-coverage certification blocked

A completed result reporting no findings does not establish complete coverage, complete inventory, successful persistence, or applicability to the current snapshot.

Retrieve retained evidence if available. If those properties remain unverified, a properly scoped assessment of the current intended change is needed before certification. Any new submission keeps default auto effort; missing metadata does not justify deep mode.

**Safe claim:** The older result completed and reported no findings. Full final coverage, overall local readiness, persistence, and reuse remain unverified.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry before confirmation that enrollment occurred. Do not switch accounts or deployments, or attempt login as an entitlement workaround.

**Safe claim:** Review is blocked by organization entitlement; no completed assessment is established.

### 6. `budget` — stop new assessments

**Budget reached: 2 of 2 assessments used.** The five status polls and extended-result retrieval are not additional assessments. Resuming in another coding session does not reset the budget.

`F-BLOCK` remains action-required. Keep it visible and do not claim readiness. Another assessment requires explicit authorization to extend the budget.

**Safe claim:** The assessment budget is exhausted, and required work remains unresolved.

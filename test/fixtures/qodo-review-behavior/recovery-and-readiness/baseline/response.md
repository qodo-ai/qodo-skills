### 1. `accepted` — pending

Wait the requested **20 seconds**, then collect the same operation with stored detail:

```sh
qodo review status op-accepted --extended --json
```

If it remains working, respect the next returned polling delay. Do not resubmit or attach the changed context.

**Safe claim:** The original request is still being assessed. Its eventual result covers its submitted snapshot and context—not the subsequently changed branch or context. `--extended` retrieves detail; it does not deepen or rerun the review.

### 2. `uncertain` — recover original submission

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, context, scope or effort options. Preserve the retained original request. Once recovery returns an operation ID, collect that operation rather than submitting again.

**Safe claim:** Acceptance is currently unknown, not confirmed failed. Neither completion nor coverage of the changed checkout is established.

### 3. `storage-gap` — ready locally; handoff unfinished

The current intended snapshot is **ready locally**: assessment, coverage and inventory are complete, required findings are settled, and tests passed.

But **not all local-to-Git work is verified finished**:

- Saving the reusable checkpoint failed; successful persistence or future reuse cannot be claimed.
- PR handoff remains unverified.

Next, reconcile the actual Git/PR candidate, base and scope with the completed coverage and verify handoff separately. Do not buy another assessment merely to erase a storage warning. A hosted Qodo-clean claim also requires separate hosted-review verification.

### 4. `older-result` — full-coverage certification blocked

Stop short of certification. Coverage completeness, inventory completeness and persistence are **unknown**.

**Safe claim:** “The older completed result reports no findings.”

That is not evidence of full final coverage, successful storage, reusable coverage or local readiness. Retained detail may be collected if a valid handle exists, but `--extended` cannot establish properties absent from the available evidence. Any further assessment needs a concrete missing-coverage reason and applicable authorization and budget.

### 5. `entitlement` — review blocked

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Stop. Do not retry before enrollment is confirmed, or switch accounts/deployments, log in again, strip context or lower effort to bypass the restriction.

**Safe claim:** Review access is blocked by enrollment. Verified identity does not establish review entitlement; no successful assessment is established here.

### 6. `budget` — budget reached; blocker remains

**Stop submitting new assessments.** Both permitted assessments have run. Five status polls and one extended retrieval are collection operations, not additional assessments. Resuming in another session does not reset the budget.

Qodo’s **F-BLOCK remains action-required**, so the work is not ready. Preserve it and any missing coverage in the handoff. Further assessment requires an explicitly expanded budget **and** a concrete reason; do not purchase unchanged reviews to chase zero findings.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then request its result and stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and poll the same operation. Do not resubmit or attach the changed checkout/context. `--extended` retrieves detail; it does not increase effort or rerun Qodo’s review.

**Safe claim:** The operation was accepted and remains pending. Its eventual assessment concerns the original submitted snapshot and context, not the changed checkout. Verify the returned operation/snapshot association, coverage and inventory before interpreting it.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Use the retained original request. Do not append a new base, scope, context or effort, and do not gather the changed checkout. If recovery returns an operation ID, collect that operation.

**Safe claim:** Acceptance is currently unknown—not confirmed failure or completion. Do not launch an independent replacement submission.

### 3. `storage-gap` — ready locally, handoff unfinished

**Ready locally:** The current intended snapshot has completed assessment, complete coverage and inventory, no required open findings, and passing tests.

However:

- Saving the reusable checkpoint failed. Do not claim successful checkpoint persistence or guaranteed reuse.
- PR handoff remains unverified. Local readiness does not establish finding handoff or hosted review status.

**Next:** Address/report checkpoint persistence separately and verify the intended PR candidate, base, scope and finding handoff when authorized. Do not rerun the assessment solely to remove a storage warning.

**Safe answer:** Local readiness is established, but **all local-to-Git work is not verified finished**.

### 4. `older-result` — certification blocked by missing evidence

Stop short of certifying full final coverage.

**Safe claim:** The older assessment completed and reported no findings. Coverage completeness, inventory completeness and persistence are **unknown**, not confirmed successful or failed.

Retrieve retained supporting evidence, including an extended view if available, using the actual operation handle. Do not invent one or assume extended output supplies missing metadata. If evidence remains unavailable, missing required final coverage can justify another assessment within authorization and budget; it does not justify increasing effort automatically.

### 5. `entitlement` — stop

`closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Next:** Stop. A new run requires confirmation that enrollment occurred. Do not retry now, log in again, or switch accounts/deployments.

**Safe claim:** Review is blocked by organization enrollment; verified identity does not establish review entitlement.

### 6. `budget` — stop further assessments

**Budget reached: 2 of 2 new assessments used.** The five status polls and one extended retrieval consume no additional assessments, but resuming in another session does not reset the budget.

`F-BLOCK` remains action-required. Do not dismiss it, claim readiness, or start a third assessment under the existing authorization.

**Next:** Preserve the blocker and review history. Another assessment requires an explicit budget extension and a concrete review reason; the session restart supplies neither.

Commands below are **proposals only**; nothing was executed.

### 1. `accepted` — collect the existing operation

After the requested **20-second delay**:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next polling delay and keep using `op-accepted`. `--extended` retrieves stored detail; it does not rerun or deepen the review.

Verify returned identities and snapshot metadata against the original submission; disclose unavailable checks. Branch/context changes do not modify that submission.

**Safe claim:** Qodo accepted the review and it remains pending. It does not yet establish completion, readiness, or coverage of your changed checkout.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, scope, context or effort options, or collect a replacement snapshot. Recovery must use the retained original request despite checkout changes. If it returns an operation ID, collect that operation.

**Safe claim:** Acceptance is currently unknown. Neither successful admission nor completed review is established.

### 3. `storage-gap` — ready locally, not finished end to end

**Safe claim:** The current intended snapshot is **ready locally**: assessment, coverage and inventory are complete, required findings are settled, and tests passed.

But **no**, all local-to-Git work cannot be called finished:

- Saving the reusable checkpoint failed; successful persistence and reusable coverage are not established.
- PR handoff remains unverified; local readiness does not establish hosted review or handoff success.

Use only a supported persistence-recovery mechanism if one is provided. Otherwise report the gap. Do not rerun an already sufficient assessment merely to chase storage success, or invent a recovery command.

### 4. `older-result` — certification blocked

**Safe claim:** “The older completed result reported no findings.”

Missing coverage, inventory-completeness and persistence metadata remain **unknown**. Zero findings does not prove full final coverage, successful storage or reusable coverage.

Do not certify. Establish missing final coverage through an authorized assessment if continuing; this is a concrete reason for another assessment, not for increased effort. Do not assume `--extended` can manufacture absent evidence.

### 5. `entitlement` — stop

`closed_preview`:

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Safe claim:** Review is blocked by enrollment. Do not submit again until enrollment is confirmed. Do not switch accounts/deployments, repeat login, strip context or lower effort to bypass it.

### 6. `budget` — stop new assessments

Your explicit **two-assessment budget is exhausted**. Five status polls and one extended retrieval are not additional assessments; resuming in another session does not reset the budget.

**Safe claim:** **Budget reached; needs action.** `F-BLOCK` remains action-required, so readiness is not established.

Do not launch a third assessment or dismiss the blocker. Preserve the outstanding finding and obtain explicit budget extension before another assessment; any fixes still require covering edit authority.

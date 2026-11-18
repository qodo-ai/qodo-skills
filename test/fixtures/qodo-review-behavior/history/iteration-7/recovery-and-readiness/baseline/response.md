Proposals only; nothing executed. `qodo` below means the verified installed invocation.

### 1. `accepted`
After the requested **20-second delay**, collect the existing operation with stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect its next polling delay and keep the same ID. Do not resubmit or substitute the changed checkout/context. `--extended` retrieves detail; it does not rerun or deepen review.

**Safe claim:** Accepted and pending. Any eventual assessment covers the original submitted snapshot, not automatically the current branch.

### 2. `uncertain`
Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Preserve the retained original request, snapshot, context and effort. Append no new review-input options. Once an operation ID is returned, collect that operation.

**Safe claim:** Acceptance is currently unknown—not confirmed failure or completion. Do not gather a fresh snapshot.

### 3. `storage-gap`
**Ready locally, but not all local-to-Git work is established as finished.**

The supplied evidence supports local readiness: completed assessment, complete coverage/inventory, settled required findings and passing tests. Separately:

- Reusable-checkpoint saving failed; do not claim successful storage or guaranteed reuse.
- PR handoff remains unverified; do not claim findings transferred or hosted review is clean.
- Retain the result and warning, then verify the intended candidate/base/scope and any authorized handoff obligations.

Do not buy another assessment merely to erase the storage warning.

### 4. `older-result`
**Stop certification: review blocked by missing evidence.**

Safe claim: “The older assessment completed and reported no findings.”

Coverage, inventory completeness and persistence are **unknown**, not implicitly successful. This cannot certify full final coverage or current-snapshot readiness. Missing required coverage can justify a further authorized assessment; it does not justify increased effort by itself.

### 5. `entitlement`
**Stop: `closed_preview`.** Preserve the returned text unchanged:

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry, poll for activation, log in again or switch accounts/deployments. Do not submit again unless the user confirms enrollment.

**Safe claim:** Review is blocked by entitlement; verified identity does not establish review access.

### 6. `budget`
**Budget reached; do not start a third assessment.**

Both permitted assessments were consumed. The five status polls and one extended retrieval do **not** count as assessments. Resuming in another coding session does not reset the budget.

Preserve **F-BLOCK as action-required**. No newer assessment or authorization settles it.

**Safe claim:** Budget exhausted and action remains; not ready locally. Further assessments require explicit budget authorization.

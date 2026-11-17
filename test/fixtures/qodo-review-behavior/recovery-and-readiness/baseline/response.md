Commands below are proposals only; nothing was executed.

### 1. `accepted`

After the server’s **20-second delay**, collect the existing Qodo operation with stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and poll the same operation. Do not resubmit because the branch or context changed. `--extended` retrieves detail; it does not deepen or rerun the review.

**Safe claim:** The review is accepted and pending. Its eventual result covers the originally submitted snapshot and context, not the changed checkout.

### 2. `uncertain`

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Replay the retained original request. Do not append current scope, context, base or effort options, or collect a new snapshot. If recovery returns an operation ID, collect that operation.

**Safe claim:** Acceptance is currently unknown—not confirmed failure or completion. The recovery identifier is not an operation ID.

### 3. `storage-gap`

**Ready locally, but end-to-end completion is not established.** The current snapshot has complete assessment and inventory, no required open findings, and passing tests.

Report the checkpoint-save failure and verify PR handoff separately. Do not start another assessment merely to chase successful storage.

**Safe claim:** Local readiness is established. Reusable checkpoint persistence failed, and PR handoff remains unverified. You cannot yet claim all local-to-Git work is finished.

### 4. `older-result`

**Review blocked for full-final-coverage certification.** Seek retained evidence for coverage, inventory completeness and persistence. If unavailable, keep those properties unknown; the empty findings list does not establish them.

**Safe claim:** “The older completed result reported no findings.” You cannot certify full final coverage, complete inventory, successful persistence or current-snapshot readiness.

### 5. `entitlement`

Stop on `closed_preview`. Preserve the returned message and hint:

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

Do not retry until enrollment is confirmed. Do not switch accounts/deployments, re-login or change effort to bypass the restriction.

**Safe claim:** Review is blocked by organization entitlement; no successful assessment is established.

### 6. `budget`

**Budget reached—do not start a third assessment.** Both permitted assessments were used. The five status polls and one extended retrieval do not count as additional assessments, and resuming in another session does not reset the budget.

`F-BLOCK` remains action-required. Additional assessment requires an explicit budget extension.

**Safe claim:** The review budget is exhausted and the work still needs action. It is not ready or clean.

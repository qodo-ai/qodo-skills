Commands below are proposals only; nothing was executed.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then:
```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned delay and keep polling **op-accepted**. Do not resubmit.

`--extended` retrieves stored detail; it does not rerun or deepen the assessment. Branch and context changes do not change the submitted request. Any completed result covers its original snapshot and context—not automatically your current checkout. Until completion, you can claim only that the operation was accepted and remains pending.

### 2. `uncertain` — recover the exact retained request

Use the returned command unchanged:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append a new base, context file, scope or effort, and do not collect the changed checkout. Once recovery supplies an operation ID, collect that operation with `review status`; use `--extended --json` for stored detail.

Acceptance is currently **unknown**. This is admission recovery, not permission to submit a fresh assessment of current work.

### 3. `storage-gap` — ready locally; handoff is not established

The supplied evidence supports **Ready locally**: the current intended snapshot has complete assessment, coverage and inventory, no required open findings, and passing tests.

It does **not** support “all local-to-Git work is finished”:
- Saving the reusable checkpoint failed.
- PR handoff remains unverified.
- No evidence establishes completed commit, push or hosted-review obligations.

Retain the completed result and storage warning. Reconcile persistence through supported mechanisms and verify Git/PR handoff separately, within authorization. Do not rerun the assessment merely to obtain a cleaner-looking storage outcome.

### 4. `older-result` — stop final-coverage certification

You can say: **“The older completed result reported no findings.”**

You cannot certify full final coverage, inventory completeness, successful persistence or reusable coverage. Those properties are **unknown**, not established by an empty findings list.

Retrieve any available evidence from the existing operation, but `--extended` cannot create evidence that was never stored. Without supporting evidence or an appropriately authorized assessment establishing required coverage, final-review certification remains **blocked**.

### 5. `entitlement` — stop

Code: `closed_preview`

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

No review entitlement is established. Do not retry, log in again, switch accounts/deployments or change effort to bypass this gate. A new run requires confirmation that enrollment occurred.

### 6. `budget` — stop new assessments

**Budget reached: 2 of 2 assessments used.** The five status polls and one extended retrieval are collection operations, not additional assessments. Resuming in another session does not reset the budget.

Qodo’s **F-BLOCK remains action-required**. Do not start a third assessment without an explicit budget extension. Existing-result collection may continue within retention, but it cannot settle the blocker by itself.

Safe claim: **“The assessment budget is exhausted; F-BLOCK remains unresolved, so the work is not ready locally.”**

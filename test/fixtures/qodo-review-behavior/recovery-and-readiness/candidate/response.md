Commands below are proposals only; none were executed.

### 1. `accepted` — collect the existing operation

Wait the requested **20 seconds**, then retrieve its status and stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, honor the next returned delay and poll the same operation. Do not resubmit or attach the changed context.

**Safe claim:** The original submission is accepted and pending. Its eventual result covers its original snapshot and context—not the changed checkout. `--extended` retrieves more stored detail; it does not rerun or deepen the assessment. Inspect the completed inventory, coverage, warnings and reviewer comment before making further claims.

### 2. `uncertain` — recover the original submission

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append a new base, context file, path restriction or effort flag. Recovery must preserve the retained original request despite checkout changes. If it returns an operation ID, collect that operation.

**Safe claim:** Acceptance is currently unknown. This is recovery of the original request, not authorization for a fresh assessment of the changed checkout.

### 3. `storage-gap` — ready locally, handoff unfinished

**Ready locally:** The current intended snapshot has completed assessment, complete coverage and inventory, no required open findings, and passing tests.

But **not all local-to-Git work is finished**:

- Saving the reusable checkpoint failed; reusable coverage is not established.
- PR handoff remains unverified.
- Local readiness does not establish hosted review status, CI or merge readiness.

Preserve the persistence warning and verify the handoff separately. Do not buy another unchanged assessment merely to repair the appearance of successful storage.

### 4. `older-result` — full final coverage cannot be certified

**Review blocked for final certification.** The older assessment completed and reported no findings, but coverage, inventory completeness and persistence are **unknown**, not proven complete or proven failed.

Next, seek the missing evidence from the original stored result; an extended retrieval is appropriate if its actual operation ID is available. Do not invent a handle or assume extended output will supply absent metadata.

If the evidence remains unavailable, required final coverage needs a new assessment within the applicable authorization and budget. No new effort was requested, so do not escalate to deep.

**Safe claim:** “The older completed result reported no findings; full final coverage and reusable persistence are unverified.”

### 5. `entitlement` — stop

**Review blocked — `closed_preview`.**

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

No new review run until enrollment is confirmed. Do not retry automatically, relogin, switch accounts or deployments, strip context, or lower effort to bypass the restriction.

**Safe claim:** Review access is blocked; no successful assessment is established by this error.

### 6. `budget` — stop the assessment loop

**Budget reached.** Both permitted new assessments ran. The five status polls and one extended retrieval do **not** consume additional assessments. Resuming in a new coding session does not reset the budget.

`F-BLOCK` remains **action-required**. Preserve it visibly; do not dismiss it, suppress it or claim readiness.

**Safe claim:** “The two-assessment budget is exhausted, and F-BLOCK remains unresolved.”

Another assessment requires an explicit budget extension and a concrete review reason. Nothing here authorizes edits or finding-status writes.

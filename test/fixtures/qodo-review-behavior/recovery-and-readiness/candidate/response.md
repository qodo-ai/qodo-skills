Proposed actions only; no commands executed. Below, `qodo` means the verified installed invocation.

### 1. `accepted`

Wait the requested **20 seconds**, preferably using a nonblocking wait, then collect the same operation with stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned polling delay and keep collecting **op-accepted**. Do not restart it or submit another review for more detail. `--extended` changes the result view, not review effort.

The accepted run retains its original snapshot and context; branch changes and context edits do not update it. Preserve its original base, scope, snapshot identity and context association. On completion, inspect warnings, coverage, the full finding inventory and `review_agent_comment`.

**Safe claim:** The operation was accepted and remains pending. Its eventual assessment covers the submitted inputs—not automatically the current checkout or edited context.

### 2. `uncertain`

Use exactly the returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

Do not append new base, path, context or effort options. The retained original request must survive unchanged despite checkout and context changes.

Once recovery returns an operation ID, retain both IDs and collect that operation through `review status`. If admission remains uncertain or recovery fails, preserve the recovery handle and report the gap rather than issuing a fresh submission.

**Safe claim:** Acceptance is currently unknown. This recovers the original submission; it is not an assessment of the changed checkout.

### 3. `storage-gap`

**Ready locally, but not all local-to-Git work is finished.**

The fixture establishes completed assessment of the intended snapshot, complete coverage and inventory, settled required findings, and passing tests. Checkpoint persistence is a separate outcome.

Next actions:

- Preserve the result and its checkpoint-save warning.
- Report that reusable checkpoint storage failed.
- Before PR handoff, reconcile the actual candidate’s code, base and scope with the completed assessment and verify finding handoff.
- Verify hosted review separately before claiming hosted Qodo-clean status.

Do not buy another assessment solely to remove the persistence warning. Do not infer permission to push, publish notes or open a PR.

**Safe claim:** Local readiness is established. Successful reusable-checkpoint storage and local-to-PR handoff are not established.

### 4. `older-result`

**Stop short of certifying full final coverage.**

The older result reports no findings, but coverage completeness, inventory completeness and persistence are all **unknown**. Missing metadata is not affirmative evidence.

If a retained operation handle exists, retrieve its extended result and inspect any additional evidence. Do not invent a handle or assume extended output restores missing metadata.

If the evidence remains unavailable, report **Review blocked** for required final coverage. A current assessment to establish missing coverage is a concrete reason for another submission, subject to authorization and budget. Keep ordinary auto effort; missing metadata does not justify `--deep`. Use `--full` only if supported and appropriate for establishing a fresh assessment.

**Safe claim:** The older assessment returned no findings. Full final coverage, a complete inventory and successful persistence cannot be certified.

### 5. `entitlement`

Show the returned message and hint unchanged:

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Stop: Review blocked by `closed_preview`.** Do not retry, watch for activation, log in again, switch accounts/deployments, strip context or lower effort. Do not submit again unless the user confirms enrollment.

**Safe claim:** The organization lacks review entitlement; no completed assessment is established. Verified identity does not establish review access.

### 6. `budget`

**Budget reached. Do not start a third assessment.**

Both permitted new assessments ran. The five status polls and one extended retrieval are collection operations, not additional assessments. Resuming in another coding session does not reset the finishing-attempt budget.

Preserve F-BLOCK’s action-required status and report it as an outstanding obligation. Do not dismiss it, mark it resolved or claim readiness without supporting evidence and authority.

Existing-result collection may continue when needed; another assessment requires explicit authorization extending the budget.

**Safe claim:** The assessment budget is exhausted, and F-BLOCK still requires action. The work is not ready for a completed-work handoff.

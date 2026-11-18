Proposed actions only; no commands executed.

### 1. `accepted`

Wait the requested **20 seconds**, then collect the existing operation with stored detail:

```sh
qodo review status op-accepted --extended --json
```

If still working, respect the next returned polling delay and keep the same operation ID. Collect within its retention window.

**Safe claims:** The review was accepted and remains pending. `--extended` retrieves detail; it does not rerun or deepen review. Any completed result covers the **original submitted snapshot and context**, not the changed checkout or edited context. Preserve its original base, tree, scope and context association. Do not submit again merely to obtain its result.

### 2. `uncertain`

Use the exact returned recovery command:

```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```

This must use the retained original request. Do not collect the changed checkout, substitute edited context, or append new review-input options.

If recovery returns an operation ID, retain **both** IDs and collect that operation:

```sh
qodo review status <returned-operation-id> --extended --json
```

Respect returned polling delays.

**Safe claims:** Acceptance is currently uncertain—not confirmed failure or completion. Recovery preserves the original submission; it does not establish coverage of newer work. Do not promise that an independent fresh submission would be free or deduplicated. If recovery cannot resolve admission, preserve the recovery handle and report the evidence gap rather than automatically submitting anew.

### 3. `storage-gap`

**Ready locally, but not all local-to-Git work is finished.**

The supplied evidence establishes:
- Completed assessment of the current intended snapshot.
- Complete coverage and finding inventory.
- No required open findings.
- Passing relevant tests.

Separately, **reusable checkpoint storage failed**, and **PR handoff remains unverified**. Preserve the result and warning. Do not claim reusable checkpoint availability or infer finding-storage outcomes from the checkpoint warning alone.

No additional assessment is justified solely to obtain successful checkpoint storage. Before a PR/update, compare the intended snapshot, base and scope against completed coverage and reconcile outstanding results. Perform notes or PR maintenance only with covering authority. Matching HEAD or published notes alone does not prove finding handoff; verify hosted review separately before claiming hosted Qodo-clean status.

### 4. `older-result`

**Review blocked for full-final-coverage certification.**

The defensible statement is: **“The completed older result reported no findings.”**

It does not establish:
- Complete assessed coverage.
- Complete finding inventory.
- Successful persistence or reusable checkpoint availability.

Missing metadata is unknown, not success. Do not call this fully covered or clean.

If final coverage must now be established, the missing evidence is a concrete reason for another assessment. After confirming the current intended scope, comparison base and complete session context, propose an ordinary auto submission:

```sh
qodo review --base <verified-comparison-base-sha> \
  --context-file <current-context-file> --async --json
```

Include every intended path; omit `--fast` and `--deep`. Do not invent support for `--full`, which this fixture has not confirmed. Assess the returned coverage rather than assuming the new submission repairs the gap.

### 5. `entitlement`

Show the returned message and hint unchanged:

> Review access is not enabled for this organization.

> Ask your administrator to enroll the organization.

**Stop.** `closed_preview` is an entitlement blocker, not a transient failure. Do not retry, watch for completion, log in again, switch accounts/deployments, or lower effort. Another submission requires confirmation of enrollment.

**Safe claim:** Required review is blocked by organization access; there is no completed assessment established here.

### 6. `budget`

**Stop new assessments: budget reached.**

Both permitted assessments ran. Five status polls and one extended-result retrieval are collection operations, not additional assessments. Resuming in another coding session does **not** reset the budget.

Report **F-BLOCK** with its original reference and action-required status. Local readiness remains unmet; do not suppress, dismiss or mark it resolved without evidence and authority. Existing results may still be collected without starting another assessment.

**Safe claims:** The two-assessment budget is exhausted, and an action-required blocker remains. A third assessment requires renewed explicit budget authorization; the current session provides none.

For any completed result collected above, inspect warnings, `review_agent_comment`, coverage and inventory completeness, and both introduced and still-open findings. Report resolved/dismissed findings separately. Do not invent execution, model or timing metadata.

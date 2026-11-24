I followed the qodo-review workflow. Nothing was run because these inputs are synthetic.

## 1. `accepted`: op-accepted still running

**Next step:** Wait the 20 seconds the server asked for, then check the same operation:
```sh
qodo review status op-accepted --json
```
If it's still working (exit 2), keep waiting for its `retry_after` and check again. Once it finishes (exit 0), get the extra stored detail with:
```sh
qodo review status op-accepted --extended --json
```
`--extended` only shows more of the stored result. It doesn't run or rerun a review. Don't submit a new review just to check progress or get more detail.

**What you can safely say:**
- The review was accepted but isn't finished. No assessment exists yet.
- When it finishes, it covers the branch and context as they were at submission. It doesn't cover your current branch or your later context edits. Each finding has to be rechecked against the current code, and the result can't certify the newer work.
- Check that the returned operation and snapshot identities match. If the CLI doesn't show the operation ID, say that check wasn't available rather than that it passed.

## 2. `uncertain`: acceptance reply was lost

**Next step:** Run exactly the recovery command the CLI returned:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
Don't add options, refresh the context or collect your changed checkout. Keep the recovery ID. If the command returns an operation ID, keep that too and check it with `qodo review status <id> --json`.

**What you can safely say:**
- It's unknown whether the review was accepted, and there's no operation yet.
- Any result from this recovery covers the original request only, not your current checkout or context. Reviewing the current state would be a separate new submission, which you haven't asked for.

## 3. `storage-gap`: assessment done, checkpoint save failed

**Next step:** Stop reviewing. Nothing changed, so another assessment would just repeat the same one. The remaining gaps aren't review steps.

**Answer: no, not all local-to-Git work is verified as finished.**
- **Ready locally (you can say this):** the current snapshot has a completed assessment with complete coverage and inventory, no required open findings, and passing tests.
- **Checkpoint storage failed:** don't say reusable coverage was stored. A later review may not be able to build on this one.
- **PR handoff not verified:** don't say the change has been handed off, or that the hosted Qodo review is clean. That needs its own check through `qodo-review-resolver`. CI, merge and deployment are separate gates again.

## 4. `older-result`: you asked me to certify full final coverage

**I can't certify it.** The result has no coverage, inventory-completeness or storage metadata, and there's no other evidence. Missing metadata means unknown, not complete. An older result also can't certify newer work.

**Stopping reason:** Review blocked, because final coverage is unknown. If you want certification, it needs a new assessment of the current intended snapshot. Use the default effort (no `--fast` or `--deep`) and the same base and scope, and the review engine will report whether it did a full, incremental or reused review. You haven't asked for new review effort, so I'd only submit if you approve.

**What you can safely say:** an older completed review reported no findings. Its coverage, completeness and storage are unknown, and it doesn't certify the current code.

## 5. `entitlement`: `closed_preview`

**Stop.** The error, unchanged:
- **Message:** Review access is not enabled for this organization.
- **Hint:** Ask your administrator to enroll the organization.

Don't retry, switch accounts or deployments, or lower effort. A new run needs your confirmation that the organization has been enrolled.

**What you can safely say:** no review ran, so the change has no assessment.

## 6. `budget`: two of two assessments used

**Don't continue. The budget is reached.** Your limit of two new assessments carries over to the new session, and both have run. The five status checks and the one extended view don't count against it, but there's nothing left.

**Status:** Needs action. F-BLOCK is still action-required, and there's no newer assessment or authorization.

**What you can safely say:** the change is not ready locally, and F-BLOCK is unresolved. To go further, you'd need to do one of these:
- Raise the budget.
- Authorize a fix for F-BLOCK, then decide whether to review that fix.
- Make a recorded decision on F-BLOCK, such as an authorized dismissal with evidence.
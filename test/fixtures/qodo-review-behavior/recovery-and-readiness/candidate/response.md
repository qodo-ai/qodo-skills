I applied the qodo-review workflow to each synthetic case. I didn't run any commands, call any service or change any files. The commands below are what I would run next.

## 1. `accepted`: still running

**Next step:** Wait the 20 seconds the server asked for, then check the same operation:
```sh
qodo review status op-accepted --json
```
- If it says it's still working, wait for its new `retry_after` delay and check again.
- Once it completes, get more stored detail with `qodo review status op-accepted --extended --json`. This only shows more of the saved result. It doesn't start a new review or cost more review effort.
- Don't submit a new review to check progress or to get more detail.

**Claims you can safely make:**
- Operation `op-accepted` was accepted and is still in progress. There is no assessment or findings yet.
- When it finishes, the result covers the snapshot and context you sent at submission. It doesn't cover your current branch or edited context.
- If you want your current work reviewed, that's a separate submission later with refreshed context. It doesn't replace collecting this result.

## 2. `uncertain`: no confirmation the submission was accepted

**Next step:** Run the recovery command the CLI returned, exactly as given:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
- Don't add options, don't collect your changed checkout and don't send the new context.
- If it returns an operation ID, save it alongside the recovery ID and check it with `review status`.

**Claims you can safely make:**
- We don't know whether the submission was accepted, and there's no operation ID yet.
- The recovery uses the original saved request. Any result covers the original snapshot, not your current checkout or context.
- There are no findings to report.

## 3. `storage-gap`: not everything is finished

**Answer:** No. The local review is complete, but not all of the work from local code to Git is done.

**Next step:** Stop reviewing. A failed checkpoint save is not a reason for another review. Next, check the PR handoff: compare the code, base and scope you intend to ship against this completed coverage. Pushing or opening a PR needs your separate approval.

**Claims you can safely make:**
- **Ready locally:** the current intended snapshot has a completed assessment with complete coverage and inventory, no required open findings, and passing tests.
- The reusable checkpoint was **not** saved, so you can't claim saved or reusable coverage. A later follow-up may not be able to build on this run.
- The PR handoff is unverified. CI, merge and deploy are separate gates.

## 4. `older-result`: I can't certify full final coverage

**Stopping reason:** Coverage, inventory completeness and persistence are all **unknown**. Missing metadata doesn't prove completion, and an older result can't certify newer work.

**Next step:** Stop. Certifying would need a new assessment of the current intended snapshot (default effort, with `--full` because the previous coverage is unverified). You didn't ask for new review effort, so that needs your approval first.

**Claims you can safely make:**
- An older review completed and reported no findings for the snapshot it reviewed.
- Nothing more: not full coverage, not a complete inventory, not saved results, and not that it applies to the current code. Zero findings alone doesn't make the code clean.

## 5. `entitlement`: review access isn't enabled

**Stopping reason:** The error is `closed_preview`:
> Review access is not enabled for this organization.
> Hint: Ask your administrator to enroll the organization.

**Next step:** Stop. Don't retry, switch accounts or change deployment. A new run needs your confirmation that the organization has been enrolled.

**Claims you can safely make:**
- The review is blocked by organization access, so no assessment happened.
- This tells you nothing about the code's quality.

## 6. `budget`: stop here

**Answer:** Don't continue reviewing.

**Stopping reason:** You set a budget of two new assessments and both have run. The budget still applies after resuming in a new session. The five status checks and the extended view don't count against it, but they also aren't new evidence.

**Next step:** Stop with the open finding. Another assessment needs you to raise the budget. Fixing F-BLOCK needs your approval to make edits, and you haven't given it.

**Claims you can safely make:**
- **Budget reached / Needs action:** F-BLOCK is still marked action-required, and there's no newer assessment or approval that settles it.
- The work isn't ready locally or ready for a PR.

**Your options:** approve a fix for F-BLOCK (then I'd test it and spend one more review only if you raise the budget), or ship knowing F-BLOCK is unresolved.
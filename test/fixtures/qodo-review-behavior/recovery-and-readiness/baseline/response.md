I used the qodo-review skill to work through these six cases. Nothing was run: no live calls, no submissions and no file changes. `qodo` below stands for the installed command you already verified.

---

### 1. `accepted`: op-accepted is still running

**Next step:** Wait the 20 seconds the server asked for. Then check the same operation:
```sh
qodo review status op-accepted --json
```
- Exit `2` (still working): wait for the returned `retry_after` (15 s if none is given), then check again.
- Exit `0` (done): get the extra stored detail with:
  ```sh
  qodo review status op-accepted --extended --json
  ```
  `--extended` only shows more of the stored result. It doesn't start a new review or add effort.

Don't submit again to check progress or to get more detail.

**Safe claims:**
- The review was accepted and is not finished yet. Accepted doesn't mean assessed.
- When it finishes, the result covers the branch, code and context as they were at submission. It doesn't cover your current branch or your edited context.
- Findings from it need rechecking against the current code. It can't vouch for the newer work.

### 2. `uncertain`: the acceptance reply was lost

**Next step:** Run the exact recovery command the CLI returned, with no added options:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
It resends the saved original request. Don't collect a new snapshot of your changed checkout or swap in the new context. Keep the recovery ID. If the request is accepted, save the operation ID it returns and check it as in case 1.

**Safe claims:**
- It's unknown whether the first submission was accepted. There is no operation ID yet.
- The recovered request covers the original snapshot and context, not the current checkout.
- No result exists yet, so nothing is assessed.

### 3. `storage-gap`: done, but the checkpoint failed to save

**Next step:** Stop and report. A failed save isn't a reason to run another review.

**Answer:** No, not all local-to-Git work is finished. The local review is done. Saving the checkpoint and the PR handoff are not.

**Safe claims:**
- **Ready locally:** the current intended snapshot has a completed assessment with complete coverage and inventory. No required findings are open, and tests passed.
- Saving the reusable checkpoint **failed**. Don't claim stored or reusable coverage. A later review may not be able to build on this one.
- PR handoff is **not verified**. Before saying the PR is clean, compare the PR's code, base and scope against this coverage. Hosted Qodo state needs `qodo-review-resolver`. CI and merge are separate checks.

### 4. `older-result`: you asked me to certify full final coverage

**Next step:** I can't certify it. Coverage, inventory completeness and storage are all **unknown**: the result doesn't include them, and nothing else shows them. Missing data isn't proof they're complete. Also, an older result can't vouch for newer work. A fresh assessment of the current intended snapshot would be a good reason for a new review, but you didn't ask for new review effort. So I'd recommend it, not run it.

**Safe claims:**
- An older completed review reported no findings, for whatever scope it actually covered.
- It doesn't show full coverage, a complete inventory or saved state. Don't call it "clean" or "final".

### 5. `entitlement`: closed preview

**Next step:** Stop. Here is the error as returned:
- **Code:** `closed_preview`
- **Message:** "Review access is not enabled for this organization."
- **Hint:** "Ask your administrator to enroll the organization."

Don't retry, switch accounts or deployments, or change the request. A new run needs confirmation that the organization has been enrolled.

**Safe claims:**
- **Review blocked:** this organization doesn't have review access, so no assessment happened.

### 6. `budget`: two of two assessments used

**Next step:** Don't continue reviewing. Your budget of two new assessments applies to the whole finishing attempt, including after the move to a new session, and both have run. The five status checks and the one extended view don't count against it. F-BLOCK still needs action, so there's also no unchanged code worth reviewing again.

**My recommendation:** Stop here. You can continue in either of these ways:
- Decide how to handle F-BLOCK, and authorize the fix if you want one.
- If the fix will need a follow-up review, raise the budget explicitly.

**Safe claims:**
- **Budget reached** and **Needs action:** F-BLOCK is still open and requires action. No newer assessment or authorization exists.
- The work is not ready locally. F-BLOCK hasn't been fixed or dismissed.
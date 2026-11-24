I ran all six through qodo-review's rules on paper only. Nothing was called, polled or submitted, and no files changed.

## 1. `accepted`: op-accepted still working

**Next step:** wait the 20 seconds the server asked for, then check the same operation:
```sh
qodo review status op-accepted --json
```
- Exit `2` (still working): wait the returned `retry_after` and check again.
- Exit `0` (done): read the result, then get the extra stored detail with:
  ```sh
  qodo review status op-accepted --extended --json
  ```
  `--extended` only shows more detail. It doesn't start another review or change the effort.

Don't submit a new review to see progress or to get more detail.

**What you can say:**
- op-accepted was accepted and hasn't finished. That doesn't mean it has passed.
- When it finishes, the result covers the branch and context you had when you submitted. It doesn't cover the branch you switched to or the context you edited since.
- Any findings must be checked against the current code before you act on them. The result can't be used to sign off on your current work.

## 2. `uncertain`: the submission's acceptance reply was lost

**Next step:** run the command the CLI returned, exactly as given:
```sh
qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
```
Don't add flags, don't collect your current checkout or context again, and don't start a separate submission. The retry sends the saved original request. Keep the recovery ID. If the retry returns an operation ID, keep that too and check it as in case 1.

**What you can say:**
- Nobody knows yet whether the review was accepted. There is no operation ID.
- Any result from the retry covers the original snapshot and context, not your changed checkout.
- Covering the current code would need a separate review later, for a concrete reason.

## 3. `storage-gap`: you asked if all local-to-Git work is finished

**Answer: no.** The current code is ready locally, but two items are still open:
- **Ready locally:** yes. The review of the current snapshot completed, coverage and the findings list are complete, no required findings are open, and tests pass.
- **Saved checkpoint:** failed. You can't claim the result was stored or can be reused by later reviews.
- **PR handoff:** not verified. That's a separate check: a qodo-review-resolver check before claiming the PR is Qodo-clean, plus CI and merge.

**Next step:** no new review. The code hasn't changed, so the failed save alone isn't a reason to run another. Report the save failure as it is.

## 4. `older-result`: you asked me to certify full final coverage

**Answer: I can't.** Coverage, findings-list completeness and storage metadata are all missing, and missing means unknown, not complete. The result is also older, so it may not match the current code.

**What you can say:** "An earlier completed review reported no findings for whatever it covered." Don't call it clean, complete or final coverage.

**Next step:** stop. A real sign-off needs a new full review (`--full` is justified because the earlier coverage is unknown). You haven't asked for new review effort, so that's your decision.

## 5. `entitlement`: closed_preview

**Next step:** stop. No retries, no other account, no other deployment.

> **closed_preview** — Review access is not enabled for this organization.
> Hint: Ask your administrator to enroll the organization.

**What you can say:** the review is blocked by entitlement and no review ran. A new run needs confirmation that the organization has been enrolled.

## 6. `budget`: you asked whether to continue

**Answer: don't run another review.** Your limit was two new reviews for this finishing attempt, and both ran. The five status checks and the one extended view don't count toward it. The limit still applies after the move to a new coding session.

**What you can say:**
- **Budget reached.** It also still needs action: F-BLOCK is unresolved.
- There is no newer review or authorization, so nothing supports calling it ready.

**Your options:**
- **Raise the budget explicitly** if you want a third review.
- **Fix F-BLOCK** if you authorize that, run the tests, and hand off with F-BLOCK listed as fixed but not re-reviewed.
- **Hand off as is**, with F-BLOCK listed as an open blocker.

I'd recommend fixing F-BLOCK and handing it off as "fixed, not re-reviewed" unless you want to spend more budget on a re-review.
I used the qodo-review workflow on each case. I didn't run any commands, contact any services or edit any files. Command examples use `qodo` to stand for the installed command you've already verified.

## 1. `mixed-followup`: submit one follow-up review

**Next action:** Submit one follow-up review. The reason is that new code is waiting for review: the timeout fix and the new cancellation API. Keep the effort on auto and keep the same base and scope. Don't add `--full`, because nothing invalidated reuse and you didn't ask for a fresh assessment. Write the context to a file outside the repository and its diff.

**Complete next context:**

```json
{
  "decisions": [
    "The user selected cooperative cancellation without breaking existing callers.",
    "The coding agent kept admission enforcement in src/jobs/worker.ts:runJob so all callers share the mandatory guard."
  ],
  "notes": "src/jobs/worker.ts:runJob rejects invalid input before dispatch. Original timeout finding F-TIMEOUT remains open pending semantic verification. New caller evidence: src/api/jobs.ts:startJob routes cancellation through runJob's admission guard. Cancellation tests passed; live load was not tested.",
  "recent_work": [
    "Changed timeout handling to address finding F-TIMEOUT from the previous review; the fix is an author claim awaiting verification.",
    "Added a new cancellation API; this round includes new behavior, not only fixes."
  ]
}
```

I replaced the old `recent_work` entry because it described work from before review one. That field should only cover changes since the last review. The decisions and notes are unchanged.

**Command:**

```sh
qodo review --base 1111111111111111111111111111111111111111 --async --json --context-file "$QODO_REVIEW_CONTEXT"
```

Include the same path arguments as review one, if it had any. Keep the returned operation ID and collect the result with `qodo review status <operation-id>`. Don't submit again just to check progress.

**Final status:** Pending. Accepting the submission is not a review result. F-TIMEOUT stays open until a completed result settles it.

## 2. `old-backlog`: don't submit again; not ready

**Next action:** Don't submit. No code or evidence has changed, so another review would buy the same result. Instead, decide what to do about F-OLD:
- fix it,
- authorize a stored dismissal with a reason, or
- have it investigated.

**Context:** The review is complete and both completeness flags are true. It found nothing new, but that doesn't settle earlier findings, and F-OLD is still pending and marked action-required.

**Final status:** **Needs action.** The work isn't ready until F-OLD is settled.

## 3. `unsupported-repeat`: stop the loop

**Next action:** Stop. Don't change code and don't submit another review. Your current code shows every caller goes through the unchanged mandatory token guard, so there's nothing to fix and nothing new to review. Based on that evidence, I recommend dismissing F-GUARD. You authorized code fixes, not finding-status writes, so I can't record that dismissal. Skipping it in conversation doesn't dismiss it.

**Context:** The same concern came back without any new evidence, which is the point to stop. Re-fixing guarded code or paying for identical reviews to reach zero findings wouldn't help.

**Final status:** **Needs action.** On the code, the concern isn't supported. F-GUARD stays open in Qodo until you authorize a stored dismissal, which would then need to be read back to confirm it was saved.

## 4. `helper-fixed`: one finding settled, overall not ready

**Next action:** Don't submit again, since nothing has changed. Decide how to handle F-REMAIN: fix it, dismiss it, or investigate.

**Context:** F-HELPER is settled. The completed review with full coverage marks it resolved. That matches the code: the original line didn't change, but the authorized helper fix now rejects the unsafe input before it gets there, and the current tests passed. The same complete inventory still lists F-REMAIN as pending and action-required, and you haven't chosen what to do with it.

**Final status:** F-HELPER is settled, but overall status is **Needs action**. One resolved finding doesn't make the work ready.

## 5. `quote-gone`: you can't claim it's fixed

**What you can claim:** F-QUOTE is still open, and there's no evidence it's fixed. The quoted line disappearing after a rename isn't a fix, so don't mark it resolved or dismissed by hand.

**Next action:** Check whether the unsafe path still exists in the renamed code by following the same inputs and callers. Then:
- If the path is still there and you've authorized fixes, fix it.
- If you only want a report, report it as still open.

If the rename or a later fix hasn't been reviewed yet, that's a valid reason for a follow-up. Its `recent_work` should mention the rename and say the F-QUOTE fix isn't verified.

**Final status:** **Needs action.** F-QUOTE is open and unverified, so readiness can't be claimed.
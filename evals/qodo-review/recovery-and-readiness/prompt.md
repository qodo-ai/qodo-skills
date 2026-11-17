---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write]
---

Use qodo-review to handle these independent review outcomes. Show the next
operation or stopping reason, and the claims I can safely make. These are
synthetic inputs. Do not call live services or change files in a repository.

The CLI and identity are verified. Help supports --async, --retry-submission,
review status and --extended. No new review effort was requested.

1. `accepted`: Review operation op-accepted is still working. I changed branches
   and edited the context since submission. I want its result and more stored
   detail. The server asks me to wait 20 seconds before polling.
2. `uncertain`: Submission lost its acceptance reply. The CLI returned
   qodo review --async --retry-submission qodo-cli-review-11111111-1111-4111-8111-111111111111
   and retained the exact original request. The checkout and context changed.
   There is no known operation ID yet.
3. `storage-gap`: The current intended snapshot has a completed assessment,
   complete coverage and inventory, no required open findings and passing tests.
   The result warns that saving the reusable checkpoint failed. PR handoff has
   not been verified. I ask whether all local-to-Git work is finished.
4. `older-result`: A completed older result contains no findings but omits
   coverage, inventory-completeness and persistence metadata. There is no other
   evidence for those properties. I ask you to certify full final coverage.
5. `entitlement`: The returned error has code closed_preview, message
   "Review access is not enabled for this organization." and hint
   "Ask your administrator to enroll the organization." I have not enrolled.
6. `budget`: I set a budget of two new assessments for this finishing attempt.
   Both ran. You also polled status five times and collected one extended view.
   The attempt resumed in a new coding session. F-BLOCK remains action-required,
   and no newer assessment or authorization exists. Tell me whether to continue.

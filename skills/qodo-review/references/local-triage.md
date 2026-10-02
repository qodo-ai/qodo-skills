# Record local dispositions

Record every decided finding from a completed local review in Qodo, so later reviews and other
sessions do not resurface it. Keep fixing, declining, and uncertainty distinct:

| Decision | Command |
|---|---|
| Fixed: code changed and verified (tests/checks pass) | `mark-implemented` |
| Declined: the user chose not to fix it | `dismiss` with a reason |
| Undecided, investigating, or fix unverified | nothing |

The user's disposition choice authorizes its matching record; do not ask again. Fix authority
(`autofix`, an explicit fix request, the user picking "fix") covers `mark-implemented` for findings
actually fixed and verified. Only the user's decision to decline covers `dismiss`. A recommendation
the user did not choose, or a skipped edit alone, authorizes nothing.

**Record as soon as the decision is made:** `dismiss` right after the user declines,
`mark-implemented` right after the fix is verified. Do not defer to a later review; an interrupted
session must not lose decisions already made.

1. Read each finding's `id` and `local_review_id` from the review result. Keep findings from
   different local reviews in separate batches. Never invent these values or substitute a PR URL.
2. For `dismiss`, choose the supported reason that matches the decision: `false_positive` for an
   incorrect finding, `intentional` for deliberate behavior, `deferred` for postponed work, or
   `rejected` for an understood concern the developer declines to fix. For both commands record a
   concise explanation: what changed, or why it was declined.
   Batch only findings sharing the same `local_review_id`, command, reason, and explanation. Use
   separate calls when their reasons or explanations differ, even within one review.
3. Inspect the input schema of the command you are about to call, e.g.
   `qodo tools help pr-review-session dismiss --json` (or `mark-implemented`). Check
   `parameters.properties.local_review_id` on the returned tool. If inspection fails or the
   tool or field is absent, run `qodo tools --refresh` once and repeat the same inspection. If the
   schema remains unreadable or unsupported, stop and report that local recording is unavailable;
   do not submit without `--local-review-id`.
4. Submit the batch through the existing status tools:

```bash
qodo pr-review-session mark-implemented --finding-ids ID1,ID2 --local-review-id REVIEW_ID \
  --explanation "Bounded the retry loop at 3 attempts." --json
qodo pr-review-session dismiss --finding-ids ID3 --local-review-id REVIEW_ID \
  --reason rejected --explanation "The caller enforces the required limit." --json
```

5. Inspect every per-finding result and report each returned status.
   For `dismiss`, report the stored `reason` and `explanation`; `already_dismissed` preserves the
   original decision: compare those returned values with the request. If they differ, say the prior
   dismissal remains; do not claim the new reason or explanation was saved.
   `reconciled: false` means downstream synchronization needs a retry of that exact request.
   `conflict` or `not_found` is not success. For a stale review reference, review again and
   reassess the finding before acting on the new result.

Keep the returned finding IDs and outcomes in the session's disposition report; a decided finding
whose record failed stays pending and is retried before the next review. Review again after code
changes and read both current findings and `finding_state`; a record does not establish review
coverage or resolve other findings.

An applicable decision can follow the finding into the same verified PR or Gerrit Change.
It does not suppress unrelated Changes, waive repository merge policy, or automatically
cover a changed concern. The server supplies authenticated ownership; do not pass actor,
workspace, or origin values as tool arguments.

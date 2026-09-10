# Record local triage

Use this only for an explicitly authorized dismissal of findings from a completed local review.
Keep fixing, declining, and uncertainty distinct. Existing session authorization can cover the
batch; a recommendation or a skipped edit alone does not authorize a status change.

1. Read each finding's `id` and `local_review_id` from the review result. Keep findings from
   different local reviews in separate batches. Never invent these values or substitute a PR URL.
2. Choose the supported reason that matches the decision: `false_positive` for an incorrect
   finding, `intentional` for deliberate behavior, `deferred` for postponed work, or `rejected`
   for an understood concern the developer declines to fix. Record a concise explanation.
3. Check the available write contract with `qodo read tools pr-review-session --json`. If
   `local_review_id` is absent, refresh discovery once with `qodo tools --refresh`. If still
   unsupported, report that the backend cannot persist this local decision yet.
4. Submit the authorized batch through the existing status tool:

```bash
qodo pr-review-session dismiss --finding-ids ID1,ID2 --local-review-id REVIEW_ID \
  --reason rejected --explanation "The caller enforces the required limit." --json
```

5. Inspect every result. `dismissed` or `already_dismissed` confirms the stored decision;
   `reconciled: false` means downstream synchronization needs a retry of that exact request.
   `conflict` or `not_found` is not success. For a stale review reference, review again and
   reassess the finding before acting on the new result.

Keep the returned finding IDs and outcomes in the session's disposition report. Review again
after code changes and read both current findings and `finding_state`; a dismissal does not
establish review coverage or resolve other findings.

An applicable decision can follow the finding into the same verified PR or Gerrit Change.
It does not suppress unrelated Changes, waive repository merge policy, or automatically
cover a changed concern. The server supplies authenticated ownership; do not pass actor,
workspace, or origin values as tool arguments.

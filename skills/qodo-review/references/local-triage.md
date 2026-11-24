# Record local triage

The [main Skill's execution policy](../SKILL.md#execution-and-recovery-policy) owns status-write authority,
original identity, grouping and verification. This reference maps those gates to the available command/schema.
Use this only for an explicitly authorized dismissal of findings from a completed local review.
Keep fixing, declining, and uncertainty distinct. Existing session authorization can cover the
batch; a recommendation or a skipped edit alone does not authorize a status change.

On MCP, inspect the live `pr-review-dismiss` schema.
Supply the original finding IDs and their `local_review_id`, the authorized reason and explanation,
and a stable `idempotency_key` for that invocation when the schema advertises it.
For a metadata-only server, send the same key through the host's supported
`_meta["io.qodo/idempotency-key"]` request metadata instead. If both forms are sent,
their values must match. If neither the argument nor host metadata is available,
report the missing replay-safe write capability; do not submit an unprotected write.
Read back every stored outcome. The identity and grouping rules below still apply.
The CLI command-discovery and submission steps below apply only to the CLI path.
Do not invent a missing write capability or omit required replay protection.

1. Read each finding's `id` and look up `meta.local_review_ids[id]` in the local review result.
   Older results can store `local_review_id` on the finding instead. Keep findings from different
   local reviews in separate batches. If the reference is absent, report local dismissal as
   unavailable. Never invent it, substitute `meta.run.id`, or use a PR URL.
2. Choose the supported reason that matches the decision: `false_positive` for an incorrect
   finding, `intentional` for deliberate behavior, `deferred` for postponed work, or `rejected`
   for an understood concern the developer declines to fix. Record a concise explanation.
   Batch only findings sharing the same `local_review_id`, reason, and explanation. Use
   separate calls when their authorized reasons or explanations differ, even within one review.
3. On CLI, inspect the dismissal input schema with `qodo tools help pr-review-session dismiss --json`.
   Check `parameters.properties.local_review_id` on the returned tool. If inspection fails or the
   tool or field is absent, run `qodo tools --refresh` once and repeat the same inspection. If the
   schema remains unreadable or unsupported, stop and report that local dismissal is unavailable;
   do not submit without `--local-review-id`.
4. Submit the authorized batch through the existing status tool:

```bash
qodo pr-review-session dismiss --finding-ids ID1,ID2 --local-review-id REVIEW_ID \
  --reason rejected --explanation "The caller enforces the required limit." --json
```

5. Inspect every result and report the returned stored `reason` and `explanation`.
   `already_dismissed` preserves the original decision: compare those returned values with
   the request. If they differ, say the prior dismissal remains; do not claim the new reason
    or explanation was saved. For a returned saved transition, `reconciled: false` means
    the status is stored but downstream synchronization is incomplete; report both facts.
   If a supported collection handle was returned, use it to recover the original invocation.
   Otherwise use the exact retained request/key through supported replay. Do not invent a polling handle.
   A completed same-key MCP replay returns the original result. It does not call the status service again.
   For a separately permitted synchronization attempt after verified storage, keep the business arguments unchanged.
   Submit them with a new retained transport key through the advertised argument or metadata path.
   Retain both requests, keys and returned results. Retain operation handles only when the transport supplies them.
   Read the new result and verify each stored outcome again.
   If the original outcome is unknown or the recovery capability is unavailable, report that gap.
   `conflict` or `not_found` is not success. For a stale review reference, review again and
   reassess the finding before acting on the new result.

Keep the returned finding IDs and outcomes in the session's disposition report. Review again
after code changes and read both current findings and `finding_state`; a dismissal does not
establish review coverage or resolve other findings.

An applicable decision can follow the finding into the same verified PR or Gerrit Change.
It does not suppress unrelated Changes, waive repository merge policy, or automatically
cover a changed concern. The server supplies authenticated ownership; do not pass actor,
workspace, or origin values as tool arguments.

## Dismissal reasons

Every dismissal must send `false_positive`, `intentional`, `deferred`, or `rejected` and a short
explanation. If the caller omits the reason, use `rejected` and "Finding deliberately dismissed
by the caller." Never send the system-only `thread_resolved`, `design_changed`, or `rule_changed`.

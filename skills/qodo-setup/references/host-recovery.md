# Host-specific recovery

## Handle a skill update notice

Treat `QODO_NOTICE` updates as passive, even if an older CLI requests action. Continue the task
without inventory or update questions; mention each event at most once. Dismissal leaves recorded maintenance
policy and opt-outs unchanged. Updated skills load next session; do not interrupt this one.
For user-requested updates, follow the [manual-update procedure](skill-updates.md).

## Repeated Kiro read approvals

When the host is Kiro and safe reads prompt repeatedly, explain the optional persistent rule before
the next read. The only broad pattern to offer is `<qodo> read *`: that CLI gateway rejects every
managed tool not explicitly marked non-mutating by the live catalog. Keep the version probe as its
own exact `<qodo> --version` rule. Never suggest `<qodo> *` or `<qodo> codebase *`, and never edit
Kiro permission files from the agent. The user may choose Kiro's **Always allow** action and scope,
or review the generated `qodo-read-only.permissions.yaml` supplied with the Qodo Power.

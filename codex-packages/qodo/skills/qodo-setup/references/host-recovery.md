# Host-specific recovery

## Handle a skill update notice

A Qodo command can emit `QODO_NOTICE <json>` to stderr while still succeeding. When
`code` is `qodo_skill_update_available`, keep the command's result and finish the current
task. Then follow the notice's `steps`: do read-only inventory first, resolve the installed
Qodo package and scope, show the exact lifecycle-owner update command or UI action, and ask
once before any mutation. If the user declines, keep the current version usable.

Never invoke a different lifecycle owner, guess a placeholder, or install an optional package
implicitly. After an approved update, ask for the host restart named by the notice; the current
session may still have the old skill loaded.

## Repeated Kiro read approvals

When the host is Kiro and safe reads prompt repeatedly, explain the optional persistent rule before
the next read. The only broad pattern to offer is `<qodo> read *`: that CLI gateway rejects every
managed tool not explicitly marked non-mutating by the live catalog. Keep the version probe as its
own exact `<qodo> --version` rule. Never suggest `<qodo> *` or `<qodo> codebase *`, and never edit
Kiro permission files from the agent. The user may choose Kiro's **Always allow** action and scope,
or review the generated `qodo-read-only.permissions.yaml` supplied with the Qodo Power.

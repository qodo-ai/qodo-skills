# Host-specific recovery

## Handle a skill update notice

Treat `QODO_NOTICE` availability as passive information: retain the result and continue the task.
Do not inventory or ask to update because of a notice, even if an older CLI says to ask.
Mention it at most once; dismissal does not disable updates.
Qodo automatically maintains verified enterprise installations under their recorded policy,
source and opt-outs. Other installations retain their lifecycle owner; do not replace it.
Only for requested maintenance, inspect `<qodo> agents update --help`. When supported, preview
enterprise updates with `<qodo> agents update --enterprise --dry-run --json`; explain the full
packages, physical locations and affected integrations before any additional consent. Reuse
existing approval covering that operation, then execute its exact returned `--apply-plan` command.
Never expand a narrow approval or add optional packages. Without preview support, direct the
user to interactive `<qodo> agents update --enterprise`; do not guess an agent-scoped command.
Report persistent failures once without bypassing checks. New sessions load updated files; old
loaded instructions do not prove installed files are outdated. Do not interrupt or restart.

## Enterprise setup policy

Before installing enterprise skills, explain that Qodo will automatically maintain the disclosed
installations and selected packages from the verified organization source, respecting existing
opt-outs. Setup consent covers that policy; a notice or unrelated task does not authorize enrollment.

## Repeated Kiro read approvals

When the host is Kiro and safe reads prompt repeatedly, explain the optional persistent rule before
the next read. The only broad pattern to offer is `<qodo> read *`: that CLI gateway rejects every
managed tool not explicitly marked non-mutating by the live catalog. Keep the version probe as its
own exact `<qodo> --version` rule. Never suggest `<qodo> *` or `<qodo> codebase *`, and never edit
Kiro permission files from the agent. The user may choose Kiro's **Always allow** action and scope,
or review the generated `qodo-read-only.permissions.yaml` supplied with the Qodo Power.

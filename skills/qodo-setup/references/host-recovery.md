# Host-specific recovery

## Handle a skill update notice

Treat `QODO_NOTICE` availability and completion as passive: continue the task without inventory or update questions, even if an older CLI asks.
Mention each event at most once. Dismissal does not disable verified enterprise maintenance under its recorded policy, source and opt-outs; other lifecycle owners remain unchanged.
For requested enterprise maintenance, keep commands and any approvals in this conversation; do not require a terminal or TTY.
Inspect `<qodo> agents update --help`. If planning is supported, skip runtime recovery and use the skills preview below.
Only if planning is unavailable, inspect `<qodo> update --help` and use the supported `<qodo> update --check --json`. Require the recorded source and a newer release in its result, not just exit zero; otherwise explain the blocker and stop this maintenance attempt.
For this fallback, explain the CLI prerequisite before updating: skill-update consent alone does not authorize a CLI upgrade. Reuse authorization covering the runtime update, otherwise ask once.
In that fallback, run `<qodo> update --json` once within that authorization; never override the source or channel. Stop on denial or failure; do not reinstall, switch owners or fall back to a public source.
Recheck `<qodo> --version` and `<qodo> agents update --help`; if planning remains unavailable, report the blocker in this conversation without repeating the upgrade or directing the user to a terminal.
When planning is supported, run `<qodo> agents update --enterprise --dry-run --json`. Explain the package and complete affected installation scope in plain language before any still-needed approval.
Reuse approval covering that operation. Execute the returned `--apply-plan` command from `commands.sh` or `commands.powershell` for the tool’s shell (Git Bash uses `sh`, including on Windows); older previews expose `command`. The user need not type flags, paths or agent IDs.
Never expand a narrow approval or add optional packages. CLI-only consent does not approve the skills operation; reuse any existing approval covering its resolved scope.
Report persistent failures once without bypassing checks. New sessions load updated files; old loaded instructions do not prove installed files are outdated. Do not interrupt or restart the current session.

## Repeated Kiro read approvals

When the host is Kiro and safe reads prompt repeatedly, explain the optional persistent rule before
the next read. The only broad pattern to offer is `<qodo> read *`: that CLI gateway rejects every
managed tool not explicitly marked non-mutating by the live catalog. Keep the version probe as its
own exact `<qodo> --version` rule. Never suggest `<qodo> *` or `<qodo> codebase *`, and never edit
Kiro permission files from the agent. The user may choose Kiro's **Always allow** action and scope,
or review the generated `qodo-read-only.permissions.yaml` supplied with the Qodo Power.

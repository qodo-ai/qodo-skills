# Manual enterprise skill updates

Keep commands and approvals in this conversation; do not hand off to a terminal.

1. Resolve `<qodo>` and complete the parent skill’s Runtime compatibility gate, starting with unadorned `<qodo> --version`. Reuse completed checks; any runtime upgrade counts toward the one recovery attempt below.
2. Check `<qodo> agents update --help` for planning support. If missing, use runtime recovery below. Otherwise preview with `<qodo> agents update --enterprise --dry-run --json`. If that preview reports a higher CLI version prerequisite, use the same bounded runtime recovery, then retry the preview once; stop if the prerequisite remains unsatisfied.
3. If the preview returns a plan, explain the packages, complete affected installation scope, and any `retainedSkills` that will stay at their previous content. Reuse covering authorization or ask once, then execute the exact returned `--apply-plan` command using `commands.sh` or `commands.powershell` for the tool's shell (Git Bash uses `sh`; older previews expose `command`).

Compatible CLIs can add a verified core skill and retain an omitted recorded skill at its previous content during automatic maintenance. If a preview still reports changed core membership, use Runtime recovery below and retry the preview once only if no runtime upgrade has been attempted and a newer CLI is available. Otherwise continue to the explicit-install fallback.

For a remaining membership blocker, inspect `<qodo> agents status --json` and `<qodo> agents install --help`. If status records the optional Standards package, read `standardsAgents` when present; on older CLIs, use `<qodo> skills list --json` and require both Standards skills to show verified `enterprise-bundle` locations for the same agent subset. Stop if that selected subset is ambiguous. Explain the complete recorded core-agent scope and any separate Standards-agent subset; reuse covering installation authorization or ask once. For an authorized noninteractive recovery:

1. Install core for every recorded core agent with `<qodo> agents install --enterprise --agent <comma-separated-core-ids> --yes`, without `--standards`.
2. If Standards was already selected, install it for only its recorded subset with `<qodo> agents install --enterprise --standards --agent <comma-separated-standards-ids> --yes`.

`--yes` confirms the approved scope; it does not grant authorization. Verify every recorded core and Standards agent before claiming the new skill is available. If either step fails, report the incomplete operation and inspect status before retrying.

Never widen approval, change owners or add optional packages. Report persistent failures once without bypassing checks. Loaded instructions may be older than installed files.

## Runtime recovery

Stop if a runtime upgrade was already attempted. Otherwise inspect `<qodo> update --help`, then use the supported `<qodo> update --check --json`; require a newer release and the recorded source in its result.
Explain the CLI prerequisite and reuse runtime-update authorization or ask once; skills-only consent is insufficient. Run `<qodo> update --json` once without source/channel overrides. Recheck unadorned `<qodo> --version` and require the skill minimum before rechecking planning support and returning to the preview.
Stop on denial, failure, missing metadata or continued incompatibility; never reinstall or switch sources. Runtime-only consent does not approve the skills operation.

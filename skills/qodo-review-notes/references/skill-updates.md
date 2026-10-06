# Manual enterprise skill updates

Keep commands and approvals in this conversation; do not hand off to a terminal.

1. Resolve `<qodo>` and complete the parent skill’s Runtime compatibility gate, starting with unadorned `<qodo> --version`. Reuse completed checks; any runtime upgrade counts toward the one recovery attempt below.
2. Check `<qodo> agents update --help` for planning support. If missing, use runtime recovery below. Otherwise preview with `<qodo> agents update --enterprise --dry-run --json`.
3. Explain the packages and complete affected installation scope. Reuse covering authorization or ask once, then execute the exact returned `--apply-plan` command using `commands.sh` or `commands.powershell` for the tool's shell (Git Bash uses `sh`; older previews expose `command`).

If the preview reports that core membership changed (for example, the package adds `qodo-review-notes`), automatic maintenance cannot add that skill. Inspect `<qodo> agents install --help`, explain the complete package and every recorded agent target, and reuse covering installation authorization or ask once. Use `agents install --enterprise` with all those `--agent` targets and the existing package selection; include Standards only if already selected. Verify the resulting installation before claiming the new skill is available.

Never widen approval, change owners or add optional packages. Report persistent failures once without bypassing checks. Loaded instructions may be older than installed files.

## Runtime recovery

Stop if a runtime upgrade was already attempted. Otherwise inspect `<qodo> update --help`, then use the supported `<qodo> update --check --json`; require a newer release and the recorded source in its result.
Explain the CLI prerequisite and reuse runtime-update authorization or ask once; skills-only consent is insufficient. Run `<qodo> update --json` once without source/channel overrides. Recheck unadorned `<qodo> --version` and require the skill minimum before rechecking planning support and returning to the preview.
Stop on denial, failure, missing metadata or continued incompatibility; never reinstall or switch sources. Runtime-only consent does not approve the skills operation.

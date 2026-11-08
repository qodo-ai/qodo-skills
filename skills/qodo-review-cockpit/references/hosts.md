# Hosts and prerequisite recovery

Resolve the installed skill directory from this SKILL.md, not the workspace, current directory
or CLAUDE_PLUGIN_ROOT (which may hold several skills). POSIX: `python3 -B "<skill>/scripts/launch.py"`.
PowerShell: `python -B '<skill>/scripts/launch.py'`; confirm that interpreter is Python 3.9+.
Arguments are passed directly, without shell evaluation. Keep the server process alive in the
host's supported background session; do not use a process timeout that kills an active review.
If the browser cannot be opened automatically, show the printed loopback URL.

The launcher probes the installed `qodo` command, then `qodo read whoami`, then `qodo read tools`.
It never logs in, installs dependencies, or updates. Read its gate-specific error. Use qodo-setup
for an authorized setup. A CLI below 2.x needs explicit major-install authorization; a failed
version parse is not permission to upgrade. Never print credentials or update-origin URLs.
Preserve deployment-specific login and the recorded origin. An unavailable Python interpreter
requires user-owned installation; no nested agent, package manager or bootstrap runs on launch.

Read tools only through the CLI catalog gateway. Unsupported provider sections and failed reads
must stay visible as unavailable. Stop on permission denial rather than using another account,
gh, provider APIs, a local clone or an alternate workspace. The runtime's product mode disables
provider publication; changing configuration does not authorize bypassing it.

`review-prs` is legacy request wording. This package does not install or overwrite a review-prs
alias, standalone checkout, ~/.claude/skills root or ~/.agents/skills root. Ask to use
qodo-review-cockpit explicitly if another installed skill owns that name.

Generation/resource retention is tested for advertised hosts; real browser/process lifetime
acceptance must be reported per host. Optional Ask Qodo requires an already available supported
host adapter; never silently install or launch another coding agent during setup.

I ran no commands and wrote no files. None of the three cases allows a runtime change or a review submission without further input from you.

## 1. `ordinary-update-check`

Version 1.6.0 is below the required 2.0.0. That already stops identity checks (`whoami`), login, reviews and managed tools until a compatible runtime exists. The ordinary-update route only goes ahead if its check offers a newer compatible 2.x version.

| Check result | Next allowed action |
|---|---|
| **TLS error** | Stop before changing anything. Report the TLS failure as it is, not as a login problem. Don't retry the check, switch to `latest-2`, or use the installer route. |
| **No update** | Stop without changing anything. Report that no compatible target was offered. Don't switch routes. |
| **Offers 3.0.0** | Stop without changing anything. Your approval covered a compatible 2.x target only, not a new major version. Don't install 3.0.0 and don't fall back to `latest-2`. |

In every subcase, the next action is to report **Review blocked**: the version is 1.6.0, the route was ordinary update, and the check gave the result above.

**Still pending:** the update, the version re-check, `whoami`, `qodo review --help`, and the review. They need a working compatible target or a new route decision from you. The recorded origin and update holds stay unchanged.

## 2. `missing-cli`

Neither bare `qodo` nor the trusted fallback works, so the CLI path stops. I won't run any launcher from the repository, won't install anything (there's no approval and no checksum-pinned installer), and won't log in or change accounts or deployments. MCP isn't an option either: it can't read this worktree without a tested collector, and none was supplied. A plain `git diff` doesn't count as one.

**Next allowed action:** report **Review blocked** because no trusted runtime is available. To unblock it, you'd need one of these:
- a working installed invocation
- approval plus a checksum-pinned installer from Qodo or your organization
- an MCP setup with a tested collector that covers the intended scope and exclusions

**Still pending:** the version check, identity, help, and the review itself.

## 3. `user-no-retry`

`repo_not_connected` is a recoverable terminal failure. Normally that allows one resubmission with the cause corrected, here by adding the repository name. Your instruction not to retry automatically overrides that, so it needs your explicit approval first.

**Next allowed action:** report the failure, keeping the operation ID and the error envelope. Then propose the exact resubmission and ask you to approve it:
- the same base, scope and session context
- auto effort (neither `--fast` nor `--deep`)
- plus `--repo <exact connected full_name>`

**Still pending:** the resubmission itself. If you approve it, it uses the single retry allowance, and any further failure stops. That includes permission, authentication, entitlement and rate-limit errors. Until then the result is **Review blocked**, and nothing gets assessed or certified.
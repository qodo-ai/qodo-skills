### 1. `ordinary-update-check`

Each result independently stops recovery:

| Check result | Next allowed action |
|---|---|
| TLS error | Report the check failure. Do not weaken TLS or treat it as missing credentials. |
| No update | Report that no approved compatible target was offered. |
| Version `3.0.0` offered | Report that the target is incompatible with the approved 2.x requirement. |

Do **not** run the update, switch to `latest-2`, use an installer, or change deployments. Preserve the recorded origin, version choices and update holds.

**Pending:** Compatible-runtime recovery and the review. With `1.6.0`, identity, login, review and managed-tool calls remain blocked.

### 2. `missing-cli`

Report that CLI review is blocked and stop the CLI path. Do not install anything, run a repository-local launcher, invent a checksum, pipe an installer into a shell, or change accounts/deployments.

Proceeding requires either a working trusted installed invocation or separate installation approval covering a Qodo/organization-supplied checksum-pinned installer.

**Pending:** Runtime compatibility verification, identity verification and review. No review coverage has been established.

### 3. `user-no-retry`

Do **not** resubmit automatically. Your explicit no-auto-retry instruction applies even though the error itself permits recovery.

The next allowed action is to ask:

> May I make one cause-corrected resubmission using `--repo` with the known exact connected repository `full_name`, preserving the original base, scope, context and auto effort?

Retain the failed operation handle and error. Do not log in, change accounts or switch deployments.

**Pending:** Your approval, the corrected submission and its completed assessment. If approved, that submission uses the single cause-corrected retry allowance; further failure does not create another allowance.

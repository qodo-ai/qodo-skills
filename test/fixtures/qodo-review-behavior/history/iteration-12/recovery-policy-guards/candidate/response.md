### 1. `ordinary-update-check`

Each subcase stops before any runtime change:

| Check result | Next allowed action |
|---|---|
| TLS error | Report the check failure; preserve the TLS error. |
| No update | Report that no compatible update was offered. |
| Version `3.0.0` offered | Reject it as outside the approved compatible 2.x target. |

Do **not** run the update, switch to `latest-2`, or fall back to an installer. Preserve the deployment origin, version choices and update holds.

**Pending:** compatibility recovery and review. CLI `1.6.0` cannot proceed to identity, login, review or managed-tool calls.

### 2. `missing-cli`

Stop the CLI path and report that neither trusted installed invocation is available. Review authorization does not authorize environment installation.

Do not use a repository-local launcher, invent an installer checksum, or change accounts or deployments.

**Pending:** installation requires explicit covering approval and a Qodo/organization-supplied checksum-pinned installer. Review remains blocked until a trusted compatible runtime is available and preflight succeeds.

### 3. `user-no-retry`

Do not resubmit automatically. The explicit no-retry instruction takes precedence over the error’s recoverability.

Ask:

> May I make one corrected resubmission using `--repo` with the known exact connected repository `full_name`, retaining the current base, scope, context and auto effort?

Retain the failed operation ID and terminal error. If approved, that correction consumes the single cause-corrected resubmission allowance; collect its operation if accepted.

**Pending:** explicit approval and completed review coverage. The failed assessment does not establish readiness.

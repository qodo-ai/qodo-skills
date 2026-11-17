### 1. `ordinary-update-check`

Stop compatibility recovery in every subcase:

- **TLS error:** report the check failure; do not bypass TLS or reinterpret it as missing credentials.
- **No update:** report that no compatible target was offered.
- **Version 3.0.0:** reject it as incompatible with the required 2.x runtime.

Do not run the update, switch to `latest-2` or an installer, change deployment, or alter version pins/update holds. Any `QODO_UPDATE_BASE_URL` check must expose only whether it is set, never its value; if set, stop for the user.

**Pending:** compatible-runtime recovery. With 1.6.0, identity, login, reviews and managed-tool calls remain blocked. The conditional update approval was not satisfied.

### 2. `missing-cli`

Stop the CLI path and report the missing-runtime blocker. Review authorization does not authorize installation.

Proceed only after a trusted installed invocation becomes available, or after separate installation approval **and** a Qodo/organization-supplied checksum-pinned installer are provided. Do not use a repository-local launcher, invent a checksum, pipe an installer into a shell, or change accounts/deployments.

**Pending:** runtime availability, compatibility and identity verification, then review. Do not substitute an unverified MCP collector or claim review coverage.

### 3. `user-no-retry`

Do not resubmit automatically. The explicit no-auto-retry instruction overrides the otherwise available recovery allowance.

Retain the failed operation ID and error, plus the original base, scope, context and auto effort. Ask:

> May I make one cause-corrected resubmission using the known connected repository’s exact `full_name` through `--repo`, preserving the original base, scope, context and auto effort?

If approved, that consumes the single cause-corrected resubmission allowance; collect its new operation ID if accepted.

**Pending:** explicit approval, corrected submission and completed assessment. The terminally failed run does not establish review coverage.

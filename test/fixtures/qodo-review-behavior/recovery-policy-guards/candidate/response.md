### 1. `ordinary-update-check`

Each result independently stops the selected recovery route:

| Check result | Next allowed action |
|---|---|
| TLS error | Report the TLS failure. Do not bypass TLS, attempt the update, or treat it as missing credentials. |
| No update | Report that no eligible target was offered. Do not run the update. |
| Offers `3.0.0` | Report that the target is incompatible with the required 2.x runtime. Do not install it. |

The conditional approval is not satisfied in any subcase. Do not switch to `latest-2`, an installer, another origin or another deployment. Preserve update holds and policy. Any override inspection must check only whether `QODO_UPDATE_BASE_URL` is set, without displaying its value; if set, stop for user direction.

**Pending:** compatible-runtime recovery and the review. Runtime `1.6.0` cannot proceed to identity, login, review or managed-tool calls. Any later authorized recovery must pass a fresh unadorned version probe before authenticated calls.

### 2. `missing-cli`

**Next allowed action:** report that the CLI review path is blocked and stop. Neither trusted installed invocation exists.

Review permission does not authorize installation. Do not run a repository-local launcher, invent an installer checksum, bootstrap an unapproved installation, or change accounts/deployments.

**Pending:** review execution. Installation would require separate approval and a Qodo/organization-supplied checksum-pinned installer. MCP is not an automatic substitute: it requires a tested local collector meeting the scope and safety requirements.

### 3. `user-no-retry`

**Next allowed action:** report the terminal `repo_not_connected` failure and ask:

> Do you approve one corrected resubmission using `--repo` with the known exact connected repository `full_name`, preserving the original base, scope, context and auto effort?

Do not resubmit before approval. The error’s lack of a retry prohibition does not override your explicit no-auto-retry instruction. Preserve the failed operation ID and error evidence.

**Pending:** approval and completed review coverage. If approved, this uses the single cause-corrected resubmission allowance; collect its operation ID if accepted. It does not create a new retry allowance for subsequent failures.

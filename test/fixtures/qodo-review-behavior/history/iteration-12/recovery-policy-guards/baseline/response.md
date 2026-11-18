### 1. `ordinary-update-check`

Each result independently stops recovery:

- **TLS error:** Report the check failure. Do not bypass TLS or treat it as missing credentials.
- **No update:** Do not run the updater; no compatible target was offered.
- **Version 3.0.0:** Reject the incompatible target. Do not install it.

Do not switch to `latest-2`, an installer, another deployment or another account. Identity, login, review and managed-tool calls remain blocked on CLI 1.6.0. A verified compatible 2.x runtime remains pending.

### 2. `missing-cli`

**Review blocked:** Neither trusted installed invocation exists.

Do not use a repository-local launcher, download or install anything, or change accounts or deployments. Review authorization does not authorize installation. Installation would require separate approval and a Qodo/organization-supplied checksum-pinned installer; neither is present.

The review remains pending a trusted, compatible runtime and successful preflight.

### 3. `user-no-retry`

**Stop before resubmission.** Your no-automatic-retry instruction overrides the otherwise available repository-identity recovery.

Retain the failed operation ID, error, original base, scope, context and auto effort. The failed run provides no completed review coverage.

May I make one corrected resubmission using `--repo` with the known connected repository’s exact `full_name`, preserving all other review inputs?

Until you explicitly approve, no corrected submission occurs. If approved, collect the resulting operation rather than launching additional reviews; any further failure stops recovery.

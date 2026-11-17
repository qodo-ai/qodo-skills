### 1. `ordinary-update-check`

Each result independently requires stopping:

- **TLS error:** Preserve the TLS failure. Do not update, relabel it as a login problem, or switch routes.
- **No update:** Do not run the updater. The check did not satisfy the approval condition.
- **Version 3.0.0 offered:** Reject the incompatible target. Do not install it.

In all three cases, do not fall back to `latest-2` or an installer. Preserve the deployment origin, version choices and update holds. Identity, login, managed tools and review remain pending because CLI 1.6.0 is incompatible. Recovery requires a separately approved path; none is currently authorized.

### 2. `missing-cli`

Report **Review blocked: no trusted installed CLI invocation is available**, and stop the CLI path.

Do not run a repository-local launcher, download an installer, invent a checksum, or change accounts or deployments. A review request does not authorize installation.

Installation remains pending covering approval and a Qodo/organization-supplied checksum-pinned installer. Compatibility, identity and the requested review remain unperformed. Do not assume an alternative collector is available.

### 3. `user-no-retry`

Do **not** resubmit automatically. The user's explicit prohibition applies even though the error itself permits recovery.

Report the terminal failure and request explicit approval for **one corrected resubmission using `--repo` with the known exact connected repository name**. Preserve the current base, scope, context and auto effort; omit `--fast` and `--deep`.

Until approved, the corrected submission and review coverage remain pending. Retain the failed operation’s ID and error. If approved, the correction uses the single bounded terminal-recovery attempt—not an additional retry allowance. Collect the new operation if accepted; stop if that retry fails.

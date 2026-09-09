# Authentication and execution context

Read for an identity failure or before any customer-deployment login. Invoke the identity
command from SKILL.md so the active package/version/distribution/host provenance is preserved.

## Classify the identity result

- Successful identified account: retain it and proceed to catalog verification.
- `unknown command` or `unknown option`: runtime-contract failure; report it and stop.
- Network, TLS, service, or authorization errors: preserve the error and address that cause.
  Do not treat every nonzero exit as signed out or automatically start login.
- `not_logged_in` or missing credentials: this can mean an absent credential or an inaccessible
  keychain. In a sandbox that may block credential access, request the host's approval for
  one exact read-only identity retry outside that sandbox. This is unnecessary when already
  running in the working context or after an approved unsandboxed check established sign-out.
  If denied, stop. If it succeeds, retain that context and proceed. If it again reports missing
  credentials, choose login below. Other retry errors retain their own diagnosis.
- Explicit sandbox/network denial: request the narrow permission needed for the failed check
  through the host. Do not relax the host's configuration.

Keep the executable, user, QODO_HOME and deployment consistent. Once login or an identity
check works outside a restricted sandbox, run subsequent identity/catalog checks in that
same context with the host's required approvals. Do not first repeat them in the sandbox
known to hide credentials. Approval for one diagnostic does not authorize other commands.
Do not change credential storage, set QODO_NO_KEYCHAIN, or export tokens as a workaround.

If the post-login identity still fails in the context where login succeeded, stop with that
error; do not loop through browser sign-in. Never refresh tools before identity succeeds.

## Resolve the login destination

Choose the login command before opening a browser:

- For Qodo Cloud, run `<qodo> login`.
- For a customer deployment, preserve the exact deployment-specific command from the
  installer, administrator, or user, such as `<qodo> login --auth-url <their-url>`.
- Plain login is safe for a customer only with explicit evidence in this interaction that
  CLI 0.1.0-next.37 or newer retained the endpoint (for example, logout reported retaining
  it). Never assume a previous installation saved the endpoint, or read credentials to
  infer it. Keep any provided QODO_AUTH_URL consistent with the chosen destination.
- If a customer deployment is known but no exact command, endpoint, or retained-endpoint
  evidence is available, obtain that command from the administrator before login.
  Never probe or fall back to Qodo Cloud.

Tell the user browser sign-in will open. Run login once, wait for the process to finish and
inspect its outcome. On cancellation or failure, report that Qodo is still not connected.
After success, verify identity using the main skill's command, then verify the catalog.

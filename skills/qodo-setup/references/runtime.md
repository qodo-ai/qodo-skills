# Runtime discovery and installation

Read when the CLI is missing, outdated, or the host uses PowerShell.
Keep the first working executable for the rest of setup; no extra PATH edits are needed.

## PowerShell discovery

The extensionless `bin/qodo` is a POSIX script. Resolve a verified native invocation:

1. If `QODO_HOME` is configured, use that installation's `bin` directory. If it is unusable,
   report the blocker; do not silently select a different installation.
2. Otherwise inspect absolute directories from the process PATH in order, then Windows'
   persisted user PATH (`[Environment]::GetEnvironmentVariable('Path', 'User')`). Ignore
   empty or relative entries and expand environment variables as data, without executing
   them. Inspect existing files; do not edit either PATH or search the workspace.
3. A usable installation directory contains an existing `qodo.mjs` plus either `qodo.exe`
   or `qodo.cmd`. Use the first usable PATH installation. If none exists, check the default
   `(Join-Path $HOME '.qodo')/bin` directory. Custom roots need not set `QODO_HOME` when
   their installer registered a usable absolute directory in the user PATH.
4. Check the selected directory's `qodo.exe` with `Test-Path -LiteralPath <path> -PathType Leaf`.
   If it exists, use it. Otherwise run that same installed `qodo.mjs` directly with Node.
   Resolve Node with `Get-Command node -CommandType Application -ErrorAction SilentlyContinue`.
   If absent, read the selected `qodo.cmd` as text and use an existing absolute Node path
   from its `set "NODE=..."` lines. Do not execute that batch launcher to discover Node.
5. Verify the selected executable and entry point exist before invoking them. If no native
   invocation is usable, report the launcher blocker; do not proceed to auth or reinstall.

Run the unadorned `--version` probe with that executable, or Node followed by the installed
entry point. Retain the invocation and authenticated deployment for every later command;
recompute the selection if host shell state does not persist. Do not execute `qodo.cmd`.

## Missing runtime

Use the official installer; do not reconstruct the manifest/download/shim installation in
ad hoc code. The installer requires Node.js >=20.6.0 and verifies the CLI artifact against
the SHA-256 in its distribution's version.json before installing it under QODO_HOME
(default ~/.qodo). It also configures its launchers and shell PATH integration.

1. Resolve the distribution from this interaction and keep its installer URL, expected
   SHA-256, channel and distribution/auth settings together throughout installation.
   For Qodo Cloud use these published, immutable installer pins:

   | Platform | Installer URL | Expected SHA-256 |
   | --- | --- | --- |
   | POSIX | `https://get.qodo.ai/installers/bd546a0fc51ac4bb32486c9f766870ba0dedef27bf0472bb1e15ffdede52acf8/install.sh` | `bd546a0fc51ac4bb32486c9f766870ba0dedef27bf0472bb1e15ffdede52acf8` |
   | PowerShell | `https://get.qodo.ai/installers/4ebee2878d8d39bbbdd3153aff1c6a329601d844df7ce915b7a54739aa32d498/install.ps1` | `4ebee2878d8d39bbbdd3153aff1c6a329601d844df7ce915b7a54739aa32d498` |

   For a customer deployment, use its exact installer URL and expected SHA-256 from the
   organization-provided installation instructions. Preserve QODO_INSTALL_BASE, the login
   endpoint and any channel/installer arguments. Do not fetch the public installer or apply
   a Cloud digest to a customer script. A base or login endpoint alone does not establish the
   installer URL and checksum; obtain missing information from the administrator. Never guess
   a mirror path or fall back to the public distribution.
2. Check `node --version`. If missing or too old, explain the prerequisite and help the user
   install a supported Node version within their authorization before resuming setup.
3. Download from the selected URL into a unique, user-private temporary directory. Use
   `curl --fail --silent --show-error --location` on POSIX, or `Invoke-WebRequest` with a
   `.ps1` destination on PowerShell. Calculate the file's SHA-256 with `sha256sum`,
   `shasum -a 256` or Node's `crypto.createHash('sha256')`; PowerShell has `Get-FileHash`.
   Require an exact match to the expected digest before reading or executing the script.
   Stop on a failed download, missing digest or mismatch; never derive the expected digest
   from the downloaded file, replace it after a mismatch or use a mutable installer alias.
   Keep the verified absolute file path across tool calls and execute those same bytes.
   No guessed README URL, npm package, remote pipe or installer reconstruction is needed.
4. Inspect the verified script, then explain that you will run it to install the user-scoped
   runtime and PATH integration. A user who asked to set up Qodo
   has requested this installation; request only approvals still required by the host or
   a narrower user instruction. Inspect the downloaded script before requesting execution.
   Installer verification above and the installer's later CLI-artifact verification are
   separate checks; require both and never invent a checksum.
5. Run the saved script with `sh` (POSIX) or a PowerShell process (Windows), preserving any
   provided distribution/auth settings. Use a non-PTY tool invocation with redirected
   stdin/stdout: the installer skips its interactive agent-selection setup when stdout is
   not a terminal. Do not allocate a TTY, run `qodo setup`, or install skill packages again.
   If the host requires a TTY, redirect installer stdout to a temporary log and inspect it.
   Honor execution-policy restrictions; do not bypass them. Stop if execution is denied.
6. Require installer success, rerun the standard user-scoped executable's `--version`, then
   return to the main skill's version gate and authentication step immediately. Installation
   is not login or readiness. Report checksum/download failures exactly; never run a failed
   download or continue after verification fails. Remove only temporary files you created.

## Old or unparseable runtime

Do not run whoami or login until the minimum CLI version in SKILL.md is met. Explain the
compatibility issue and use `<qodo> update`, which retains the runtime's recorded origin.
Proceed if the user's setup request covers this update; otherwise ask once. Keep customer
origins unchanged. Rerun the unadorned version probe after updating. If declined, failed or
still incompatible, stop without modifying the skill package or diagnosing an auth failure.

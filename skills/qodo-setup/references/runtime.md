# Runtime discovery and installation

Read when the CLI is missing, outdated, or the host uses PowerShell.
Keep the first working executable for the rest of setup; no extra PATH edits are needed.

## PowerShell discovery

The extensionless `bin/qodo` is POSIX-only. In PowerShell:

1. Use explicit `QODO_HOME/bin`; otherwise inspect absolute process PATH, Windows user
   PATH (`[Environment]::GetEnvironmentVariable('Path','User')`), then `$HOME/.qodo/bin`.
   Expand variables as data; do not edit PATH or search the workspace.
2. Resolve filesystem links before probing. Require existing, verifiable installation,
   entry point and executable targets outside every repository/workspace directory.
3. Try native `qodo.exe`, then native `node.exe` with the same installed `qodo.mjs`.
   Find Node with `Get-Command node.exe -CommandType Application`, or read existing absolute
   `.exe` paths from that installation's `qodo.cmd` NODE assignments (including conditional
   fallbacks) as text. Never execute `.cmd`, `.bat` or `.ps1` launchers.
4. Run unadorned `--version`; skip rejected/broken choices and keep the first working
   invocation. Unusable explicit `QODO_HOME` or no trusted invocation is a blocker before
   auth/reinstall; a working old version follows the main skill's update gate.

Reuse that invocation, installation and authenticated deployment across commands/tool calls.

## Missing runtime

Use the official installer; do not reconstruct the manifest/download/shim installation in
ad hoc code. The installer requires Node.js >=20.6.0 and verifies the CLI artifact against
the SHA-256 in its distribution's version.json before installing it under QODO_HOME
(default ~/.qodo). It also configures its launchers and shell PATH integration.

1. Resolve the distribution from this interaction and keep its installer URL, expected
   SHA-256 and distribution/auth settings together throughout installation, preserving
   any explicitly provided version or channel. For Qodo Cloud use these published,
   immutable installer pins. For a normal install, run the verified script without adding
   a selector; the installer chooses the distribution-approved version and reports it.
   For an explicitly requested exact version, pass `--version <version>` on POSIX or set
   `$env:QODO_INSTALL_VERSION = '<version>'` on PowerShell before executing the saved
   script. Only when a channel is explicitly provided, pass `--channel=<name>` on POSIX or
   set `$env:QODO_CHANNEL = '<name>'` on PowerShell. Do not combine an exact version with
   an explicit channel; clear a previously set selector before choosing the other.

   | Platform | Installer URL | Expected SHA-256 |
   | --- | --- | --- |
   | POSIX | `https://get.qodo.ai/installers/9dfe51a938ac0b7e193d03a1acc7d5f4d35a829efff6aff79b3fd4114f17d8ff/install.sh` | `9dfe51a938ac0b7e193d03a1acc7d5f4d35a829efff6aff79b3fd4114f17d8ff` |
   | PowerShell | `https://get.qodo.ai/installers/b0386d363d07e62384d099ddf41347f48cc1e80ed842c2916fb181c9356ed96e/install.ps1` | `b0386d363d07e62384d099ddf41347f48cc1e80ed842c2916fb181c9356ed96e` |

   For a customer deployment, use its exact installer URL and expected SHA-256 from the
   organization-provided installation instructions. Preserve QODO_INSTALL_BASE, the login
   endpoint and any explicitly supplied installer arguments. Do not fetch the public installer or apply
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
compatibility issue. Automatic updates stay within a major version: moving to a newer major uses
the checksum-pinned installation procedure above, preserving the recorded distribution origin.
For a normal install, let the verified installer choose the distribution-approved version.
Honor a requested exact version and keep it separate from channel selection; never silently
substitute a channel for it. For a customer installer, inspect the verified script and use
only selectors it supports, preserving the customer's origin and installation settings.
Proceed if the setup request covers installation; otherwise ask once. Keep customer origins unchanged. Rerun the unadorned version probe after updating. If declined, failed or
still incompatible, stop without modifying the skill package or diagnosing an auth failure.

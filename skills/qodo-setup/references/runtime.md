# Runtime discovery and installation

Read when the CLI is missing, outdated, or the host uses PowerShell.
Keep the first working executable for the rest of setup; no extra PATH edits are needed.

## PowerShell discovery

```powershell
$qodoRuntimeHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Join-Path $qodoRuntimeHome 'bin/qodo.cmd') --version
```

## Missing runtime

Use the official installer; do not reconstruct the manifest/download/shim installation in
ad hoc code. The installer requires Node.js >=20.6.0 and verifies the CLI artifact against
the SHA-256 in its distribution's version.json before installing it under QODO_HOME
(default ~/.qodo). It also configures its launchers and shell PATH integration.

1. Resolve the distribution from this interaction. For Qodo Cloud use
   `https://get.qodo.ai/install.sh` (POSIX) or `https://get.qodo.ai/install.ps1` (PowerShell).
   If an organization-specific installer, QODO_INSTALL_BASE or login endpoint was provided,
   preserve it. A known customer deployment without its installation instructions requires
   the administrator's exact command; never substitute the public distribution.
2. Check `node --version`. If missing or too old, explain the prerequisite and help the user
   install a supported Node version within their authorization before resuming setup.
3. Download the installer to a unique temporary file and read it before execution. Use the
   exact official URL above; no web search, guessed README URL, npm package or remote pipe
   into a shell is needed. For example, on POSIX:

   ```sh
   qodo_setup_dir=$(mktemp -d "${TMPDIR:-/tmp}/qodo-setup.XXXXXXXX") || exit 1
   curl --fail --silent --show-error --location https://get.qodo.ai/install.sh --output "$qodo_setup_dir/install.sh" || exit 1
   printf '%s\n' "$qodo_setup_dir/install.sh"
   ```

   Keep the returned absolute path across tool calls. On PowerShell use a temporary file
   ending in `.ps1` and `Invoke-WebRequest -Uri https://get.qodo.ai/install.ps1 -OutFile ...`.
4. Explain that you will run the official installer, which verifies the CLI download and
   writes the user-scoped runtime and PATH integration. A user who asked to set up Qodo
   has requested this installation; request only approvals still required by the host or
   a narrower user instruction. Inspect the downloaded script before requesting execution.
   Never invent a checksum or claim the installer script itself was checksum-verified
   merely because it verifies the CLI artifact.
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

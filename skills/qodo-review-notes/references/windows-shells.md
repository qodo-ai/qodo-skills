# Windows shells

Read before CLI notes commands in PowerShell or Git Bash on Windows. Keep the resolved
executable and authenticated deployment; do not install or switch accounts to work around a shell issue.

## PowerShell launcher

The extensionless `bin/qodo` is a POSIX script. Resolve a verified native invocation:

1. If `QODO_HOME` is configured, inspect that installation's `bin` directory. If it is
   unusable, report the blocker; do not silently select a different installation.
2. Otherwise inspect absolute directories from the process PATH in order, then Windows'
   persisted user PATH (`[Environment]::GetEnvironmentVariable('Path', 'User')`). Ignore
   empty or relative entries and expand environment variables as data, without executing
   them. Do not edit PATH or search the workspace.
3. Before any probe, resolve the real filesystem targets of the candidate directory,
   `qodo.exe`, `qodo.mjs`, and any Node fallback, including filesystem links. Reject targets
   inside the host's repository/workspace directories, even when PATH names an absolute
   directory outside them. Reject targets that cannot be verified. Apply this check to an
   explicit `QODO_HOME` too; never execute workspace files to discover a version.
4. An installation candidate contains an existing `qodo.mjs` plus either `qodo.exe` or
   `qodo.cmd`. Check files with `Test-Path -LiteralPath <path> -PathType Leaf`. Try a trusted
   native `qodo.exe` first. If absent or its probe fails, try that same installed `qodo.mjs`
   directly with verified Node. Inspect
   `Get-Command node -CommandType Application -ErrorAction SilentlyContinue` first. If that
   Node choice is absent, untrusted, or fails its probe, read the selected `qodo.cmd` as text
   and try existing absolute Node paths from its `set "NODE=..."` lines, applying the same
   trust/probe checks to each. An untrusted Node choice excludes only that invocation;
   it does not discard another trusted invocation for the installation. Do not execute
   the batch launcher to discover Node.
5. For each trusted candidate, run the unadorned `--version` probe with the executable,
   or Node followed by its installed entry point. Retain the first invocation that starts
   successfully and returns a parseable CLI version. Skip broken PATH candidates; if none
   works, check `(Join-Path $HOME '.qodo')/bin` with the same trust/probe checks. Custom roots
   need not set `QODO_HOME` when their installer registered a usable user PATH directory.
6. If no trusted native invocation works, report the launcher blocker; do not proceed to
   auth or reinstall. A selected older runtime follows the main skill's version/update gate.

Retain the selected installation, invocation and authenticated deployment for later commands.
If host shell state does not persist, recreate the invocation from that recorded installation;
do not rescan into a different installation. Do not execute `qodo.cmd`.

## Preserve the complete note document

Use `--args-file <absolute-path>` for the complete JSON argument object. Passing inline JSON
through `qodo.cmd` can lose content at newlines or expand `%NAME%`; PowerShell 5.1 also strips
embedded quotes. A file avoids those argument transformations without changing the note text.

Write JSON with the host's file-editing tool as UTF-8 without a byte-order mark. PowerShell 5.1
redirection, pipes, `Out-File` and `Set-Content` can add a BOM, write UTF-16 or replace Unicode.
If using PowerShell to write an already serialized JSON object, use an absolute task-owned path:

```powershell
[IO.File]::WriteAllText($notesArgsPath, $notesArgsJson, [Text.UTF8Encoding]::new($false))
```

Pass the file to the command from the live schema using the verified native invocation,
`--args-file <path>`, `--json`, and the retained `--idempotency-key` for that authorized request.
File input does not grant write permission; retain the same file and key for an identical retry.

Git Bash can use the normal launcher and the same JSON-file route. Structured JSON is not a
path argument, so its repository paths and Markdown do not undergo MSYS argument conversion.
Do not disable path conversion globally; the launcher depends on it.

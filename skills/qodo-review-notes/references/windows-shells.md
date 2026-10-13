# Windows shells

Read before CLI notes commands in PowerShell or Git Bash on Windows. Keep the resolved
executable and authenticated deployment; do not install or switch accounts to work around a shell issue.

## PowerShell launcher

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

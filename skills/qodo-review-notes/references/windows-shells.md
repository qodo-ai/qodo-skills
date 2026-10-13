# Windows shells

Read before CLI notes commands in PowerShell or Git Bash on Windows. Keep the resolved
executable and authenticated deployment; do not install or switch accounts to work around a shell issue.

## PowerShell launcher

The extensionless `bin/qodo` is a POSIX script. Resolve a native invocation before any CLI call:

1. Use `QODO_HOME` when configured, otherwise `Join-Path $HOME '.qodo'`.
2. Check `bin/qodo.exe` with `Test-Path -LiteralPath <path> -PathType Leaf`. If it exists,
   use it; it preserves arguments without cmd.exe. Never invoke a missing executable.
3. If it is absent, run the same installed `bin/qodo.mjs` directly with Node. Look for Node
   using `Get-Command node -CommandType Application -ErrorAction SilentlyContinue`. If absent
   from PATH, read the installed `bin/qodo.cmd` as text and select an existing absolute Node
   path recorded in its `set "NODE=..."` lines. Do not execute that batch launcher to discover Node.
4. Verify that the selected Node executable and `bin/qodo.mjs` exist before invoking them.
   If neither native invocation is usable, report the launcher blocker; do not proceed to auth.

Run the unadorned `--version` probe using that verified invocation: either the executable or
Node followed by the installed entry point. Retain it for every later CLI call. Recompute the
selection when the host does not preserve shell state. Do not execute `qodo.cmd` for notes commands.

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

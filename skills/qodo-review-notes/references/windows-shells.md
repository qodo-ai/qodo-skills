# Windows shells

Read before CLI notes commands in PowerShell or Git Bash on Windows. Keep the resolved
executable and authenticated deployment; do not install or switch accounts to work around a shell issue.

## PowerShell launcher

The extensionless `bin/qodo` is a POSIX script. Prefer the installed `bin/qodo.exe`,
which preserves arguments without cmd.exe. Resolve its configured home and probe it:

```powershell
$notesQodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
$notesQodo = Join-Path $notesQodoHome 'bin/qodo.exe'
& $notesQodo --version
```

Check that the executable exists before invoking it. If unavailable, invoke the same installed
`bin/qodo.mjs` directly with Node for the version probe and all later calls:

```powershell
$notesNode = (Get-Command node -ErrorAction Stop).Source
$notesEntry = Join-Path $notesQodoHome 'bin/qodo.mjs'
& $notesNode $notesEntry --version
```

If Node is not on PATH, use the Node path recorded as `NODE` in the installed `bin/qodo.cmd`;
do not execute that batch launcher for structured notes commands. Report an unavailable launcher
if neither path is usable. Retain the resolved invocation for every CLI call and recompute
variables when the host does not preserve shell state.

## Preserve the complete note document

Use `--args-file <absolute-path>` for the complete JSON argument object. Passing inline JSON
through `qodo.cmd` can lose content at newlines or expand `%NAME%`; PowerShell 5.1 also strips
embedded quotes. A file avoids those argument transformations without changing the note text.

Write JSON with the host's file-editing tool as UTF-8 without a byte-order mark. PowerShell 5.1
redirection, pipes, `Out-File` and `Set-Content` can add a BOM, write UTF-16 or replace Unicode.
If using PowerShell to write an already serialized JSON object, use an absolute task-owned path:

```powershell
[IO.File]::WriteAllText($notesArgsPath, $notesArgsJson, [Text.UTF8Encoding]::new($false))
& $notesQodo review-notes prepare-pr --args-file $notesArgsPath --json --idempotency-key $notesRequestKey
```

On the Node fallback, replace `& $notesQodo` with `& $notesNode $notesEntry`. Use the command
from the live schema and the retained key for that authorized request. File input does not grant
write permission; retain the same file and key for an identical retry.

Git Bash can use the normal launcher and the same JSON-file route. Structured JSON is not a
path argument, so its repository paths and Markdown do not undergo MSYS argument conversion.
Do not disable path conversion globally; the launcher depends on it.

# Windows shells

Read only for CLI commands on Windows.

## PowerShell launcher

Use native `qodo.exe` from explicit `QODO_HOME/bin`, otherwise a verified installed
executable. Resolve links outside repository/workspace directories before probing; never
execute `qodo.cmd`. Reuse the invocation and deployment. If unavailable/failed, follow the
launcher recovery linked from SKILL.md before authentication.

## Complete note documents

Use the live command's `--args-file <absolute-path>` with complete UTF-8 JSON without a BOM.
Write with the host file editor or:

```powershell
[IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))
```

Avoid PowerShell 5.1 redirection/pipes/`Out-File`/`Set-Content` (encoding loss) and inline JSON
(quote loss). Retain `--json` and the same file/idempotency key for identical authorized retries.
Git Bash can use its normal launcher and this file route; keep global path conversion enabled.

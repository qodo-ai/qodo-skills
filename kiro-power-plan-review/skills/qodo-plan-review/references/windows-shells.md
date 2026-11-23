# Windows shells

Read only for CLI commands in PowerShell or Git Bash on Windows.

## PowerShell launcher

Use native `qodo.exe` from explicit `QODO_HOME/bin`, otherwise a verified installed
executable. Resolve links outside repository/workspace directories before probing; never
execute `qodo.cmd`. Reuse the invocation and deployment. If unavailable/failed, follow the
launcher recovery linked from SKILL.md before authentication.

## PowerShell: arguments and JSON

Prefer advertised `--args-file` / `--context-file` for structured input. Write complete JSON
as UTF-8 without a BOM using the host file editor, or an absolute task-owned path:

```powershell
[IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))
```

PowerShell 5.1 redirection, pipes and `Out-File`/`Set-Content` can corrupt encoding; it also
strips embedded `"` from native arguments (escape these as `\"`). Preserve full text.

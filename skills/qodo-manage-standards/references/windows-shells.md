# Windows shells

Read only for CLI commands in PowerShell or Git Bash on Windows.

## PowerShell launcher

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

## PowerShell: arguments and JSON

Prefer advertised `--args-file` / `--context-file` for structured input. Write complete JSON
as UTF-8 without a BOM using the host file editor, or an absolute task-owned path:

```powershell
[IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))
```

PowerShell 5.1 redirection, pipes and `Out-File`/`Set-Content` can corrupt encoding; it also
strips embedded `"` from native arguments (escape these as `\"`). Preserve full text.

## Git Bash: scopes

Git Bash rewrites standalone `/owner/repo/` arguments. Attach named scope values with `=`:

```sh
MSYS2_ARG_CONV_EXCL='--scopes=' qodo read rules search --query "$QUERY" --scopes="$SCOPE" --json
```

Do not disable path conversion globally; the launcher needs it.

For an authorized scope write, complete JSON preserves numeric IDs and embedded paths:

```sh
qodo rules set-scope --args '{"rule_ids":[123],"scopes":["/a/b/","/c/d/"],"dry_run":true}' --json
```

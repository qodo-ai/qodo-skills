# Windows shells

Read when commands run in PowerShell or Git Bash (MSYS2; `uname -s` starts with `MINGW` or
`MSYS`) on Windows. Each section names its shell; the skill's POSIX examples otherwise apply.

## PowerShell: launcher

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

## PowerShell: argument values

cmd.exe can truncate multiline values and reparse `%NAME%`, `&` and `^`. The verified native
invocation avoids that batch-shell parsing. Windows PowerShell 5.1 also strips embedded `"`
from arguments to programs; write each as `\"` there. For structured arguments, prefer the
CLI's advertised file input (`--args-file` for managed-tool arguments or `--context-file` for
review context) and follow the JSON-file encoding guidance below. Never shorten a query,
explanation or example to avoid shell limits; pass its full text or report the blocker.

## PowerShell: JSON files

`qodo` rejects a JSON file that starts with a byte-order mark. In Windows PowerShell 5.1, `>`,
`Out-File`, `Set-Content` and pipes add one, write UTF-16, or replace non-ASCII text. Write
context JSON with the host's file-editing tool or `[IO.File]::WriteAllText($path, $json)` with an
absolute `$path` such as `(Join-Path $PWD '.qodo/session-context.json')` (.NET ignores
`Set-Location`), creating its directory first, then pass `--context-file <path>`; do not pipe it
to `--context-file -`.

## Git Bash: values starting with `/`

Git Bash rewrites a whole argument that starts with `/` into a Windows path before `qodo` sees
it: `/owner/repo/` arrives as `C:/Program Files/Git/owner/repo/`. A scoped search then silently
returns nothing and a write stores the wrong scope. Attach the value with `=` and exclude that
flag from conversion:

```sh
MSYS2_ARG_CONV_EXCL='--scopes=' qodo read rules search --query "$QUERY" --scopes="$SCOPE" --json
qodo rules set-scope --args '{"rule_ids":[123],"scopes":["/a/b/","/c/d/"],"dry_run":true}' --json
```

Use the exclusion for every named `--scopes` flag. The set-scope example uses complete JSON
so `rule_ids` retains its integer-array type; embedded scope paths are not rewritten. Its
`dry_run` requests a preview; use this write tool only under the skill’s approval rules.
Separate several flags with `;`, e.g. `MSYS2_ARG_CONV_EXCL='--scopes=;--pattern='`. Never set
`MSYS_NO_PATHCONV=1`: the `qodo` launcher itself depends on path conversion.

# Windows shells

Read when commands run in PowerShell or Git Bash (MSYS2; `uname -s` starts with `MINGW` or
`MSYS`) on Windows. Each section names its shell; the skill's POSIX examples otherwise apply.

## PowerShell: launcher

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
selection when the host does not preserve shell state. Do not execute `qodo.cmd` for these commands.

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
MSYS2_ARG_CONV_EXCL='--scopes=' qodo rules set-scope --rule-ids 123 --scopes="/a/b/","/c/d/" --json
```

Use this form for every `--scopes`, including `rules create`, `update`, `set-scope` and `bulk`.
Separate several flags with `;`, e.g. `MSYS2_ARG_CONV_EXCL='--scopes=;--pattern='`. Never set
`MSYS_NO_PATHCONV=1`: the `qodo` launcher itself depends on path conversion.

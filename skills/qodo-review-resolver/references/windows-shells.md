# Windows shells

Read when commands run in PowerShell or Git Bash (MSYS2; `uname -s` starts with `MINGW` or
`MSYS`) on Windows. Each section names its shell; the skill's POSIX examples otherwise apply.

## PowerShell: launcher

Bare `qodo` resolves to `bin/qodo.cmd`, which runs through cmd.exe. The extensionless
`bin/qodo` is a POSIX script PowerShell cannot execute; never call it there. When `qodo` is
not on PATH, use the following, recomputing `$qodoHome` in each command because host shell
state may not persist:

```powershell
$qodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Join-Path $qodoHome 'bin/qodo.cmd') --version
```

## PowerShell: values containing a newline, `%` or `"`

cmd.exe cuts an argument at its first newline, silently dropping every later flag including
`--json`, and replaces `%NAME%` with that environment variable's value. For a command with such
a value, bypass cmd.exe by running the CLI's Node entry point with the same arguments:

```powershell
$qodoHome = if ($env:QODO_HOME) { $env:QODO_HOME } else { Join-Path $HOME '.qodo' }
& (Get-Command node -ErrorAction Stop).Source (Join-Path $qodoHome 'bin/qodo.mjs') <arguments>
```

If `node` is not on PATH, use the Node path that `bin/qodo.cmd` sets as `NODE`. For an npm global
install (`npm i -g @qodo/cli`), use `Join-Path (npm prefix -g) 'node_modules/@qodo/cli/dist/qodo.mjs'`
instead of `bin/qodo.mjs`.
Windows PowerShell 5.1 (`$PSVersionTable.PSVersion.Major` is 5) also strips embedded `"` from
arguments to any program; write each as `\"` there. Never shorten a query, explanation or
example to avoid these limits; pass its full text or report the blocker.

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

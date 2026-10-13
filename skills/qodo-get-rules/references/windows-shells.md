# Windows shells

Read when commands run in PowerShell or Git Bash (MSYS2; `uname -s` starts with `MINGW` or
`MSYS`) on Windows. Each section names its shell; the skill's POSIX examples otherwise apply.

## PowerShell: launcher

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
   `qodo.cmd`. Check files with `Test-Path -LiteralPath <path> -PathType Leaf`. Use its native
   `qodo.exe` when available; otherwise run that same installed `qodo.mjs` directly with
   verified Node. Resolve Node with
   `Get-Command node -CommandType Application -ErrorAction SilentlyContinue`. If absent,
   read the selected `qodo.cmd` as text and use an existing absolute Node path from its
   `set "NODE=..."` lines. Do not execute the batch launcher to discover Node.
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

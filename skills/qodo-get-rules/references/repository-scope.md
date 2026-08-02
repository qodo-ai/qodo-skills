# Repository Scope Detection

The skill detects the repository scope from the git `origin` remote URL and passes it to the search API as the `scopes` field. This narrows results to rules that are relevant to the specific repository, improving retrieval precision.

## Git Repository Check

```bash
# Must be inside a git repository
git rev-parse --is-inside-work-tree
```

Exit code is non-zero (128) if not in a git repository. If not in a git repo, inform the user and exit gracefully.

## Scope Extraction

After confirming a git repository, extract the scope from the `origin` remote:

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
```

### URL Format Handling

| Remote format | Example | Parsed `REPO_PATH` |
|---|---|---|
| HTTPS | `https://github.com/org/repo.git` | `org/repo` |
| HTTP | `http://git.internal/org/repo` | `org/repo` |
| SSH (scp-like) | `git@github.com:org/repo.git` | `org/repo` |
| SSH (URL) | `ssh://git@github.com/org/repo.git` | `org/repo` |
| Git protocol | `git://host/org/repo` | `org/repo` |
| With credentials | `https://user:token@github.com/org/repo` | `org/repo` |
| GitLab subgroup | `https://gitlab.com/group/subgroup/repo` | `group/subgroup/repo` |
| Azure DevOps | `https://dev.azure.com/org/proj/_git/repo` | `org/proj/_git/repo` |

A trailing slash is stripped first, then a `.git` suffix — in that order, since
`${url%.git}` only removes an exact final suffix and would leave `.git` in place on
`https://host/org/repo.git/`. The resulting scope path is `/<REPO_PATH>/`.

A `file://` remote is a local clone with no hosted org/repo path, so it yields no scope.

**Keep the full path after the host** — do not collapse to two segments. GitLab subgroups and
Azure DevOps paths are legitimately deeper than `org/repo`.

A path with no `/` (a single segment), an absolute path, or a Windows path yields no scope —
see [Graceful Degradation](#graceful-degradation).

### Portability

Parse with POSIX parameter expansion and `case`, **not** `sed` or `grep`.

`\?`, `\+`, and `\|` in a basic regex are GNU extensions. BSD `sed` (macOS) does not support
them and — critically — does not error: the substitution simply matches nothing, exits `0`,
and passes the input through unchanged. BSD `grep` *does* honor `\?` in a BRE, so a
`grep -q "^https\?://"` guard in front of a `sed 's|^https\?://[^/]*/||'` passes while the
`sed` silently no-ops, and the whole remote URL becomes the scope path. That produced a
nonsense scope like `/https://github.com/org/repo/` on every macOS run and measurably degraded
retrieval, with no error anywhere.

If a regex is genuinely needed, use `sed -E` (ERE) — `?`, `+`, and `|` are portable there.
For this parse no regex is needed at all.

### Module-Level Scope

If the current working directory is inside a `modules/<name>/` subdirectory of the repository root, the scope is narrowed to that module:

```
/org/repo/modules/<name>/
```

Otherwise the repository-wide scope `/org/repo/` is used.

Detection:

```bash
# --show-prefix is the cwd relative to the repo root: "" at the root,
# "modules/billing/src/" deeper in. Portable, and no subprocess beyond git.
PREFIX=$(git rev-parse --show-prefix)
MODULE=""
case "$PREFIX" in
  modules/*/*)
    MODULE="${PREFIX#modules/}"
    MODULE="${MODULE%%/*}"
    ;;
esac

if [ -n "$MODULE" ]; then
  SCOPE="/${REPO_PATH}/modules/${MODULE}/"
else
  SCOPE="/${REPO_PATH}/"
fi
```

`git rev-parse --show-prefix` replaces `realpath --relative-to=` here. That flag is GNU
coreutils only — BSD `realpath` rejects it — so the old snippet fell through to a `python3`
subprocess on every macOS invocation, with the real error hidden by `2>/dev/null`.

## Graceful Degradation

Scope is **optional**. If scope cannot be determined for any reason, the skill proceeds without it — org-wide semantic search still returns relevant results.

Skip scope and proceed without error when:
- No `origin` remote is configured
- Remote URL cannot be parsed into an org/repo path — no `/` after the host (a single
  segment), a local absolute path, a `file://` clone, or a Windows path
- Any other unexpected failure during extraction

Do not send `"scopes": null` or `"scopes": []` — omit the `scopes` field entirely from the request body.

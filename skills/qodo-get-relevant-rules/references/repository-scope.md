# Repository Scope Detection

The repository scope is used to identify the caller's context for audit/logging purposes. For `qodo-get-relevant-rules`, the primary retrieval mechanism is semantic search — the scope is not used as a filter parameter in the `/rules/search` call.

## Extracting Scope from Git Remote URL

Parse the `origin` remote URL to derive the scope path. Both URL formats are supported:

- SSH: `git@github.com:org/repo.git` → `/org/repo/`
- HTTPS: `https://github.com/org/repo.git` → `/org/repo/`

**If no remote is found:** Exit silently — there is nothing to log.

**If the URL cannot be parsed:** Inform the user and exit gracefully.

## Commands

```bash
# Check if inside a git repository
git rev-parse --is-inside-work-tree

# Get remote URL
git remote get-url origin
```

Exit code from `git rev-parse` will be non-zero (128) if not in a git repository.

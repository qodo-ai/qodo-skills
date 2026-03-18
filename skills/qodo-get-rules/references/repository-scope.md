# Repository Scope Detection

The only requirement is that the current directory is inside a git repository. The repository scope (org/repo path) is not used as a query parameter — the search endpoint handles relevance via semantic matching.

## Git Repository Check

```bash
# Check if inside a git repository
git rev-parse --is-inside-work-tree
```

Exit code from `git rev-parse` will be non-zero (128) if not in a git repository. If not in a git repo, inform the user and exit gracefully.

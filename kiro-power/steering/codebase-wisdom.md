# Qodo Codebase Wisdom

Load this steering file when the user needs to **understand code, its history, or cross-repo coupling** — "how does X work", "where is X defined", "who changed X", "explain this service", "what would changing X affect", "which repos depend on X", "has this been fixed before" — **especially for repos not checked out locally or work spanning repos**.

This delegates to the **Qodo CLI** managed read tools. Once this capability is selected, it **reads and cites through Qodo; it never edits code or posts to the forge**, including for a repository already checked out locally. **Not for loading the workspace's Qodo rules — that's the get-rules capability.**

## UX and Safety Rules

- Use only the named Qodo leaves whose current catalog entry is explicitly `mutating: false`. **Never call approval, comment, label, description-update, or other mutating tools** — they write to the forge. Do not infer safety from help prose alone.
- **Let the CLI resolve the repo** — it autodetects `owner/repo` from `origin`; don't run `git remote` / `git branch` to figure it out, and don't bypass this capability with local source-file pre-reading.
- No raw JSON dumps, no secrets. Deliver **cited findings**, bottom line first.
- On `MT-TOOL-LOOP`: stop and change approach, don't retry.

## Locate the CLI + auth (shared)

The CLI requires **Node.js ≥ 20**. `qodo` may be "command not found" — use `~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo`); missing there too → install `curl -fsSL https://get.qodo.ai/install.sh | sh`.

Run `qodo whoami --json` first without surfacing its raw output; on failure, tell the user to run `qodo login` and stop. Inspect `qodo tools --json` internally before the first call and use only the named leaves below when their entries are `mutating: false`. If authenticated discovery is missing/stale, refresh once and retry once; otherwise stop.

## Workflow

1. **Resolve the repo through Qodo.** Inside the target repo, omit `--repo` and let the CLI autodetect from `origin`. Otherwise: named repo → `--repo owner/repo`; a differently-named or not-checked-out repo → `qodo codebase search-repos --query "<name>" --json` first — **never guess a slug** (multiple matches → ask the user; zero → say so and stop).
2. **Route to a tool group.** Use `qodo <group> --help` to list leaves, `qodo <group> <tool> --help` for that leaf's exact flags, and `qodo --help` for global `--json`. Confirm `mutating: false` through `qodo tools --json`; never pass `--idempotency-key` in this read capability.
   - **Current code** — where/what/how it works now → `qodo codebase <tool>`: `search-repos`, `grep`, `find`, `ls`, `read-file`, `blame`, `list-commits`, `get-commit`, `list-prs`, `get-pr`, `list-issues`, `get-issue`.
   - **History / prior art** — how a change was done before, a file's PR history, similar past work → `qodo pull-request <tool>`: `stats`, `similar`, `by-file`, `details`, `patch`. (Merged PRs only.)
   - **Impact / coupling** — what a change affects, which repos depend on this → `qodo cross-repo <tool>`: `overview`, `relations`, `pair`.
3. **Narrow, then fetch.** Cheap discovery before heavy pulls: **orient** (`search-repos`; `pull-request stats`; `cross-repo relations`) → **locate** (`grep`/`find`/`blame`/`list-commits`; `pull-request similar`/`by-file`) → **read** (only then `read-file` with `--start-line`/`--limit-lines`, `get-pr`, `pull-request details`/`patch`).
4. **Deliver.** Bottom line in plain language first, then code/paths/diffs. **Cite everything** — repo, `path:line`, PR #, commit SHA; if a fact has no locatable source, say so — don't invent a citation. Present code (`read-file`) trumps history (`pull-request`) when they disagree. Empty or `truncated` result → narrow once and retry (tighter query/path/repo) before concluding; still empty → "not found in <scope>", don't overclaim.

A short, well-cited result is a confidence signal; padding with uncited detail is noise.

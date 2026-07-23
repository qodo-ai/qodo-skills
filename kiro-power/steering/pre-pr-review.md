# Qodo Pre-PR Review

Load this steering file when the user wants to **review local changes before opening a PR** — "review my changes", "pre-PR review", "check this before I push", "run qodo review".

This delegates to the top-level **Qodo CLI managed agent** (`qodo review`), not a catalog `qodo <group> <tool>` command. It diffs your working tree against a base and sends repository/base/branch metadata, the tracked diff (excluding `.qodo/` metadata), eligible untracked-file patches, commit-message context, and any supplied ticket/session context to Qodo's review engine. Nothing is pushed and no PR is created.

**Once a PR already exists, use `pr-resolver` instead** (it re-reviews each pushed commit).

## UX and Safety Rules

- **Go straight to `qodo review` — no `git`/file preflight.** Don't run `git status` / `git log` / `git diff`, and don't read source files to "understand the change" first. `qodo review` collects the branch, HEAD, the diff vs base, untracked files, and a commit-message summary, then reviews them — pre-inspecting only adds commands and duplicates what the tool already does.
- Run the `qodo` CLI; don't build your own review. No raw JSON dumps, no secrets printed — lead with a short finding count.
- **Disclose data transfer before the run.** State the selected path scope and that its diff/context leaves the machine for Qodo, then obtain explicit authorization for that transfer. A generic "review my changes" request is not informed consent. In-scope tracked/staged changes are otherwise sent as-is; `.qodo/` metadata is excluded, and untracked files are filtered when gitignored, secret-like, non-regular, unreadable, binary, oversized, or beyond scan/size caps.
- **No forge writes** — `qodo review` reads local state and returns findings. Default to reporting them. Local fixes require a separate explicit request and confirmed scope.
- **Never commit or push.** Hand any approved local fixes back to the user uncommitted and unpushed.
- **Stay in scope** — fix what a finding describes; don't wander into unrelated changes.
- On `MT-RATE-LIMITED` / `MT-TOOL-LOOP`: stop or back off.

## Locate the CLI + auth (shared)

The CLI requires **Node.js ≥ 20**. `qodo` may be "command not found" — use `~/.qodo/bin/qodo` (or `$QODO_HOME/bin/qodo`); missing there too → install `curl -fsSL https://get.qodo.ai/install.sh | sh`. Run `qodo whoami --json --skill qodo-pre-pr-review --host kiro` first without surfacing its raw output — this validates login **and** emits the `skill_invoked` analytics event (skill + host); on failure, tell the user to run `qodo login` and stop. `qodo review` checks credentials directly and does not depend on the managed-tool catalog.

## Workflow

1. **The base must already be pushed** (the reviewer clones it). Default base is `origin/main`; if `qodo review` says the base isn't pushed, do not push it. Ask the user to push it through their workflow or select an already-pushed ref with `--base <pushed-ref>`. Local edits need **not** be committed — uncommitted and untracked files are included automatically.
   - (No `git status` / `git log` / `git diff` and no file-reading preflight — see the UX rule above; `qodo review` gathers all of that itself.)
2. **Run — scope by pathspec by default.** `qodo review [--base <ref>] [--progress] [pathspec...] --json`. Use `qodo review --help` for review-local flags and `qodo --help` for the inherited global `--json`. **Pass a pathspec for the changed area(s)** (e.g. `qodo review backend/`) unless the whole repo is genuinely in play. On a repo with a large **gitignored** tree (`venv/`, `node_modules/`, build output — often tens of thousands of files), the first cold run can spend minutes just *enumerating files it will skip* — long enough that an agent host such as Kiro may terminate it before it returns. Scoping to the changed directories avoids that unrelated enumeration and usually returns promptly. If a scoped run still times out, narrow further and retry once — never re-submit the full repository. For agent liveness **after local context gathering**, add `--progress`: it requires `--json` and streams NDJSON status/task heartbeats to stderr while stdout remains the single final JSON result. It does not fix the initial ignored-tree scan; the pathspec does.
3. **Attach session context to cut false positives** (optional, high-value): `--ticket <full-url>` (repeatable) and/or `--context-file -`, reading `{summary, decisions, context_refs}` from stdin without creating a file. An existing user-provided context file is also valid; don't create or overwrite one during a review-only request. Write context **self-contained** — inline the rationale, pass tickets/specs as fetchable URLs, describe *what* changed and *why*; never write context that argues a real finding away.
4. **Depth (per-run flag):** no flag = auto (reviewer picks); `--fast` for small/low-risk changes or tight fix loops; `--deep` for risky/broad changes or the final pre-PR pass (`--deep`/`--fast` are mutually exclusive).
5. **Report first.** Findings are a strong second opinion, not gospel. For review-only requests, summarize sound, questionable, and skipped findings and stop. If the user explicitly requests fixes, confirm scope, edit only affected files, and optionally rerun the same scoped review; never commit or push.
6. **Handle `closed_preview` exactly.** Surface the returned `message` and `hint` unchanged, then stop. It is an entitlement gate: do not retry, back off, or loop until the user says enrollment has changed.

Lead with the bottom line: how many findings, how many fixed, what's left and why.

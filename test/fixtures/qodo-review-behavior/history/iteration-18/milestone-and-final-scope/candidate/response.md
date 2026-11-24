I loaded the qodo-review skill and planned each scenario. Nothing was run. The installed CLI has no `--target`, so scenarios 1–7 pass the verified merge-base explicitly as `--base 1111111111111111111111111111111111111111`. Each context file goes outside the repo (for example `$TMPDIR/qodo-ctx-<scenario>.json`) so it never ends up in a reviewed diff or commit. Each file has `decisions`, `notes` and `recent_work`.

### 1. `milestone`: submit an ordinary checkpoint in the background and keep working
- **Why review now:** the slice is coherent, tested and not yet reviewed. Feedback can still shape the integration work that remains.
- **Effort:** default auto. Omit `--fast` and `--deep`, because you asked for no special effort.
- **Command:**
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --async --json --context-file "$TMPDIR/qodo-ctx-milestone.json"
  ```
- **Context:**
  - `decisions`: the API design choices, marked as yours or mine.
  - `notes`: requirements, guards, unchanged callers, and which tests ran. Results go in only as reported; "tested" doesn't mean "passed".
  - `recent_work`: the substantive work in this slice.
- **After submitting:**
  - Save the operation ID along with the base, commit/tree, scope and context.
  - Carry on with the integration work.
  - At a natural pause, collect with `qodo review status <id> --json`. Polling isn't a new review, and only one checkpoint stays active.

### 2. `dirty-final`: review the committed candidate from the clean worktree
- **Scope:** ordinary capture in the main worktree would pick up the unrelated staged, unstaged and untracked edits. Help shows no committed-only option, so I'd use the verified task-only clean worktree at the intended commit.
- **Command:** run from that worktree, auto effort, because this is a final review:
  ```sh
  cd <clean-worktree> && qodo review --base 1111111111111111111111111111111111111111 --async --json --context-file "$TMPDIR/qodo-ctx-dirty-final.json"
  ```
- **What I'd leave alone:** no reset, stash or commit of your other edits. The original working files and the index stay exactly as they are.
- **Checks on the result:**
  - Confirm the reviewed commit matches the intended SHA.
  - Check the exclusions and omissions, and that coverage is complete.
- **Context:** the full PR intent, decisions, verification, and a note that the review ran from an isolated clean checkout.

### 3. `already-covered`: don't run another review
- **Why:** completed auto coverage already exists for this exact snapshot, base, scope and policy. Findings are settled and tests passed. Nothing changed and there's no new evidence or request, so another run adds nothing.
- **Handoff:** I'd report **Ready locally**. Creating or updating a PR, hosted Qodo review (`qodo-review-resolver`) and CI remain separate steps.

### 4. `trivial`: don't run a review
- **Why:** a typo fix in an internal comment changes no behavior, and you didn't ask for a review. I'd keep going with the task.
- **Later:** the fix gets covered whenever the full intended change has its final review.

### 5. `report-only`: review the working scope, report, then stop
- **Command:** auto effort, ordinary working-tree capture, no commits:
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --async --json --context-file "$TMPDIR/qodo-ctx-report.json"
  ```
- **Collecting:** poll the operation ID until it completes.
- **Reporting:**
  - Coverage, then the `introduced` and `still_open` findings, each with impact, my assessment and a recommendation.
  - `resolved` and `dismissed` listed separately.
- **Then stop:** no edits, no commits, and no offer to turn this into a fix task. Any local-to-PR limitation is reported separately.

### 6. `light-to-final`: yes, run an ordinary auto review
- **Why:** a `--fast` checkpoint on its own doesn't count as final coverage. That gap is the concrete reason for another assessment, and you asked for one.
- **Command:** same base and full scope, no `--fast`, no `--deep`, no `--full`:
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --async --json --context-file "$TMPDIR/qodo-ctx-final.json"
  ```
- **Reuse:** the Engine decides whether it can reuse the light evidence. I'd report the mode it returns (`full`, `incremental` or `reused`) and any fallback.
- **Context:** `recent_work` should say honestly that no code changed since the fast checkpoint, and that this run is the upgrade to ordinary final coverage.

### 7. `explicit-fresh`: honor the `--full` request
- **Why:** you explicitly asked for a fresh assessment, it's within budget, and that's the case `--full` exists for.
- **Command:** effort stays auto:
  ```sh
  qodo review --base 1111111111111111111111111111111111111111 --full --async --json --context-file "$TMPDIR/qodo-ctx-fresh.json"
  ```
- **Context:** note that nothing changed and this run was user-requested. The existing settled findings and dismissal reasons are reused from the stored results rather than re-entered by hand.
- **Budget:** this run counts against your review budget.

### 8. `stacked`: newer CLI with `--target`
- **Fetch first:** `git fetch origin parent`.
- **Diff base:** `git merge-base HEAD origin/parent`, the point where the child diverged. It is **not** the parent tip, which has moved on, and it is not `main`.
- **Target:** `parent`, which is also what links the review to the PR. A SHA doesn't identify a branch, so I wouldn't also pass `--base`. An exact base skips target selection and could stop the PR from linking.
- **If the child has one open same-repo PR:**
  - Either omit both flags so the CLI discovers the target, or pass it explicitly. Since you asked for a specific stack layer, I'd make the choice explicit:
    ```sh
    qodo review --target parent --async --json --context-file "$TMPDIR/qodo-ctx-child.json"
    ```
  - Then confirm the reported target is `parent` and the diff covers only the child's commits.
- **If the CLI reports two possible targets:**
  - I'd stop and ask you which one you mean.
  - I wouldn't guess, and I wouldn't fall back to `main` or the parent tip.
  - After your answer I'd retry once with `--target <chosen-branch>`, keeping the same scope, context and effort.
I loaded the qodo-review skill and nothing was run. Each command below uses `qodo` to stand for the installed invocation you already resolved. `BASE` means the merge-base SHA `1111111111111111111111111111111111111111`. I'd write each context file outside the reviewed tree, for example `$TMPDIR/qodo-ctx-<case>.json`, so it never ends up in the diff or a commit.

---

### 1. `milestone`: submit one auto checkpoint in the background, keep working

**Reason to review:** you finished and tested a coherent slice, and its findings can still shape the integration work left to do.

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-milestone.json" --async --json
```

- **Effort:** auto. I'd leave out `--fast` and `--deep` because you asked for neither.
- **Scope:** no path limits. The worktree is clean, so ordinary capture is exactly the task commit.
- **Context:**
  - `decisions`: the API design choices, each with who made it (you or me) and the reason, if known.
  - `notes`: requirements, guards and their file locations, callers that didn't change, and the exact checks run with their results. "Tested" alone isn't recorded as "tests passed"; any result I don't have is marked unknown.
  - `recent_work`: "First review: implemented the API slice …"
- **Afterwards:** save the `operation_id` and keep doing the integration work. At a natural pause, collect the result with `qodo review status <id> --json`. Exit 2 means it's still running; I'd wait the returned `retry_after` and check again. I wouldn't submit a second review while this one is active.

### 2. `dirty-final`: review the verified clean task-only worktree

Ordinary capture in your main worktree would pull in the unrelated staged and unstaged edits and the scratch file. I'd leave that worktree and its index alone: no stash, reset or commit.

```sh
cd /path/to/verified-clean-worktree          # at the intended commit
git merge-base HEAD origin/main              # confirm it equals 1111…1111
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-dirty-final.json" --async --json
```

- **Effort:** auto, full intended path scope.
- **Context:** the same three fields. `notes` would say the review ran in an isolated clean checkout of commit `<sha>`, and that unrelated local edits were left out on purpose.
- **Checking coverage:** the result's commit and tree should match the intended commit. I'd also check for exclusions or omissions before treating it as covering the PR candidate.

### 3. `already-covered`: no new review

There's no concrete reason to run another: nothing changed, there's no new evidence, and you didn't ask for a fresh assessment. I'd report **Ready locally**. The completed auto assessment covers the exact commit, tree, base, scope and policy; required findings are settled; and tests passed. I'd report two things separately: whether findings and checkpoints were stored, and the local-to-PR handoff. A hosted "Qodo-clean" claim would still need a separate check with `qodo-review-resolver`. CI and merge are their own gates.

### 4. `trivial`: no review

A comment typo with no behavior change doesn't warrant a review on its own. I'd keep working and mention the fix in `recent_work` on the next meaningful submission.

### 5. `report-only`: review the working scope, no edits or commits

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-report.json" --json
```

- **Scope:** ordinary capture, which covers uncommitted changes and eligible untracked files. That's what you asked for. I'd create no commits.
- **Context file:** it stays outside the repository, so I don't touch `.qodo/` or the ignore files.
- **Effort:** auto.
- **Afterwards:** I'd assess each finding against the code and then stop. No fixes, no stored dismissals, and no offer to switch to implementation.

### 6. `light-to-final`: yes, one auto final review

**Reason to review:** a `--fast` checkpoint doesn't count as ordinary final coverage, and you're about to hand off.

```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-final.json" --json      # or --async --json, then poll
```

- **Effort and scope:** auto, with `--fast` dropped. Same base and the same full scope as the checkpoint.
- **No `--full`:** the earlier checkpoint completed, and you didn't ask for a fresh run. I'd let the service decide whether to report `full`, `incremental` or `reused`, and pass on what it reports.
- **Context:** `recent_work` would say no code changed since the `--fast` checkpoint and that this run upgrades it to ordinary final coverage. Open findings from the checkpoint stay listed as backlog, not as new findings.

### 7. `explicit-fresh`: honor `--full`

**Reason to review:** you explicitly asked for a fresh assessment, and it's within your budget.

```sh
qodo review --base 1111111111111111111111111111111111111111 --full \
  --context-file "$TMPDIR/qodo-ctx-fresh.json" --json
```

- **Effort and scope:** auto, same base and full scope.
- **Context:** `recent_work` would say no code changed and you requested a fresh assessment.
- **Budget:** this run counts against your review budget.
- **Results:** findings marked `introduced` are reported separately from earlier settled ones.

### 8. `stacked`: review only the child layer

**Diff base:** the child's fork point on the fetched parent, not the parent tip and not `main`.

```sh
git fetch origin parent
CHILD_BASE="$(git merge-base HEAD origin/parent)"   # old fork point, because parent advanced
```

- **Why the fork point:** using the advanced parent tip would show the parent's new commits as reverted changes. Using `main` would pull in the whole parent layer.
- **Checks before submitting:** `CHILD_BASE` must still be reachable on the remote parent's history. If the parent was rebased or force-pushed and the old fork point is gone from the remote, I'd stop rather than substitute the tip.
- **No rebasing:** I wouldn't rebase the child onto the new parent tip or push anything.

**Target identity:** I'd first read `qodo review --help` to confirm what `--target` means on that version.

- **One open same-repository PR:** its base branch is the target. I'd confirm it really is `parent`, not `main`, and then run:
  ```sh
  qodo review --base "$CHILD_BASE" --target <that PR's base branch, as help specifies> \
    --context-file "$TMPDIR/qodo-ctx-child.json" --async --json
  ```
  `notes` would describe the stack (child → parent → main) and say the review covers only the child layer.
- **CLI reports two possible targets:** I'd stop before submitting. I'd show you both candidates and ask which one this child layer should be reviewed against. I wouldn't pick one myself or default to `main`. Once you choose, `--base` stays `CHILD_BASE` and `--target` names the branch you chose.
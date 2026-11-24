Below is the plan for each scenario. Nothing was run. Some things apply to all of them:

- **Command:** `qodo` is the installed command, already checked. The version and identity checks are done, so I don't repeat them.
- **Base:** this CLI's help doesn't list `--target`. So for scenarios 1–7 I pass the merge-base SHA directly as `--base 1111111111111111111111111111111111111111` on every run. The catch is that the review may not get linked to a PR, and I'd tell you that.
- **Effort:** I use the default (auto), meaning I leave out both `--fast` and `--deep`, unless a scenario says otherwise.
- **Context file:** I write the session notes to a JSON file outside the repo, e.g. `"$TMPDIR/qodo-ctx-<task>.json"`, so it never ends up in the reviewed changes. It has three fields:
  - `decisions`: what was chosen, who chose it (you or me), and why.
  - `notes`: requirements, existing guards, callers, which checks ran and their actual results, and anything still uncertain.
  - `recent_work`: what changed since the last review.
- **Tracking:** I keep each operation ID along with the base, commit/tree, scope and context it was run with.

---

**1. `milestone`: review now, in the background, and keep working**
This is a finished, tested slice that hasn't been reviewed, and feedback can still shape the integration work. That makes it a good checkpoint.
```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-milestone.json" --async --json
```
- **Context:** `recent_work` describes the API slice as the first substantive work up for review. `notes` lists the tests you actually ran and whether they passed; if I don't know a result, I record it as unknown rather than "passed". It also lists the integration work still to do as a known non-goal for now.
- **Scope:** the worktree is clean, so a normal capture is the task commit and nothing else.
- **Next:** continue the integration work. I'd collect the result at a natural pause with `qodo review status <id> --json` and not start a second review while this one is running.

**2. `dirty-final`: review from the clean task-only worktree**
A normal capture in your main checkout would pick up the unrelated staged and unstaged edits and the untracked scratch file. So I don't touch that checkout at all: no stash, reset or commit, and the index stays as it is.
```sh
git -C <clean-worktree> rev-parse HEAD   # must equal the intended PR commit
git -C <clean-worktree> status --porcelain   # must be empty
cd <clean-worktree> && qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-final.json" --async --json
```
- **Effort:** auto. It's a final review, but that alone doesn't justify `--deep`.
- **Context:** `notes` says this is a final review of the committed PR candidate, gives the HEAD SHA, and lists test results. `recent_work` covers anything changed since the last review.
- **After the run:** check that the result's commit/tree matches the intended commit, and review any reported exclusions.

**3. `already-covered`: don't review again**
A completed auto review already covers this exact snapshot, base, scope and policy. The full set of findings is settled, tests passed, and nothing has changed, so another run has no concrete reason.
- **Status:** I report it as **ready locally** and hand the work over.
- **Kept separate:** PR or hosted Qodo review state (that's the `qodo-review-resolver` skill), CI, merge and deployment are separate checks. I don't claim any of them.

**4. `trivial`: don't review**
A comment typo with no change in behavior doesn't warrant an automatic review. I keep working. The fix will be part of the snapshot covered by the next useful review or the final review.

**5. `report-only`: review the working changes, no edits or commits**
```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-report.json" --async --json
```
- **Scope:** the normal working-tree capture is exactly what you asked for. I don't commit anything first.
- **Context:** `notes` states that the review covers uncommitted working changes, that this is report-only, and what verification you actually ran.
- **Next:** poll with `status <id>`, then check the result's coverage. For each finding I explain the impact, my assessment against the code, and a recommended action. Then I stop: no edits, and I don't ask to switch to implementing fixes.
- **Caveat:** I note that this reviews your local working state, not a commit or PR.

**6. `light-to-final`: yes, run an ordinary review**
- **Reason:** a `--fast` checkpoint on its own doesn't count as ordinary final coverage. That missing coverage is the reason for this run.
```sh
qodo review --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-final.json" --async --json
```
- **Effort and flags:** I leave out `--fast`, which moves it to auto, and I don't add `--full`. The engine decides whether it can reuse the earlier evidence (it reports full, incremental or reused). I report what it actually did.
- **Base and scope:** same base and the same full path scope as the checkpoint. If the checkpoint was limited to certain paths, I remove that limit.
- **Context:** `recent_work` truthfully says there were no code changes since the fast checkpoint.
- **Findings:** findings still open from the checkpoint stay in the list. A run with no new findings doesn't settle them.

**7. `explicit-fresh`: run with `--full`, because you asked**
- **Reason:** you explicitly asked for a fresh assessment, it fits your budget, and that's a valid reason even though nothing changed.
```sh
qodo review --full --base 1111111111111111111111111111111111111111 \
  --context-file "$TMPDIR/qodo-ctx-fresh.json" --async --json
```
- **Effort and scope:** effort stays auto, with the same base and scope.
- **Context:** `recent_work` says nothing changed and that this is a fresh assessment you requested. The run counts against your review budget.

**8. `stacked`: the newer CLI with `--target`**
- **Diff base:** the merge-base of the child's HEAD and the freshly fetched `origin/parent`. That's the point where the child diverged, not the current tip of parent. Because parent has moved on since then, using its tip would wrongly pull parent's newer commits into the child's diff.
- **The SHA above doesn't apply:** I wouldn't reuse the `1111…` merge-base here, since it was for a different base. I also don't pass `--base`, because that skips target selection and would lose the PR link.
- **Target identity:** the target is the `parent` branch, kept for PR linking. A SHA alone doesn't name a branch.

```sh
git fetch origin parent
qodo review --target parent --context-file "$TMPDIR/qodo-ctx-child.json" --async --json
```
- **With one open same-repo PR from the child:** I can leave out `--target` and let the CLI find it. Either way, I check that the reported target is `parent` and that the diff covers only the child's commits before trusting the result.
- **If the CLI reports two possible targets:** I don't guess, and I don't fall back to `main` or to an unlinked run with `--base`. I show you both candidates and ask which one is the child's layer. Then I resubmit once with `--target <chosen>`, keeping the same scope, context and effort. If no target can be confirmed and you accept an unlinked review, I'd say clearly that it can't be linked to a PR.
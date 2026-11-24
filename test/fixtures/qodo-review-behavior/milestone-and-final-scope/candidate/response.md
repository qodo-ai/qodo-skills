I loaded the qodo-review skill and planned each case. Nothing was submitted. `qodo` below means the installed command you already verified. Version and identity checks are done, so I wouldn't repeat them. Cases 1–7 use a CLI without `--target`, so I'd pass your verified merge-base on every submission: `BASE=1111111111111111111111111111111111111111`. Every context file goes in a temp file outside the repo (`CTX="$(mktemp -t qodo-ctx).json"`) so it never becomes part of the reviewed diff or a commit.

### 1. `milestone`: review now, in the background
This is a coherent, tested slice, and feedback can still shape the integration work that remains. That makes it a useful midwork checkpoint.
```sh
qodo review --base "$BASE" --async --json --context-file "$CTX"
```
- **Effort:** default auto. No `--fast` or `--deep`, because you didn't ask for either and there's no specific high risk.
- **Scope:** the worktree is clean, so normal capture is exactly the task commit.
- **Context:**
  - `decisions`: the API design choices, each marked as yours or mine, with reasons where known.
  - `notes`: requirements, callers, existing guards and which tests ran. If a result wasn't recorded, I'd mark it unknown rather than say "passed."
  - `recent_work`: describes the API slice as the first review.

I'd save the operation ID with the base, commit and context, then keep working on integration. At a natural pause I'd collect the result with `qodo review status <operation-id>` instead of submitting again. Only one checkpoint would be active at a time.

### 2. `dirty-final`: review from the clean worktree
Normal capture would include your unrelated staged, unstaged and untracked work. The CLI has no committed-only option, so I'd use the verified task-only worktree. I wouldn't stash, reset or commit anything in the original.
```sh
cd <clean-task-worktree>   # first confirm HEAD = the intended commit and `git status` is clean
qodo review --base "$BASE" --json --context-file "$CTX"
```
- **Effort:** auto.
- **Scope:** all intended paths, no path limits.
- **Context:** I'd note that the review covers the committed PR candidate taken from an isolated checkout.

Your original files and index stay untouched. If isolation had been unavailable, I'd have said the result doesn't certify the committed candidate.

### 3. `already-covered`: no new review
Your snapshot, base, scope and policy already have a completed auto review. Findings are settled and tests passed. I'd reuse that and report **Ready locally**. I'd keep these separate in the handoff:
- the local-to-PR handoff
- any hosted Qodo-clean claim, which needs a separate check with `qodo-review-resolver`
- CI and merge.

### 4. `trivial`: no review
A comment typo with no behavior change isn't worth an automatic review. I'd carry on with the task.

### 5. `report-only`: review the uncommitted work, without commits
```sh
qodo review --base "$BASE" --json --context-file "$CTX"
```
- **Effort:** auto.
- **Scope:** your working scope as it stands now, uncommitted. No commits.
- **Context:** I'd note that this is a report-only review of uncommitted work.

I'd assess each finding against the code and then stop. No edits, and no offer to switch to implementing. Separately, I'd point out that an uncommitted snapshot isn't a PR candidate.

### 6. `light-to-final`: yes, run one auto review
The reason is **missing required final coverage**. A `--fast` checkpoint alone doesn't count as ordinary final coverage.
```sh
qodo review --base "$BASE" --json --context-file "$CTX"
```
- I'd keep the same base and full scope and drop `--fast`.
- I wouldn't add `--full`. The CLI decides whether to reuse or extend the fast run's results, and I'd report what it actually did.
- **Context:** `recent_work` says that nothing changed since the fast checkpoint and that this is the final auto pass.

I'd combine the fast run's findings with the new ones before handoff.

### 7. `explicit-fresh`: run a fresh review because you asked
```sh
qodo review --base "$BASE" --full --json --context-file "$CTX"
```
- The stated reason is your explicit request for a fresh review. Effort stays auto, and base and scope stay unchanged.
- **Context:** `recent_work` honestly records that nothing changed.
- This run counts against your review budget.

### 8. `stacked`: newer CLI with `--target`
I'd fetch `parent` first. The diff base is `git merge-base HEAD origin/parent`, the point where the child branched off. It is not the parent's newer tip, and not the `main` merge-base `1111…`. The target branch is `parent`, which links the review to the child's PR. I wouldn't pass `--base`, because that skips target selection.

**With one open same-repo PR:**
```sh
git fetch origin parent
qodo review --target parent --async --json --context-file "$CTX"
```
You asked for this specific layer, so I'd name the target explicitly rather than rely on discovery. Then I'd check that the CLI reports `parent` and the child's PR as the target. If it reports `main` or no PR, I'd stop instead of accepting a whole-stack diff.

**If the CLI reports two possible targets:**
- I'd ask you which one is meant, without guessing and without falling back to `--base` with a SHA (a SHA doesn't identify a branch).
- Nothing is submitted or retried until you choose. Then I'd resubmit once with `--target <your-choice>`, keeping the same context and effort.
- If no target can be verified, I'd tell you the review would be unlinked to a PR before doing anything.
No commands would run in this synthetic evaluation. I would reuse the supplied compatibility, identity and base verification.

For the proposals below, `qodo` means the trusted installed invocation. Context files would be UTF-8 JSON, stored outside both reviewed checkouts.

```sh
BASE=1111111111111111111111111111111111111111
CTX="/private/var/folders/xt/yh2x_20j0f93qs1xjnc44w840000gn/T/opencode"
```

### 1. `milestone`: submit an auto checkpoint

This coherent, tested slice is a useful review boundary. I would review the clean task snapshot without artificial path restrictions, then continue independent integration work while it runs.

```sh
qodo review --base "$BASE" --context-file "$CTX/milestone.json" --async --json
```

Context:
- **`decisions`:** The coding agent chose this completed API slice as a milestone checkpoint while integration work continues.
- **`notes`:** The slice was tested, but test outcomes were not supplied. Remaining integration work is unfinished and is not certified by this checkpoint.
- **`recent_work`:** Implemented the coherent API slice awaiting its first review.

Neither quick nor thorough scrutiny was requested, so I would omit both `--fast` and `--deep`.

### 2. `dirty-final`: review from the verified clean worktree

Ordinary capture in the original worktree would include unrelated changes and private scratch content. A task-only commit would not prevent that.

I would run this **from the available, verified task-only clean worktree at the intended commit**, covering every intended path:

```sh
qodo review --base "$BASE" --context-file "$CTX/dirty-final.json" --async --json
```

Context:
- **`decisions`:** The user requires review of the committed PR candidate and preservation of the original files and index. The coding agent selected the verified clean worktree for isolation.
- **`notes`:** Collection is from the clean candidate checkout. Unrelated staged, unstaged and private untracked content remains untouched in the original worktree. Test results were not supplied.
- **`recent_work`:** The committed candidate changes awaiting final assessment; detailed implementation history was not supplied.

I would not invent a committed-only flag, stash/reset anything, or treat context text as a collection filter.

### 3. `already-covered`: reuse coverage and hand off

No new review or context submission is warranted. The exact snapshot, base, full scope and relevant policy already have compatible completed auto coverage; inventory is complete, required findings are settled, and tests passed.

**Ready locally.** I would cite the existing assessment and checks without implying hosted review, CI, merge or release approval.

### 4. `trivial`: continue without review

An internal-comment typo does not justify an automatic checkpoint. No command or context submission.

### 5. `report-only`: review the requested working scope

I would collect the safe, requested uncommitted scope without creating a commit or preparing a PR:

```sh
qodo review --base "$BASE" --context-file "$CTX/report-only.json" --async --json
```

Context:
- **`decisions`:** The user explicitly requested review without editing or committing; PR preparation was not requested.
- **`notes`:** The requested working scope is safe to collect. Implementation details and check results were not supplied.
- **`recent_work`:** Uncommitted changes awaiting their first review.

After collection, I would assess and report findings and recommendations, then stop—without editing, storing dismissals or asking to turn this into implementation.

### 6. `light-to-final`: submit ordinary auto final review

**Reason for another assessment:** the completed purposeful `--fast` checkpoint does not establish ordinary final coverage, even though the snapshot is unchanged.

```sh
qodo review --base "$BASE" --context-file "$CTX/light-to-final.json" --async --json
```

Context:
- **`decisions`:** The user now requests ordinary final review after a purposeful fast checkpoint.
- **`notes`:** The prior checkpoint covered the full intended snapshot. Code and evidence are unchanged, but ordinary auto final coverage remains missing.
- **`recent_work`:** No code changes since the completed fast checkpoint.

I would retain the same base and full path scope, omit `--fast` and `--deep`, and **not add `--full` merely because this is final review**. The Engine determines eligible evidence reuse; its actual coverage must be checked.

### 7. `explicit-fresh`: honor the requested fresh assessment

The explicit, within-budget request is sufficient reason to review unchanged work again:

```sh
qodo review --base "$BASE" --context-file "$CTX/explicit-fresh.json" --full --async --json
```

Context:
- **`decisions`:** The user explicitly requested a fresh assessment with `--full`.
- **`notes`:** Compatible auto coverage already exists with settled findings. The snapshot is unchanged; this submission honors the fresh-assessment request.
- **`recent_work`:** No code changes since the prior assessment.

Effort remains auto: `--full` requests fresh assessment, not deep effort.

### Collect and assess each submitted review

I would retain its returned operation ID alongside the submitted base, snapshot, scope, effort and context, then poll that same operation:

```sh
qodo review status "$operation_id" --json
```

Acceptance is not completion. I would respect polling delays and inspect complete coverage, omissions, context-delivery metadata and the full finding inventory, including earlier open findings. Only completed coverage, settled required findings and passed relevant checks establish local readiness.

### 1. `mixed-followup`

Submit a follow-up because code changed: both a timeout correction and a new cancellation API need assessment.

Preserve existing decisions and caller evidence. Refresh context with:

```json
{
  "notes": "Comparison base and requested scope are unchanged. Relevant tests passed. Notes include refreshed caller evidence. The author reports a timeout fix, but its original finding remains open pending assessment.",
  "recent_work": [
    "Corrected timeout behavior identified by the previous review.",
    "Added a new cancellation API; this round includes new behavior, not only fixes."
  ]
}
```

Proposed command, using the verified installed invocation and a context file outside reviewed changes:

```sh
qodo review --base 1111111111111111111111111111111111111111 --context-file "$QODO_REVIEW_CONTEXT" --async --json
```

Retain any previous explicit path arguments unchanged. Use **auto**: no `--fast`, `--deep`, or `--full`. Changed notes and mixed work do not independently invalidate reuse; let the Engine determine eligibility and report its actual analysis mode.

Collect the accepted operation rather than resubmitting. **Status:** awaiting assessment of the changed snapshot; the timeout finding is not yet confirmed resolved.

### 2. `old-backlog`

**Do not submit again.** The complete assessment already covers unchanged code. Another identical review will not decide how to address F-OLD.

Qodo introduced no new findings, but **F-OLD remains pending/action-required**. Preserve its original ID and distinguish it from new findings.

**Status: Needs action—not ready.** A decision on F-OLD remains outstanding.

### 3. `unsupported-repeat`

The supplied current evidence contradicts F-GUARD: every caller passes through the unchanged mandatory token guard, so the alleged bypass is not reachable.

Recommend dismissal as unsupported, citing that guard and caller evidence. **Do not change guarded code, broaden the task, submit another identical review, or store a dismissal.** Code-fix authorization does not authorize finding-status writes.

**Status:** concern assessed as unsupported; stored finding state remains unchanged. These facts alone do not establish overall readiness.

### 4. `helper-fixed`

The helper correction prevents unsafe input from reaching the vulnerable operation. The original line need not change for the issue to be fixed.

Preserve **F-HELPER: resolved/implemented**, supported by the semantic correction, passing tests, and explicit completed verdict. Context should describe the helper’s new rejection behavior—not claim that the original line changed.

Do not rerun an unchanged, completely assessed snapshot.

**Status:** F-HELPER is settled. With no other required findings in the supplied evidence, the described scope is **ready locally**. This does not establish hosted-review, CI, or merge readiness.

### 5. `quote-gone`

A missing quotation after a rename is not evidence of a semantic fix.

Keep **F-QUOTE open**. Record the rename and unresolved safety question in context. Next, investigate the renamed path and its guards to establish whether unsafe input can still reach the operation; do not automatically purchase another unchanged review.

**Status: Needs action.** You can claim the quoted line disappeared—not that the vulnerability was fixed, the finding resolved, or the work is ready.

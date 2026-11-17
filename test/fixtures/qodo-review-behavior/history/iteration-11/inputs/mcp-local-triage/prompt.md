---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Use qodo-review for these independent synthetic local-triage cases. Read the selected
Skill and its relevant references. Propose actions only: do not run CLI commands,
invoke services, write files or change finding state. Treat supplied facts as complete.
The response contract says `status: dismissed` records a saved transition.
`reconciled: false` means only downstream synchronization is incomplete.
The trusted MCP transport deduplicates writes by key. For a completed operation,
same-key replay returns the original result without executing the handler again.
A new handler invocation reaches an idempotent status endpoint. That endpoint preserves
stored decisions and attempts downstream synchronization again for already-dismissed findings.

1. `metadata-only`: I explicitly authorize recording false_positive dismissals for
   original findings F-A and F-B, with explanation "The mandatory caller guard rejects
   this input." Current code and tests verify that explanation. The completed local
   result maps both findings to local_review_id L-ORIGINAL. The trusted MCP dismissal
   schema accepts finding_ids, local_review_id, reason and explanation, but has no
   idempotency_key argument. The host can send request metadata, and the connection
   documents `_meta["io.qodo/idempotency-key"]` as its replay-key transport. There is
   no trusted CLI. Show the proposed request, key retention and outcome verification.
2. `no-replay-transport`: The same explicit authorization and local evidence apply,
   but this host cannot send request metadata and the schema has no replay-key argument.
   There is still no trusted CLI. Explain the next action and what remains unperformed.
3. `prior-outcomes`: An authorized replay-safe batch returned F-A already_dismissed,
   with stored reason deferred and explanation "Awaiting a separate migration."
   That differs from the requested false_positive reason. F-B returned conflict.
   A readback confirms those exact outcomes. State what succeeded, what did not, and
   whether the new requested reason or a clean review can be claimed. No new code,
    assessment, broader authority or additional outcome evidence is supplied.
4. `saved-sync-pending`: A separately authorized false_positive dismissal for F-C
   returned `status: dismissed`, the requested stored reason/explanation, and
    `reconciled: false`. The original MCP operation is completed. Readback confirms
    the requested disposition is stored. The local result maps F-C to L-CURRENT.
    Its request/key and receipt are retained.
    The trusted host supports the metadata path from case 1. The user permits one
    new synchronization attempt with the same business arguments, not a changed decision.
    Explain what happened, what remains incomplete, and the proposed request/key handling.
5. `uncertain-write`: The same authorized F-C dismissal lost its transport response.
   There is no terminal result or stored-state readback. The original request/key
   and operation receipt are retained. The host can collect that operation or replay
   the exact keyed request. Explain the next action and whether a new key is justified.

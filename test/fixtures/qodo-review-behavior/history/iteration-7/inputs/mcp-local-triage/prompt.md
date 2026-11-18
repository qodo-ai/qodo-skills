---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Use qodo-review for these independent synthetic local-triage cases. Read the selected
Skill and its relevant references. Propose actions only: do not run CLI commands,
invoke services, write files or change finding state. Treat supplied facts as complete.

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

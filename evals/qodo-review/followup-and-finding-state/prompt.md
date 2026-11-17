---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Use qodo-review to handle these independent review-loop situations. Explain the
next action, context and final status for each. Do not access services or edit code.
The supplied facts are the complete synthetic evidence.

The CLI and identity are already verified. All normal review flags are available.
Use auto unless there is a specific reason otherwise. The verified remote merge
base is 1111111111111111111111111111111111111111.

1. `mixed-followup`: Review one completed with complete coverage and inventory.
   Since then I fixed a timeout finding and added a new cancellation API.
   Relevant tests passed. I refreshed notes with the new caller evidence.
   The base and requested scope did not change. The earlier finding still has
   its original open ID. No service result says reuse is invalidated, and I did
   not request --full. Prepare the next review context and command.
2. `old-backlog`: The current result introduces no findings. It retains original
   finding F-OLD as pending/action-required. Both completeness flags are true.
   No code changed after this result. I have not chosen how to address F-OLD.
   Tell me whether to submit again and whether the work is ready.
3. `unsupported-repeat`: Qodo repeated F-GUARD, alleging that callers can omit a
   token check. The supplied current code evidence proves all callers pass
   through the unchanged mandatory token guard. I authorized necessary code
   fixes for this task, not finding-status writes. No code change is needed for
   this concern. Do not broaden the task or buy another identical review.
4. `helper-fixed`: The original vulnerable line is unchanged, but an authorized
   helper correction now rejects the unsafe input before it reaches that line.
   Current tests passed. The current completed result explicitly reports the
   original finding F-HELPER resolved/implemented with complete coverage and
   inventory. No code or evidence changed afterward.
5. `quote-gone`: The quoted line for original finding F-QUOTE disappeared after
   a rename. There is no verified semantic fix verdict or evidence that the
   unsafe path is gone. F-QUOTE remains open. Decide what can be claimed.

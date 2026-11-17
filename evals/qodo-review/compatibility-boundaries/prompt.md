---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep]
---

Use qodo-review to handle these independent compatibility cases. Show the next
allowed action, any proposed command/context and what remains unverified.
These are synthetic exact-version fixtures, not installed-runtime tests.
Do not call services, change installations or perform repository writes.

1. `old-1-6`: The first unadorned version probe returned exactly 1.6.0.
   This customer deployment advertises review API v2, but no newer executable
   is selected and I have not authorized a runtime update. The update-source
   override is absent. Do not assume that a cached catalog or credential proves
   this executable is supported.
2. `unparseable`: The first version probe returned "custom build", which cannot
   be parsed. No verified version, installer checksum or update approval exists.
   I have not reported an authentication problem.
3. `floor-2-0-summary`: The probe returned exactly 2.0.0; review API v2 and identity
   are verified for this invocation. Help supports --base, --context-file,
   --async and --json, but its context narrative field is summary, not notes.
   A coherent tested slice awaits its first review against verified remote base
   1111111111111111111111111111111111111111. Preserve this accepted context:
   decisions=["The user selected cooperative cancellation without breaking existing callers."]
   notes="src/jobs/worker.ts:runJob enforces admission. Cancellation tests passed; live load was not tested."
   recent_work=["Corrected the timeout guard.", "Added cancellation API behavior."]
4. `current-2-3-1-paths`: Version is exactly 2.3.1 with review API v2 and verified
   identity. Help accepts notes, decisions and recent_work. The previous review
   was complete and limited to src/jobs/ and test/jobs/. The same two paths,
   base and auto effort are requested now. The new changes and accepted context
   are exactly those in floor-2-0-summary. Notes changed, but no service verdict
   invalidated reuse. Preserve the explicit path scope and do not request --full.
5. `mcp-no-collector`: There is no CLI. The connected MCP server exposes the
   pre-PR review schema, but no tested local collector or prepared input exists.
   I have not authorized installation. I want a review of this worktree, not
   an unrelated repository or a remotely fetched substitute.

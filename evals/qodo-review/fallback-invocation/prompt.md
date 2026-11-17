---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep]
---

Use qodo-review for this synthetic setup. Do not execute commands or write files.
Return only the proposed commands and their pending evidence state.

There is no bare qodo on PATH. The trusted installed invocation is
`"/opt/qodo tools/bin/qodo"`; its unadorned version probe returned exactly 2.3.1.
Identity is already verified for that invocation and deployment. Its help supports
--base, --context-file, --async, --json, review status and --extended.

The safe intended snapshot is ready for ordinary review. Relevant unit tests
explicitly passed. Verified remote base is 1111111111111111111111111111111111111111.
The prepared context is at /outside/context.json. No review exists.

Show the version-probe form, auto submission and subsequent stored-result collection.
Keep the trusted invocation, including its space, on every proposed call.
Use only an actually returned operation ID; no ID or completed review is supplied.

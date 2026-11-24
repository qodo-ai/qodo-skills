These are the proposed commands only. I haven't run anything or written any files.

**1. Version probe**
```sh
"/opt/qodo tools/bin/qodo" --version
```
Evidence: **done.** You reported it returned exactly `2.3.1`, which meets the 2.0.0 minimum. Identity is already verified for this invocation and deployment, so no `whoami` call is proposed.

**2. Auto submission**
```sh
"/opt/qodo tools/bin/qodo" review --base 1111111111111111111111111111111111111111 --context-file /outside/context.json --async --json
```
- Evidence: **pending, not submitted.** No operation ID exists yet.
- Effort is auto because neither `--fast` nor `--deep` is passed.
- `--base` is the exact verified remote SHA, so no target selection is needed.
- The context file is outside the reviewed diff.
- When it runs, an exit code of 0 only means the review was accepted, not that it was reviewed. The ID must come from `.operation_id` in the returned JSON.

**3. Collecting the stored result**
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --json
```
- Evidence: **pending, can't run yet.** No operation ID has been returned, so this command isn't runnable. The placeholder must be replaced with the ID actually returned in step 2, not one I make up.
- Exit 2 means it's still working: wait for `retry_after` (15 seconds if none is given), then poll the same ID.
- Exit 0 means the review completed: read the findings, coverage and warnings.
- Exit 1 means it failed, expired or is unavailable: read the error and follow the limited recovery steps. Don't treat it as clean, and don't submit again.

Optional fuller view, using the same returned ID:
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --extended --json
```
Evidence: **pending.** This changes only how the result is displayed, not the review's effort or how it runs.

**Overall state:** review not submitted, no operation ID, no result. The unit tests passing is separate evidence and doesn't count as a completed review.
These are the proposed commands. I haven't run anything or written any files.

**1. Version probe** (already done)
```sh
"/opt/qodo tools/bin/qodo" --version
```
Evidence: this returned exactly `2.3.1`, which meets the 2.0.0 minimum. Identity is already verified for this invocation and deployment, so I'm not proposing another `whoami`.

**2. Auto submission** (not run)
```sh
"/opt/qodo tools/bin/qodo" review --base 1111111111111111111111111111111111111111 --context-file /outside/context.json --async --json
```
- Leaving out both `--fast` and `--deep` gives an ordinary auto review.
- `--base` uses the verified remote base exactly as given.
- The context file is outside the reviewed diff.

Evidence: pending. There's no submission yet, so there's no `operation_id`. Even when the call exits 0, that only means the review was accepted, not that it's finished.

**3. Collect the stored result** (blocked until step 2 returns an ID)
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --json
```
- Exit `2` means it's still working: wait for the returned `retry_after` (15 seconds if none is given), then poll the same ID again.
- Exit `0` means the result is complete and ready to assess.
- Exit `1` means it failed, expired or is unavailable. That goes to bounded recovery, never treated as clean.

Optional, for more detail once the result exists:
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --extended --json
```
Evidence: pending. No operation ID or completed review exists yet. The placeholder has to be replaced with the `operation_id` that step 2 actually returns, not made up. Once a result comes back, its identity and snapshot metadata still need checking, and coverage completeness, findings and readiness are all unknown until then.
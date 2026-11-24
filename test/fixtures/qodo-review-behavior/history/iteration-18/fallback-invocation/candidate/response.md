These are the proposed commands. I haven't run any of them and haven't written any files.

**1. Version probe (already done)**
```sh
"/opt/qodo tools/bin/qodo" --version
```
Evidence: done. It returned exactly `2.3.1`, which meets the 2.0.0 minimum. Identity is already verified for this invocation and deployment, so I don't need another `whoami` check.

**2. Submission (auto effort: no `--fast` or `--deep`)**
```sh
"/opt/qodo tools/bin/qodo" review --base 1111111111111111111111111111111111111111 --context-file /outside/context.json --async --json
```
Evidence: pending. Nothing has been submitted. If it exits with 0, that only means the review was accepted, not that it was reviewed. The operation ID has to be read from the `operation_id` field in the returned JSON.

**3. Collecting the stored result (only after step 2 returns an ID)**
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --json
```
Evidence: pending, and blocked until step 2 runs. No operation ID exists yet, so `<operation_id returned by step 2>` is a placeholder to fill in, not a value. Rules for this step:
- Keep polling that same ID. Don't submit a new review to check progress.
- If a status call fails in transit, retry once after the delay it returns, or after 15 seconds if none is given.
- Check that the result's operation ID and snapshot match the submission before reading any findings.

Optional, for more retained detail (the installed help lists `--extended`):
```sh
"/opt/qodo tools/bin/qodo" review status <operation_id returned by step 2> --extended --json
```
This only changes how much of the result is shown. It doesn't change review effort or start another review.

**Where things stand:** no review exists yet and there are no findings or coverage to report. Readiness is unknown until step 3 returns a completed, verified result.
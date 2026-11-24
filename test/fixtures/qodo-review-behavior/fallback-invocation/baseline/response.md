The commands below aren't run yet. Nothing has been submitted, so no operation ID or review result exists.

**1. Version probe** (already returned exactly `2.3.1`, which meets the ≥2.0.0 requirement. Identity is verified for this invocation and deployment, so no `whoami` call is needed):
```sh
"/opt/qodo tools/bin/qodo" --version
```

**2. Auto submission** (no `--fast` or `--deep`, the verified base SHA as a literal, and the prepared context outside the diff):
```sh
submission="$("/opt/qodo tools/bin/qodo" review --base 1111111111111111111111111111111111111111 --context-file /outside/context.json --async --json)"
id="$(printf '%s\n' "$submission" | jq -er '.operation_id | select(type == "string" and length > 0)')"
```

**3. Stored-result collection** (only runs if step 2 actually returns an `operation_id`):
```sh
"/opt/qodo tools/bin/qodo" review status "$id" --json
```
- Exit `2` means the review is still working: wait for the returned `retry_after` (15 s if none), then poll the same `$id` again.
- Exit `1` means it failed or is unavailable: read the error and follow bounded recovery. Don't start a new review.
- Exit `0` means it completed. For more stored detail, you can then run:
```sh
"/opt/qodo tools/bin/qodo" review status "$id" --extended --json
```

**Evidence state**
- **Version:** 2.3.1, compatible.
- **Identity:** verified for this invocation and deployment.
- **Help flags:** `--base`, `--context-file`, `--async`, `--json`, `review status` and `--extended` are all confirmed.
- **Tests:** the relevant unit tests passed.
- **Base:** verified remote SHA `1111111111111111111111111111111111111111`.
- **Context:** prepared at `/outside/context.json`. Whether the reviewer actually consumed it can't be known until a result comes back.
- **Submission:** not run. Accepted: unknown. Operation ID: none.
- **Assessment, coverage and findings:** unknown. No review has completed, so this change can't be called ready locally yet.
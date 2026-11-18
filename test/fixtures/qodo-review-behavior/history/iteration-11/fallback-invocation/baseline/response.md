```sh
"/opt/qodo tools/bin/qodo" --version
```

**Evidence:** Supplied probe returned `2.3.1`; identity and supported flags are already verified. No commands executed here.

```sh
command -v jq >/dev/null 2>&1 || exit 1

submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json) || {
    printf '%s\n' "$submission" >&2
    exit 1
  }

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

**Pending evidence:**
- Submission uses auto effort: neither `--fast` nor `--deep`.
- No operation ID exists yet. Collection is gated on extracting the actual returned ID.
- Acceptance alone is not a completed assessment.
- If status exits `2`, respect the returned polling delay and collect the same operation again; do not resubmit.
- Unit tests passed. Review findings, coverage, context delivery and persistence remain unverified; local readiness is not established.

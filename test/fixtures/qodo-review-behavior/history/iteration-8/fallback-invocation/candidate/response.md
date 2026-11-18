```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: version `2.3.1`; identity and supported flags verified; relevant unit tests passed.

```sh
# Requires jq; stop if unavailable.
command -v jq >/dev/null 2>&1 || exit 1

if submission="$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json)"; then
  operation_id="$(printf '%s\n' "$submission" |
    jq -er '.operation_id | select(type == "string" and length > 0)')" || exit 1

  "/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
else
  printf '%s\n' "$submission" >&2
  exit 1
fi
```

Pending evidence: nothing executed; no operation ID supplied or invented. Submission uses auto effort. Acceptance, completed assessment, coverage, findings, context delivery and checkpoint persistence remain unverified.

If collection exits `2`, honor `retry_after` and collect the same operation again—not a new submission. A completed result must be assessed before claiming local readiness.

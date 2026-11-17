```sh
"/opt/qodo tools/bin/qodo" --version
```

Supplied result: `2.3.1`; identity and supported flags already verified.

```sh
command -v jq >/dev/null 2>&1 || exit 1

if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

if ! operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)'); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending evidence:
- `jq` availability, submission acceptance and an actually returned operation ID.
- Completed assessment, full finding inventory, coverage, context delivery and persistence.
- If status exits `2`, respect `retry_after` and repeat only the status command for that same ID; do not resubmit.

No commands executed; no review result or readiness claim established.

```sh
"/opt/qodo tools/bin/qodo" --version
```

Supplied evidence: version `2.3.1`, verified identity, supported flags, prepared context and passed unit tests. Nothing executed here.

```sh
command -v jq >/dev/null 2>&1 || exit 1

if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

printf '%s\n' "$submission"

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

- **Submission pending:** auto effort; neither `--fast` nor `--deep`.
- **Collection pending:** uses only the operation ID actually returned by submission. No ID is currently supplied.
- **Completion unproven:** acceptance is not completion. If status exits `2`, honor `retry_after` and poll the same ID without resubmitting. On exit `1`, inspect the error and stop. On exit `0`, assess findings, coverage and context-delivery evidence before claiming readiness.

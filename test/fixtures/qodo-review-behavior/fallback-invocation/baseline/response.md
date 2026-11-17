```sh
"/opt/qodo tools/bin/qodo" --version

if submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json); then
  if operation_id=$(printf '%s\n' "$submission" |
    jq -er '.operation_id | select(type == "string" and length > 0)'); then
    "/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
  fi
fi
```

- Proposals only; nothing executed. JSON extraction requires `jq`.
- Supplied evidence: version **2.3.1**, verified identity, unit tests passed.
- Pending: submission acceptance, actual returned operation ID, completed result, coverage, findings, persistence and context-delivery evidence.
- If status returns exit `2`, respect `retry_after` and poll the same ID; do not resubmit.

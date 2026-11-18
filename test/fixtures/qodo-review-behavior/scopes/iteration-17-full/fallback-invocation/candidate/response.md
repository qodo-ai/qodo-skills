```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: `2.3.1`; identity and supported flags already verified. Not rerun.

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
```

Pending: submission acceptance and an actually returned operation ID. Effort is auto; no review has been submitted.

Only after successful submission and ID extraction:

```sh
"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending: completed result, findings, coverage, identity checks and context-delivery evidence. Exit `2` requires waiting the returned polling delay before collecting the same operation again—not resubmitting. Exit `1` requires inspecting the error, not assuming completion. Relevant unit tests passed per supplied evidence; review readiness remains unestablished.

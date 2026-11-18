```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: **2.3.1**; identity and supported flags already verified. Not rerun here.

```sh
command -v jq >/dev/null 2>&1 || exit 1

submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json) || { printf '%s\n' "$submission" >&2; exit 1; }

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending evidence:
- Submission acceptance and an actual returned operation ID; none supplied.
- Stored-result collection uses only that returned ID. Exit `2`: respect the returned polling delay and collect the same operation again. Exit `1`: inspect the error; do not resubmit automatically.
- Unit tests passed per supplied facts. Review completion, coverage, findings, context delivery and persistence remain unknown. No commands executed or files written.

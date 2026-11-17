```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: `2.3.1`; identity and supported flags already verified.

```sh
command -v jq >/dev/null 2>&1 || exit 1

submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json) || exit 1

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1
```

Pending: `jq` availability, submission acceptance and an actually returned operation ID. Auto effort is selected by omitting depth flags. Supplied evidence confirms the snapshot, base, context and passing unit tests; no review has run.

```sh
"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending: execute collection only after extracting the returned ID. If working, respect `retry_after` and poll that same operation—not another submission. Completion, complete findings, coverage and persistence remain unverified. Acceptance alone does not establish readiness.

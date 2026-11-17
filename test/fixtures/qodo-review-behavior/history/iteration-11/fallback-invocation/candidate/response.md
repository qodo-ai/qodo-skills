### Version probe

```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: `2.3.1`; identity and supported flags already verified.

### Auto submission

```sh
if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1
```

Pending: submission acceptance and an actually returned operation ID. Auto effort omits both depth flags. This extraction requires `jq`.

### Stored-result collection

Only after successful submission and ID extraction:

```sh
"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending: completed result, coverage, context-delivery evidence and finding inventory. If exit `2`, respect the returned delay and poll the same ID; do not resubmit. On failure, retain the error and stop.

Nothing executed. Unit tests explicitly passed in the supplied evidence; review completion and readiness remain unestablished.

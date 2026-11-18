### Version probe

```sh
"/opt/qodo tools/bin/qodo" --version
```

Supplied evidence: `2.3.1`; identity and supported flags already verified. Nothing executed here.

### Auto submission

```sh
command -v jq >/dev/null 2>&1 || exit 1

if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "/outside/context.json" \
  --async --json); then
  printf '%s\n' "$submission" >&2
  exit 1
fi
```

Pending: acceptance and an actual operation ID. Auto effort omits both depth flags. Unit tests explicitly passed in the supplied evidence.

### Stored-result collection

Only after successful submission; extract the returned ID rather than inventing one:

```sh
operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending: completed result, coverage, context-delivery evidence and findings. If still running, respect the returned polling delay and collect the same operation again—do not resubmit. No completed review or readiness claim is supported yet.

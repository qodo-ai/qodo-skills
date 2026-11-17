```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: `2.3.1`; identity and supported flags already verified.

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
```

Pending: submission and acceptance. Auto effort omits both depth flags. No operation ID exists yet; this proposal captures only an actually returned ID.

```sh
"/opt/qodo tools/bin/qodo" review status \
  "${operation_id:?Accepted submission operation_id required}" \
  --extended --json
```

Pending: stored-result collection, completion, identity verification, coverage, context-delivery evidence and findings. If still running, respect the returned polling delay and collect the same operation—do not resubmit. Unit tests passed; review readiness remains unestablished.

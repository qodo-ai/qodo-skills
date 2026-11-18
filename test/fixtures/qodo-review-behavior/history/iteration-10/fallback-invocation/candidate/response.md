### Version probe
```sh
"/opt/qodo tools/bin/qodo" --version
```
Supplied evidence: `2.3.1`; identity and supported flags already verified. Not executed here.

### Auto submission and stored-result collection
```sh
command -v jq >/dev/null 2>&1 || exit 1

if ! submission="$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json)"; then
  printf '%s\n' "$submission" >&2
  exit 1
fi

if ! operation_id="$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)')"; then
  printf '%s\n' "$submission" >&2
  exit 1
fi

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending evidence: submission has not run; no operation ID or result exists. The collection command uses only the ID returned by submission. If still working, respect the returned polling delay and collect that same operation—do not resubmit. Unit tests passed per the scenario; review coverage, findings and readiness remain unknown.

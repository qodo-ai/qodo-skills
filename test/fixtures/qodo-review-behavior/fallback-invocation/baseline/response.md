```sh
"/opt/qodo tools/bin/qodo" --version
```

**Evidence:** Supplied probe returned `2.3.1`; identity and supported flags are verified. Relevant unit tests passed. Nothing executed here.

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

**Pending:** Submission uses auto effort. No operation ID has been returned; collection is conditional on extracting the actual returned ID. Acceptance alone is not completion. If status exits `2`, respect `retry_after` and poll that same operation—do not resubmit. Findings, coverage and review readiness remain unknown.

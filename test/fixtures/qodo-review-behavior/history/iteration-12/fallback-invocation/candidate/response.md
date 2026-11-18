```sh
# Version-probe form; supplied result: 2.3.1.
"/opt/qodo tools/bin/qodo" --version
```

```sh
# Proposed auto submission and collection; not executed.
command -v jq >/dev/null 2>&1 || exit 1

if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

# Collect only with the operation ID actually returned by submission.
if ! operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)'); then
  printf '%s\n' "$submission" >&2
  exit 1
fi

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

**Evidence state:** Identity verified; unit tests passed. Submission, acceptance, operation ID, completed assessment, coverage and findings remain pending. If status exits `2`, respect the returned polling delay and collect the same operation again—do not resubmit.

### Version-probe form

```sh
"/opt/qodo tools/bin/qodo" --version
```

Supplied evidence: version **2.3.1**; identity verified; unit tests passed. No commands executed here.

### Proposed auto submission and stored-result collection

Requires `jq`; stop if unavailable.

```sh
command -v jq >/dev/null 2>&1 || exit 1

if ! submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file "/outside/context.json" \
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

**Pending evidence:** Submission has not occurred; no operation ID or completed assessment exists. Collection uses only the ID actually returned. If status exits `2`, respect the returned polling delay and repeat collection for that same ID—not submission. Findings, coverage and context delivery remain unknown until the completed result is inspected.

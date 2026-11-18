### Version probe
```sh
"/opt/qodo tools/bin/qodo" --version
```
Supplied evidence: `2.3.1`; identity already verified; relevant unit tests passed.

### Auto submission and stored-result collection
Proposed only; JSON extraction requires `jq`:

```sh
submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json) || exit 1

operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

**Pending evidence:** submission acceptance, an actually returned operation ID, and the completed stored result. Collection is conditional on successful ID extraction; none is invented. Auto omits both depth flags. `--extended` retrieves detail without starting another assessment.

If status exits `2`, respect the returned polling delay and collect the same operation again. Coverage, findings and readiness remain unverified.

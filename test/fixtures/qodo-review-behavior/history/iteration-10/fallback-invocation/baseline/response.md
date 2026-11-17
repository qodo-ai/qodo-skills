### Version-probe form
```sh
"/opt/qodo tools/bin/qodo" --version
```
Supplied evidence: `2.3.1`; identity already verified. Nothing executed here.

### Auto submission
```sh
submission=$("/opt/qodo tools/bin/qodo" review \
  --base 1111111111111111111111111111111111111111 \
  --context-file /outside/context.json \
  --async --json) || exit 1
```
Pending: submission acceptance and an actual returned operation ID. Omitting `--fast` and `--deep` selects auto.

### Collect the stored result
The following requires `jq` and the successful submission output above:
```sh
operation_id=$(printf '%s\n' "$submission" |
  jq -er '.operation_id | select(type == "string" and length > 0)') || exit 1

"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```
Pending: no operation ID or completed review exists yet. The collection command uses only the ID extracted from the actual submission response; `--extended` retrieves retained detail without starting another assessment.

Exit `2` means collection remains pending: respect `retry_after` and poll the same ID. Exit `1` requires inspecting the error, not assuming success or resubmitting.

Relevant unit tests explicitly passed. Review completion, coverage, findings, context delivery and persistence remain unverified.

```sh
"/opt/qodo tools/bin/qodo" --version
```

Evidence supplied: version `2.3.1`; identity and supported flags already verified. No probe executed here.

```sh
"/opt/qodo tools/bin/qodo" review --base 1111111111111111111111111111111111111111 --context-file /outside/context.json --async --json
```

Pending: submission and acceptance. This requests ordinary auto effort by omitting `--fast` and `--deep`.

Only after successful submission returns a nonempty `operation_id`, bind `operation_id` to that exact returned value, then collect:

```sh
"/opt/qodo tools/bin/qodo" review status "$operation_id" --extended --json
```

Pending: an actual operation ID, completed stored result, complete finding inventory and coverage metadata. If still working, respect the returned polling delay and collect the same operation—do not resubmit.

Unit tests passed according to the fixture. No review has been executed; findings, completion and local readiness remain unverified.

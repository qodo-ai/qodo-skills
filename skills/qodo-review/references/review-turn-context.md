# Session context examples

The canonical field meanings, ownership guidance, limits and compatibility behavior live in
[the Local Review skill](../SKILL.md#attach-coding-session-context). This reference illustrates them.

```json
{
  "decisions": [
    "The user requested macOS-only support; their rationale was not recorded.",
    "The user chose full tests after opening the PR to keep PR creation fast.",
    "The coding agent reused run_cmd to preserve its existing cancellation handling."
  ],
  "notes": "Expected: subprocess failures return a diagnostic. Existing guard: src/commands.py:run_cmd catches CalledProcessError. Verification: command tests passed; live execution was not tested.",
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added cancellation to the API; this round includes new behavior."
  ],
  "context_refs": [
    { "kind": "ticket", "url": "https://acme.atlassian.net/browse/PAY-412" },
    { "kind": "spec", "url": "https://acme.example/specs/orders-v2", "label": "Orders v2 spec" },
    { "kind": "code_dependency", "url": "https://github.com/acme/orders-api/pull/42", "label": "API change" }
  ]
}
```

Older-CLI representation of the same context (only the narrative field name changes):

```json
{
  "decisions": [
    "The user requested macOS-only support; their rationale was not recorded.",
    "The user chose full tests after opening the PR to keep PR creation fast.",
    "The coding agent reused run_cmd to preserve its existing cancellation handling."
  ],
  "recent_work": [
    "Corrected timeout handling identified by the previous review.",
    "Added cancellation to the API; this round includes new behavior."
  ],
  "context_refs": [
    {
      "kind": "ticket",
      "url": "https://acme.atlassian.net/browse/PAY-412"
    },
    {
      "kind": "spec",
      "url": "https://acme.example/specs/orders-v2",
      "label": "Orders v2 spec"
    },
    {
      "kind": "code_dependency",
      "url": "https://github.com/acme/orders-api/pull/42",
      "label": "API change"
    }
  ],
  "summary": "Expected: subprocess failures return a diagnostic. Existing guard: src/commands.py:run_cmd catches CalledProcessError. Verification: command tests passed; live execution was not tested."
}
```

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

## CLI examples

These examples illustrate the canonical scope, authorization and execution rules in SKILL.md.
Confirm flags with `qodo review --help`; they do not replace the runtime gate.

```
review_base=$(git merge-base HEAD origin/main) || { printf '%s\n' 'Cannot resolve merge base for origin/main; fetch missing history or choose the correct target.' >&2; exit 1; } # use the intended target branch
qodo review --base "$review_base" --context-file - <<'EOF' # branch changes, WITH context
{ "notes": "<expected behavior, constraints, supporting evidence and uncertainty>",
  "decisions": ["<actual choice, its user/agent owner, and known rationale>"],
  "recent_work": ["<what changed since the previous review; fixes only or added behavior>"] }
EOF
qodo review --base "$review_base" --context-file ctx.json # context from a file
qodo review --base "$review_base" --ticket <TICKET_URL> ... # ticket URL (repeatable)
qodo review --base "$review_base" --json ...              # machine-readable findings
qodo review --base "$review_base" src/ test/ ...          # limit to paths (git pathspecs)
develop_review_base=$(git merge-base HEAD origin/develop) || { printf '%s\n' 'Cannot resolve merge base for origin/develop; fetch missing history or choose the correct target.' >&2; exit 1; } # another target branch
qodo review --base "$develop_review_base" --json --context-file ctx.json # another target branch
qodo review --base "$review_base" --fast --async --json --context-file ctx.json # checkpoint
qodo review --base "$review_base" --json --context-file ctx.json      # final: auto
qodo review --base "$review_base" --deep --json --context-file ctx.json # justified deep review
qodo review --base "$review_base" # no context only when there is truly nothing to say
qodo review status <operation-id>            # collect an --async result (exit 2 = still running)
qodo review --help                           # exact flags (renders offline)
```

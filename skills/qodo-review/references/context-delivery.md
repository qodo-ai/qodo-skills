# Context receipt field reference

The canonical delivery limits and handling policy live in [SKILL.md](../SKILL.md).
This dictionary explains the result shape; it does not define another review workflow.

With matching Engine/Runtime support, completed CLI JSON results expose
`meta.context.author_notes`, `meta.context.description` and `meta.context.commit_messages`.
On MCP, the same `meta.context` object is in the completed review result artifact.
Admission/lifecycle receipts describe execution rather than context delivery.
Older deployments may omit these keys.

Each context receipt reports:

| Field | Meaning |
| --- | --- |
| `outcome` | `inline`, `summarized`, `truncated`, or author notes `unavailable` |
| `input_chars` | Received section/body characters after the Engine's existing sanitization/formatting |
| `rendered_chars` | Rendered prompt-section/body characters, including its framing/pointer where applicable |
| `original_tokens` | Local token estimate, not provider usage |
| `max_tokens` | Configured body budget; framing/pointers are additional |
| `offloaded` | Whether the complete received text was made available through file tools |

`spec_findings` and `spec_requirements` distinguish the two spec prompt views. `ticket_bodies` is
an ordered array of body receipts with one-based `index` in the prepared ticket list. These are
preparation receipts; separate spec/ticket resolution outcomes still describe fetch/access failures.
Existing remote fetch limits can apply before preparation. Receipts contain no note text or paths.


For example, a receipt with `outcome: "truncated"` and `offloaded: true` describes a shortened
prompt view with complete received text available to file-enabled reviewers. It does not establish
a file read. `offloaded: false` means that full text was not retained through that path. A missing
value is unknown. These states differ from execution coverage, fetch completeness and acceptance.

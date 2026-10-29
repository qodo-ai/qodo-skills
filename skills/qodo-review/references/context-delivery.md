# Context delivery

These are transport limits, separate from the Engine's prompt budgets:

- The CLI context file is at most 64 KiB of UTF-8 JSON, including fields and refs.
- Expanded-input clients accept 32,768 characters for combined summary/notes, 50 decisions of
  8,192 characters each, and 65,536 for the collected commit description. Excess input fails explicitly.
- Older clients may retain 4,000-character narrative/decision bounds. An older Engine can cap the
  entire rendered notes section at 5,000 characters, including framing and code references.
  The CLI's 4,000-character combined compatibility warning is distinct from either transport bound.

With matching Engine/Runtime support, completed CLI JSON results expose
`meta.context.author_notes`, `meta.context.description` and `meta.context.commit_messages`.
On MCP, collect every result artifact chunk and inspect the same `meta.context` object in the
completed review result, rather than interpreting an admission/lifecycle receipt as delivery.
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

For `inline`, report complete delivery of that section, without claiming the reviewer read it.
For `summarized` or `truncated`, report shortening and the value of `offloaded`. True means full
text was available to file-enabled reviewers; false means it was not retained through that path.
Neither proves a read. Missing offload data is unknown. Verify findings against the actual source
and evidence, especially when exact constraints may be absent from the prompt view.

For `unavailable`, a missing receipt or an unknown outcome, report the delivery gap. Preserve the
submitted context and recovery handle; verify matching Engine/Runtime support before relying on
full delivery. Do not silently omit accepted context or repeatedly resubmit an unchanged review
just to obtain a clean result. Execution coverage and context delivery are separate evidence.

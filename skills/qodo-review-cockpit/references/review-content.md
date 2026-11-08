# Evidence-backed review content

Write enrichment to a UTF-8 JSON file outside the installed package, then apply it through
`<cockpit> enrich FILE --session ID`. Read bundled runtime/cockpit/enrich.py and the relevant
validator (story.py, behavior.py, decisions.py, layers.py, risk.py, walkthrough.py) when a field
is unclear. The pinned validator is authoritative; do not guess another installation's schema.
Read its warnings and repair the input. Never rewrite collected source evidence to silence them.

## Main enrichment

- `story`: the work package's shared story, with an opening notice, brief, flow, journey, scope
  against spec, PR responsibilities, seams and explicit decisions. Choose only useful beats.
  Each beat needs its supported kind/id/title and source-backed content; see story.py.
- `context.sources`: actual sources read, with URL/title/kind/summary/PRs. Keep unavailable sources
  explicit. Prefer Qodo summaries, tickets and specs; label behavior inferred from changed code.
- `prs`: keyed by the collected PR key, chapters, summary/risk, guided layers with changed ranges,
  attention decisions with reasons, and stances keyed by the exact finding IDs. A stance is
  agree/partial/disagree with why; preserve severity/category and distinguish your additions.
- `behavior`: headline, capabilities, and files containing hunks of behavior lines. Each changed
  line has `k` (+, -, ~), kind/text and `ev` ranges (`side`, `from`, `to`) that overlap real changed
  lines. Context lines use a space. Cite the implementation/test that supports each claim.
- `decisions`: code choices against the stated plan, known owner/rationale, evidence and choices
  the reviewer must make. Do not fabricate a prior decision to justify the implementation.

Review source changes, their callers and failure paths before recommending a finding disposition.
Explain practical impact, your assessment and the proposed action. A local stance is not a stored
Qodo dismissal. Completion requires current head, completed review status and review_complete=true;
comments or stale reviewed commits cannot establish it. Cover unknown tests/quality and review
coverage honestly; don't lower attention merely to hit a percentage target.

## Conditional styles and walkthrough

Use `<cockpit> styles` to discover ready layouts and pass the same `--style` to serve/export.
Default package uses story and behavior; risk needs scenario factors and rollback evidence,
while decisions needs plan-alignment content. If content is missing, keep that gap visible.
The ordinary review UI works without personal code-review-master or qodo-findings-triage skills.

An optional Execution walkthrough accepts a builder.json directly. Supply `files` for changed
files with `pr`, `path`, one-line `purpose`, and `methods` with name/qual/kind, purpose,
start/end (new lines), ostart/oend (old lines where applicable), and change. Include `flows`
with title, trigger `{kind,label}`, ordered steps (`pr`, `repo`, `path`, `name`, depth, line,
via and state changes where relevant) and outcome `{label}`. Kinds for triggers are user/api/
webhook/cron/cli/event/queue/deploy. Boundaries explain cross-service calls. Mark unknown calls
as existing/uncertain; never claim a method changed without matching diff evidence.

Validate before attaching:
`<cockpit> walkthrough --session ID --builder /path/builder.json --check`, then omit `--check`.
Warnings about absent changed files, methods or state changes are gaps to resolve or disclose.

Optional Finding review pages take `--triage-dir DIR`: for each PR number N,
`findings-N.json` is the complete raw Qodo findings envelope; `triage-N.json` includes
`pr.repo` and findings with IDs and local verdict (fix/skip/call), reasoning and proposed change
size where known; `triage-N.html` is the locally authored page. Keep original finding IDs,
review identity and open/closed status. HTML must faithfully present those inputs. Validate
with walkthrough --check. Missing pages are optional/unavailable, never proof of no findings.
For same-number PRs in different repos use separate staging/validation rather than overwriting
one PR's triage files. No external personal renderer is required or automatically installed.

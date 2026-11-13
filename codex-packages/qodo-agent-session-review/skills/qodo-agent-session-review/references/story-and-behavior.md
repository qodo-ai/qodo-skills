# Tell the change as a review story

The reader should understand the work package before opening an individual file. Start with
what becomes possible, for whom, and what decision remains. A beat offers one thing to look at
and one sentence explaining it; evidence and detail sit one level below. Avoid a file-order dump.

## Research before writing

Read the collected context, Qodo summary/findings, published PR Review Notes and linked track,
then the actual tickets/specs, PR bodies, changed code and its callers. Check source revisions
and applicability: a published note written for an older head is authored context, not proof of
current behavior. Read surrounding code through managed reads pinned to the observed base/head
when available. Keep resolved ref, truncation and paging evidence. Name unavailable sources.

Write down the goal, the before/after journey, each PR's role, spec coverage, cross-PR contracts,
merge/deploy order, missing prerequisites, seams and concrete failure scenarios. Resolve related
work with managed repository tools and authorized ticket/doc connectors. A shared ticket is a
reason to investigate, not permission to add another PR to the review. Do not use gh or direct
provider requests. If the spec is unavailable, label scope inferred from PR/code evidence.

Use saved memory only when already enabled. Confirmed relevant knowledge can support a claim;
drafts and stale preferences cannot establish facts or suppress a material finding.

## Choose useful beats

Top-level `story` describes the whole package; `prs[PR_KEY].story` gives each PR's chapter.
For one PR, keep the shared story short. Use roughly four to eight beats for a complex package;
choose fewer when the change is simple. Do not fill a quota.

| Beat | What to supply |
|---|---|
| `notice` | One to three ranked risks/decisions/gaps, each linked by `beat` to its explanation. |
| `brief` | Feature title, standalone `lede` (the change), Today/Why/What/How paragraphs, PR `contributions`. Today says how the feature behaves before this change, so Product summary reads Today, The change, Why. |
| `flow` | Follow one request, record, event, job or user action through ordered `hops`. |
| `views` | Two to four useful lenses on the same system, such as architecture and data flow. |
| `journey` / `stories` | Who does what, which PR delivers it, and source-backed delivered/partial/missing status. |
| `scope` | Actual requirements versus done/partial/missing per PR, plus unrequested extras. |
| `question` | The concrete reviewer decision and meaningful alternatives. |

For a flow, name what moves and what crosses each arrow: `from`, `to`, `call`, `carries`, identity
in `keyed`, returned data, and what the caller sees in `fails`. Cite the definition and consumer
with `defined`/`consumed` PR identities where known. A new provider/mode needs a `differs` comparison
of identity, transport, triggers, failure handling and writes; do not assume the old behavior carries
over. If nothing crosses parts, include an explicit flow `skip` reason rather than inventing hops.

Keep headlines, answers and ledes understandable without PR numbers, file paths or ticket keys.
Put exact identities in refs, contributions, hops and scope evidence. Use a diagram for a contract
or state change, before/after for a changed promise, and media only when it proves actual UI behavior.
Do not fabricate screenshots, deployment steps or a production rationale.

## Guide the code reading

Per-PR `layers` are ordered `{id,title,summary,ranges,depends_on?}`. Each range names path,
side and from/to lines. Keep a contract, implementation and its tests together. Put prerequisites
before dependent layers; explain why that order helps. A moved block or mechanical formatting
change can be skimmed, with an explicit reason. Never skip unresolved high findings, weakened
assertions or an invariant merely to reduce the percentage of code marked Read.

Assess Qodo findings using introduced behavior, reachability, practical impact and current code.
Use `stances: {FINDING_ID: {stance: agree|partial|disagree, why}}`. Add separate agent findings only
for concerns Qodo did not already report. Preserve original IDs, category/severity and reviewed SHA.
For each weakened test or untested source file, explain whether existing coverage holds (name it)
or what test is missing. A green badge or zero findings does not establish complete coverage.

## Write behavior lines, then prove them

The `behavior` section is the readable diff of promises, interfaces, config, data and tests.
Group by user/caller capability, then file and hunk. Write one concrete claim per line:

- `k: "+"`: a new promise; `"-"`: a removed promise; `"~"`: a changed value/default/degree.
- `kind`: behavior, interface, config, data or proof. Context uses `k: " "`.
- Every changed claim needs `ev: [{side: "new"|"old", from, to}]` touching actual changed lines.
  An evidence row may name another path in the same PR. Use old-side ranges for removals.
- Link the same capability across files with a shared `link` and explain it in `links`.
  Associate a concern with its real `finding` ID. `kept` records promises the change preserves,
  with actual code/test proof; do not infer preservation from silence.

Cover the important/read-tier changes and disclose omissions. Inspect the engine's coverage and
warnings; a cited range proves location, so independently verify that its code supports the prose.
Use [the minimal example](example-enrich.json) for a synthetic return-value change. Replace every
identity, path, range and claim before applying it to a live session.

# Finding results and local run metadata

Local review and the PR resolver share the default Finding object: `id`, `title`, `description`,
`category`, `action_level`, `attribution_status`, `git_sha`, `location` (`file_path`, `start_line`,
`end_line`, `side`), and `evidence.citations` (each citation's `source_type` and `source`).
Unavailable values are null. Use the location to inspect affected code and preserve the original ID.
Each finding appears once in the local `findings` inventory; lifecycle buckets contain IDs.

Local `review_agent_comment` is a stored reviewer-to-author message: general feedback, concerns,
questions, and feedback on the approach, design or scope. It is separate from findings and
execution metadata. Default and extended output both return it. Checkpoint reuse returns the
stored comment without running another reviewer. Null means no comment was produced; older
artifacts can omit the field. Read the summary alongside findings and coverage, rather than
treating it as proof of complete coverage or a replacement for code locations and evidence.
The producer aims for at most 400 words and caps new comments at 5000 characters. Clients preserve
the stored Markdown and older comments; they do not regenerate, trim or reinterpret the message.

Local-only `meta.local_review_ids` maps finding IDs to their original local review IDs for status
writes. Retained findings can belong to different reviews. Look up each ID and group authorized
status writes by that review ID. The map survives default/extended collection and result reuse.
If a reference is unavailable, report it; do not substitute the current run ID or invent a value.

For stored supporting detail, confirm `--extended` in `qodo review --help` and use it with a review
or with `qodo review status <operation-id> --extended --json`. It adds `location.code_snippet`,
`evidence.explanation`, fuller citation text/context, and dismissal reasons/explanations. It only
changes output detail; it does not deepen or rerun a review. Collect the accepted operation for more
detail instead of submitting it again. Fix instructions and internal reviewer decisions are excluded
in both modes; use the finding's impact, code location and evidence to choose the correction.

Local-only `meta.run` reports the run ID, requested/effective effort, reviewed base/commit/tree SHAs,
timing, and separate safety-net/primary passes with actual component outcomes (`completed`, `skipped`,
`failed`, or analytics-only `observed`). Available analytics add component duration and model names;
missing analytics are unknown. `agent_statuses_reported: false` means outcomes were unavailable.
The new local producer runs one primary pass with author context and reports no safety-net pass.
Older deployments can report both passes; use the returned outcomes instead of assuming a pass count.
The tree SHA identifies the submitted working tree; commit SHA alone need not include uncommitted edits.
A reused result has no passes or new effective effort and records prior coverage under `reused_from`.
Legacy `meta.reviewers.ran` / `.skipped` reflect configured reviewer dimensions, not actual execution;
prefer the new pass outcomes when present. `meta.safety_net.reinjected` records findings restored by
the safety pass. Report material failed/skipped components and attach missing input where applicable.

Older engines can omit metadata or return full objects in lifecycle buckets. Read their available
IDs/details, preserve retained open findings, and report missing coverage or execution information.
Null evidence means unavailable; an empty citations list contains no recorded citations.

## Inventory and analysis

`finding_state.introduced` and `finding_state.still_open` identify current obligations.
`resolved` and `dismissed` identify settled findings. Current buckets contain IDs.
Older buckets can contain full objects. Preserve the same original IDs in either shape.
Do not label a carried finding newly introduced because its wording changed.

Inspect both `finding_state.complete` and `meta.coverage.complete`.
Inventory completeness and assessed coverage are separate from the number of open findings.
A complete assessment can retain blockers.
Missing metadata does not establish completion, successful persistence or reusable coverage.
Read all warnings and report failed/skipped required components.

`meta.analysis.mode` reports `full`, `incremental` or `reused`.
Reused means the same reviewed snapshot and compatible context, not that earlier open findings disappeared.
The CLI retains submitted patch/checkpoint state privately and advances eligible completed checkpoints during collection.
Failed or older completions cannot replace a newer checkpoint.
Do not fabricate checkpoint identity or infer serving support from newer source tests.

Prefer incremental continuation under the main Skill's rules.
Keep the intended base, scope and requested effort stable when appropriate.
Refresh context honestly. Do not add a manual full-review trigger merely because notes changed.
The Engine can decline reuse when it cannot establish compatible evidence.
Report the returned fallback reason and actual coverage rather than inventing a promise of reuse.
`--full`, when supported, requests a fresh full assessment, not greater effort.
`--extended` requests stored detail, not another assessment.
Older Engines can omit analysis fields. Do not claim reuse or execution details they did not report.

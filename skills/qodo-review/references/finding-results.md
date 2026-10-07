# Finding results and local run metadata

Local review and the PR resolver share the default Finding object: `id`, `title`, `description`,
`category`, `action_level`, `attribution_status`, `git_sha`, `location` (`file_path`, `start_line`,
`end_line`, `side`), and `evidence.citations` (each citation's `source_type` and `source`).
Unavailable values are null. Use the location to inspect affected code and preserve the original ID.
Each finding appears once in the local `findings` inventory; lifecycle buckets contain IDs.

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
The tree SHA identifies the submitted working tree; commit SHA alone need not include uncommitted edits.
A reused result has no passes or new effective effort and records prior coverage under `reused_from`.
Legacy `meta.reviewers.ran` / `.skipped` reflect configured reviewer dimensions, not actual execution;
prefer the new pass outcomes when present. `meta.safety_net.reinjected` records findings restored by
the safety pass. Report material failed/skipped components and attach missing input where applicable.

Older engines can omit metadata or return full objects in lifecycle buckets. Read their available
IDs/details, preserve retained open findings, and report missing coverage or execution information.
Null evidence means unavailable; an empty citations list contains no recorded citations.

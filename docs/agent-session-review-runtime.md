# Managed review product profile

Maintainer contract for the component in `skills/qodo-agent-session-review/runtime/`.
User-facing workflow instructions live in that skill's SKILL.md. Use its skill-relative launcher:

```sh
python3 -B skills/qodo-agent-session-review/scripts/launch.py review org/repo#123 --collect-only
python3 -B skills/qodo-agent-session-review/scripts/launch.py serve --session latest
python3 -B skills/qodo-agent-session-review/scripts/launch.py refresh --session latest
python3 -B skills/qodo-agent-session-review/scripts/launch.py export --session latest --out /tmp/review.html
```

The launcher selects product mode, CLI/version/authentication gates and UTF-8 automatically.
It can find an existing user-owned CLI under `QODO_HOME/bin` without installing anything.
The official Windows batch fallback uses its adjacent CLI module with Node directly, preserving
UTF-8 JSON-file paths and metacharacters without a shell; native executables stay native.
The engine can also be invoked with `-m cockpit` for tests after setting PYTHONPATH to the runtime.
Legacy standalone migration is disabled in this packaged profile. Keep existing external
data roots; any owner-led migration belongs to the separate standalone workflow.

The global `--product` flag precedes the command. Direct `-m cockpit` invocations inside this skill also select product mode; omitting the flag cannot enable legacy provider reads or writes. A collected product session records `product: true`; refresh and serving retain that boundary. The server that starts in product mode rejects publishing even when its session picker opens an older standalone session. Retained standalone library implementations are not supported skill entrypoints or provider fallbacks.

The local server generates an ephemeral access key for each start and delivers it directly to the opened browser in a fragment. The bootstrap removes the fragment, exchanges it for an HttpOnly same-site browser cookie and opens the review. The key is neither logged nor written to disk; a restart invalidates prior access. Product data, media and Ask requests require browser admission as well as Host/Origin checks. An unauthenticated health endpoint contains no review data. With `--no-open`, browser admission stays closed; restart without that option to open the review. This isolates other unauthenticated local clients, not processes already able to read the owner's browser or CLI credentials.

`QODO_AGENT_SESSION_REVIEW_HOME` selects mutable data outside the package; legacy `REVIEW_COCKPIT_HOME` and `PR_COCKPIT_HOME` remain lower-priority aliases. Existing config, session directories, custom styles and optional memory remain compatible. Fresh product defaults disable memory and automatic memory commits; explicit existing user configuration wins. Use `-B` or `PYTHONDONTWRITEBYTECODE=1` so installed resources remain read-only. `QODO_AGENT_SESSION_REVIEW_CLI` selects an explicit CLI executable, ahead of the legacy `REVIEW_COCKPIT_QODO` alias and PATH. It does not select credentials or deployment.

When no home override is set, an existing runtime-local `config.local.json` external `home` pointer is retained. Otherwise fresh data uses `~/.qodo/agent-session-review`; when that directory is absent and `~/.qodo/review-cockpit` exists, the earlier directory stays selected. A malformed pointer or old runtime-local sessions require explicit owner recovery rather than silently opening an empty new home. No data is moved automatically.

Product collection discovers the exact registered repository and provider host, reads capabilities, observes the change revision, then reads bounded provider-evidence pages through the Qodo CLI. Each normalized PR retains canonical identity, context, capabilities, every page envelope, continuation cursor and completeness. Files retain patch evidence; provider threads remain visible as evidence. An unavailable section is distinct from an exhausted empty section. Revision mismatch stops the collection; rerun after observing the new change. There is no provider-client fallback. Registered GitHub paths accept case variants with ambiguity checks; other providers retain exact registered case. The same repository full path on different provider/hosts must be reviewed in separate sessions, even for different PR numbers; product collection rejects this combination before associations and does not migrate keys. One product operation shares a maximum of 96 managed calls and 180 seconds across all changes, findings, notes and secondary reads; each subprocess timeout is capped by the remaining time. A new collection that reaches the limit retains already collected changes, requested/omitted refs and an explicit incomplete-session marker; previews and badges cannot treat that subset as the whole package. Refresh can retry the original requested refs. Thrown required-read/auth/revision/budget/enrichment errors reject a saved refresh and preserve its previous snapshot. Successful optional partial reads keep new observed evidence with explicit gaps/cursors and independent local notes, as Sagi selected in KB-2043.

The Work Package source-evidence disclosure shows incomplete and unknown sections. It also explains the bounded related-work search. Qodo review evidence retains the stored run, status, reviewed commit, completeness and truncation. Comments can contribute findings but cannot establish an authoritative complete review. Local quality remains unknown when patch evidence is unavailable or incomplete, independently of the authoritative Qodo run. Contract source excerpts retain identity, resolved commit, freshness, truncation and continuation metadata; wrong immutable commits are refused and partial/mutable reads never prove completeness or absence. Merge Risk is Agent Session Review's estimate; its approval output is a preview, and this profile cannot submit it.

Managed finding coordinates are qualified separately from origin: a current-code anchor needs the exact observed head, collected path, positive line and a known diff side. Before-PR and unknown-origin findings retain the stricter new-side rule; known hosted `git_pr` findings can anchor to either side of the current diff. A head SHA alone does not identify an unknown-origin finding’s old comparison base. Older or unknown revisions keep their original path/SHA/side visible without claiming a current-code link. Unknown origin/type stays unknown. Previously saved product snapshots receive the same presentation qualification without rewriting the saved evidence. Saved local results use `meta.local_review_ids` per finding, with legacy fallback. Original stored review context is reused when available; an unknown origin record cannot borrow a later review’s commit or time. Optional comment badges use the existing informational/low severity.

The Work Package Verdict differs by mode. The standalone cockpit says Ready to merge only when every merge threshold in Customize › Verdict settings is met; the thresholds are stored under the `cockpit:verdict-rules` app-state key, and a threshold that has not been read yet counts as not met. CI that is still running, or a PR without a successful check (skipped and neutral checks are not passes), does not meet the CI threshold. A draft, merged or closed PR is never ready to merge. When GitHub reports no review decision (the repository does not require reviews), a human approval of the current head, with no change still requested, meets the human-review threshold. The "As of" time is the live check only when every PR read fully; product mode dates its recommendation by collection. The Verdict states when its data was read (the live check, else collection), so it says whether the package was ready to merge as of then. Product mode has no merge thresholds and no settings for them: its headline is the risk review's recommendation, which never claims merge readiness. In product mode, incomplete CI or human-review evidence shows a lower bound ("at least N") with "coverage unknown", never a pass. Neither mode shows Merge Risk in the Verdict; the Risk page carries it.

Provider publishing, replies and thread resolution are disabled before live preflight or dry-run execution. Local notes always have `post: false`. Accept/dismiss marks are local annotations; they do not change Qodo stored finding dispositions. Export writes a local file; sharing that file is a separate user action. A new snapshot reader is seeded from exported local feedback; their saved browser edits/removals and read/verdict state survive reload. Served sessions continue to use canonical local server events.

`app/styles/package.html` includes `{{PACKAGE_SCRIPT}}`; `cockpit.styles.render` reassembles it from `package.js` before normal substitutions. Both served and standalone exports use this renderer. Maintain and test all three resources together; the renderer prepends the local-state helper. Neither file exceeds the 524,288-byte bundle limit.

Optional content is self-contained: `cockpit walkthrough --builder FILE --triage-dir DIR` imports an existing builder/triage artifact after validation. Without those artifacts, those pages say that no content was generated. The schema and validation live in `cockpit/walkthrough.py`; no personal skill installation is required. Ask Qodo remains optional and uses the existing constrained local-agent tool loop; startup does not install or launch a coding agent.

Current qualification limits: provider identity fixtures cover six provider families; live evidence is currently GitHub only. Related-work lookup reads at most ten open and ten merged changes per repository and reports that bound. Reviewer suggestions use bounded recent review history and label path ownership/similarity unqualified. Provider thread evidence is retained but no thread actions are available. Existing optional scanner parsers consume managed comments/checks/annotations; unknown upstream data does not establish clean scans. Full air-gapped rendering is not claimed: Mermaid and fonts still use the existing public CDNs.

Product `enrich` accepts an authored JSON file from any location. After a successful application, it atomically saves the merged authored input as the session's `enrich.json` so refresh can reapply it. Successive object fields merge, omitted fields remain, and supplied lists replace earlier lists (including valid empty-list clears). Derived excerpts and normalized source revisions are not saved as new authored intent.

Unchanged authored findings retain IDs across insertion, reordering and refresh. Their identity
map survives refresh, and IDs referenced by local events are not recycled for new findings.
Supply an existing finding's `id` when changing its content while retaining its notes/verdict.
Finding portal links support encoded opaque IDs and preserve view queries; dismiss-action links
are not exposed as view actions. Local imports publish atomically before retiring old copies.

Product enrichment and refresh share a per-session `.cockpit-writer.lock` directory. A competing writer gets a busy error before changing the snapshot or authored file; retry after the active operation finishes. Refresh reuses its own guard when reapplying enrichment. Local note/mark events remain append-only and independent of this guard and snapshot rollback. The guard is released on errors. If a process crashes and leaves it behind, inspect its `owner.json` PID and confirm that no enrichment or refresh for that session is still running before manually removing the guard directory. Agent Session Review never automatically deletes a possibly live writer's guard.

Product HTTP operations and snapshot writers also share activity leases under the sessions directory's `.cockpit-active/`; parallel browser requests remain concurrent. Trash takes exclusive access and refuses an active operation from another tab or server. Its guard remains outside the moved package, so deletion cannot invalidate cleanup. A crashed process can leave a stale lease; verify that no operation still owns that session before manually removing it. App settings use an OS-released cross-process lock on both POSIX and Windows. Authored risk line references are syntax-checked and verified against one collected file's visible new-side source; unverified context retains its original numbers but renders as a file-only reference with a warning.

Ownership: this component and its behavior tests are maintained in qodo-skills. See [component maintenance](../skills/qodo-agent-session-review/references/packaging.md) and `test/agent-session-review/README.md`. This contract was adapted from the original Cockpit component, now maintained as Agent Session Review, and retains its component terms in runtime/LICENSE.

JSON requests are limited to 2,000,000 bytes before reading or parsing. Event offsets and CLI
session names are validated; CLI sessions cannot escape their configured directory. Finding
verdicts and memory attribution use PR plus finding ID, with unscoped legacy events matched
only when unambiguous. Optional OKF mutations serialize across threads and server processes;
this does not change the separately accepted failed-refresh memory-draft limit.

Known Upwind Secrets Scan Value cells are redacted before saving source text, raw evidence and
imported events, and before presenting/exporting older snapshots. Coordinates and source identity
remain intact; `source_redactions` discloses the change. This is targeted protection for detected
scanner values, not a general secret detector or permission to share a review without checking it.

HTML exports embed referenced story media only, including nested images and video. Resolved local paths must remain inside that session’s media directory; unreferenced files and external symlinks are excluded. Existing CDN/font and remote-media behavior remains unchanged.

Optional-memory failure limit (Sagi accepted for V1 in KB-2047): memory is off by default. When explicitly enabled, a failed refresh restores the review snapshot but may leave an unconfirmed memory draft or auxiliary index change. Snapshot rollback does not promise a shared-memory transaction. Local notes/events remain independent and preserved.

Refreshing an existing product session preserves the latest-session selection on success and failure; a new collection still selects its new session. Scanner check annotations retain their reported end line. One-Page story media uses the same reference selector as the full-app export, including video links and before/after images; other layouts retain their existing gallery behavior.

Saved-local findings use the same current-coordinate proof as managed findings: the observed
commit, collected path, known diff side and positive line must agree. Older snapshots are
qualified for presentation without rewriting them. Detected-after-merge is a terminal source
reason, not evidence of a verified fix; its reason survives the public view. ID-less dictionary
entries in local disposition buckets use the same synthetic display identity as their details.
Unknown impact risk and unavailable closed-comment severity remain Unknown. Explicit inline
severity can qualify a closed summary item. Repeated knowledge titles in one enrichment reuse
one draft/candidate. Reviewer lookup takes the session writer guard before snapshot work.

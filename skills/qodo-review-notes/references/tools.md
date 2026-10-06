# Tool access

Use live Qodo schemas as the contract. Tool names below are the shared wire names; connected MCP
tools may add a server prefix. Do not construct provider URLs, handle API keys or call HTTP from a skill.

## CLI

Run `qodo --version` without provenance flags, then use:

```sh
qodo read whoami --json --skill qodo-review-notes --skill-version 1.0.0 --distribution skills-sh
qodo read tools review-notes --json --skill qodo-review-notes --skill-version 1.0.0 --distribution skills-sh
qodo tools help review-notes --json
```

`qodo read tools` lists only reads. Use the non-mutating `qodo tools help` catalog to discover write
schemas and the local capture capability. If `qodo` is absent from PATH, try `~/.qodo/bin/qodo`
(or the configured Qodo home) before diagnosing a missing installation. Use `qodo-setup` for setup
or explicit missing credentials; do not inspect secret stores or switch the deployment's update origin.
An unavailable/gated tool is an unavailable feature, not a successful empty lookup. Use the CLI's
catalog refresh option once if the runtime was just upgraded; do not loop or switch accounts.

Catalog entries provide `command`, `readCommand`, `parameters`, `access` and `requiresUserApproval`.
For PR `save-pr` and `prepare-pr`, require `localGitCapture: true`. Reads use `qodo read review-notes …`;
writes use `qodo review-notes …`, with a stable `--idempotency-key` for each intended write.
Schema fields use snake_case; flags use kebab-case. `document` is a JSON object, supplied with
`--document` or inside `--args`. Serialize structured arguments safely rather than assembling
Markdown or issue text into a shell command. The CLI owns all transport and credentials.

Retain two distinct keys:

- **Transport idempotency key:** `--idempotency-key` identifies a single write request, including
  publication/binding/update calls. Retry the same request with the same key; changed arguments need a new key.
- **Creation key:** the tool's `creation_key` identifies initial record creation across sessions and
  retries. Persist it before sending. It is not needed when editing a known record ID.

### Example input for local CLI preparation

This JSON is an argument object, not an HTTP request. Replace the example path and retry key with
the actual task's values. It deliberately omits Git fields that the capable CLI captures locally.

```json
{
  "creation_key": "retained-unique-creation-key",
  "expected_revision": 0,
  "document": {
    "target_repo_path": "example/api",
    "base_branch": "main",
    "no_track_reason": "Independent fix with no wider delivery effort",
    "content_markdown": "## Intent\nCorrect the boundary check.\n\n## Review focus\nCheck equality at the limit."
  }
}
```

Pass the serialized object to the discovered `prepare-pr` command with `--args`, `--json` and
`--idempotency-key`. On an edit include `notes_id` and the latest expected revision; creation
SHA is preserved by the runtime. Explicit canonical repository IDs can be supplied instead of paths.

## Git providers and repository identities

Use the platform provider vocabulary: `github`, `gitlab`, `bitbucket`,
`bitbucket_datacenter`, `azure`, and `gerrit`. GitHub Enterprise and self-managed
GitLab use their registered hostnames. Copy the registry's opaque `repoRef` into
`repo_ref`; `providerRepoId` is a native provider ID and can differ. Never reconstruct
GitLab or Bitbucket Data Center instance prefixes or replace platform names with
LiteGit names such as `bitbucket_server` or `azure_devops`.

The capable CLI resolves HTTPS/SCP/SSH remotes using registered identities, including
GitLab subgroups, Bitbucket Data Center's `/scm/` prefix, Azure's organization/project
paths and Gerrit's host-qualified project names. Azure SSH/legacy URL forms and Gerrit
custom ports or HTTP `/a/` paths are lookup evidence, not canonical IDs. Project-path
case is preserved. If several registered candidates match, select the actual repository
explicitly; never pick the first result. With MCP, use `resolve-repository` separately
for source and target, then copy its returned provider, hostname, path and `repo_ref`.
No direct Git-provider requests are needed for registry resolution.

## MCP

Discover `tools/list` on the trusted connected Qodo managed-tools server. Use the available names
and schemas. MCP performs the same platform operations as CLI; it does not read local Git.
Supply `document.commit_sha_at_update`, current source/base branches and both canonical repository
identities yourself. Creation SHA may be omitted; the runtime sets it to that captured existing HEAD.
Never fabricate a SHA, issue ID, repository identity or track selection.

Mutating `tools/call` requests require the same stable transport key in request `_meta`:

```json
{
  "name": "review-notes-bind-pr",
  "arguments": { "notes_id": "actual-notes-uuid", "pr_number": 5443 },
  "_meta": { "io.qodo/idempotency-key": "retained-unique-bind-key" }
}
```

Use the host's MCP call interface and approval mechanism. If it cannot send the required `_meta`,
use the authenticated CLI for writes instead; do not omit write idempotency or invent a credential path.
Collect a returned operation/task to completion using the server's declared protocol before claiming
publication or binding succeeded. Read typed errors even when a transport call returned HTTP success.

## Operations

| Tool suffix | Operation |
|---|---|
| `resolve-repository` | Exact repository path/host to the registered `repo_ref`; no provider request. |
| `find-tracks` | Published track candidates by issue, repository, title and status; cursor pagination. |
| `get-track` | Published or latest draft; optional connected PR metadata. |
| `save-track` | Full-document create/update, with explicit expected revision and optional publication. |
| `publish-track` | Publish the specified latest saved track revision. |
| `save-pr` | Full-document create/update; optional PR number; publication or draft. |
| `prepare-pr` | Save and publish final PR notes atomically; publication receipt and next action. |
| `get-pr` | Notes ID or full target-repository/PR identity; published or draft authoring read. |
| `publish-pr` | Publish a specified saved revision without recapturing HEAD. |
| `bind-pr` | Associate active published notes with a PR in their saved target repository. |
| `for-pr` | Both published scopes for a bound PR, with actual current HEAD and validation applicability. |
| `history` | Authorized saved versions for a track or PR, with bounded pagination. |

All wire names start `review-notes-`. For publication use `record_id` and `revision`; for binding use
`notes_id` and positive `pr_number`. Query by PR requires `provider`, `provider_host`, `target_repo_ref`
and `pr_number`; combined reads also require `current_head_sha`. These are identities, not prose searches.

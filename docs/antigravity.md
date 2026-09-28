# Qodo plugins for Antigravity

Qodo generates native Antigravity plugins from the same canonical skills as its other adapters:

| Plugin directory in a release | Skills |
|---|---|
| `antigravity-plugins/qodo/` | `qodo-setup`, `qodo-codebase-wisdom`, `qodo-review`, `qodo-review-resolver` |
| `antigravity-plugins/qodo-standards/` | `qodo-get-rules`, `qodo-manage-standards` (optional) |

Each root has `plugin.json`, a release-identifying README, and complete skill directories with
supporting references. The plugin does not bundle the Qodo CLI, MCP servers, hooks, rules, or
permission grants. The CLI continues to own login, credentials, tool discovery, and execution.

## Availability and validation status

The adapter targets the [documented Antigravity plugin layout](https://antigravity.google/docs/plugins/)
and [Agent Skills format](https://antigravity.google/docs/skills/), checked on September 28, 2026.
Automated tests cover packaging, canonical content, provenance, and release integration. Native
Antigravity install/discovery/runtime checks remain a release acceptance gate, not a result of CI.
Do not describe this as a curated Google listing or host-verified integration before that evidence exists.

Source PRs change adapter code, tests, and documentation, not generated directories. The subsequent
release PR creates the plugin directories; use an immutable release that contains them. Older releases do not.
This adapter adds no marketplace submission workflow or new standalone release asset. Download
the source archive from [Qodo skills releases](https://github.com/qodo-ai/qodo-skills/releases),
or check out that release's exact tag, and retain its tag/commit for updates and rollback.

## Install

Use one installation channel and scope per host. Check existing Qodo skills before installing;
do not layer a native plugin over a skills.sh, legacy, or enterprise-managed copy. Preserve user
edits and remove a conflicting copy only through its existing owner with the user's approval.
This plugin adapter does not automatically migrate installed skills or change agent routing in
the Qodo CLI.

For Antigravity CLI, from the unpacked release directory:

```sh
agy plugin install ./antigravity-plugins/qodo
agy plugin list
```

Only if Qodo Standards is wanted:

```sh
agy plugin install ./antigravity-plugins/qodo-standards
```

The CLI manages its installed plugin files under `~/.gemini/antigravity-cli/plugins/`.
For Antigravity 2.0 or the IDE, place just the selected plugin directory in one scope:

- Workspace: `<workspace>/.agents/plugins/qodo/`.
- Global: `~/.gemini/config/plugins/qodo/`.

The resulting directory must contain `plugin.json` directly, not another `qodo/` wrapper. Install
Standards separately under the sibling `qodo-standards/` directory when requested. These locations
come from Google's plugin documentation; do not substitute the CLI's filesystem location for the IDE's.

Start a new conversation and inspect the host's loaded skills. Ask it to use `qodo-setup`, then
`qodo-codebase-wisdom` for a read-only question. Let the setup skill check the Qodo CLI's minimum
version and choose the existing deployment's login flow. Use the skill names shown by the host;
do not assume a plugin-qualified slash-command spelling without checking that host version.

## Update and remove

Obtain the next immutable release containing these directories and keep the same selected packages
and scope. The plugin README identifies the source release; the manifest intentionally has no
version field. The Qodo CLI's runtime updater is not this plugin's installer or updater.

For CLI replacements, preserve any local edits first, then use `agy plugin uninstall qodo` and
install the new release's `antigravity-plugins/qodo` directory. Recheck `agy plugin list` and the
loaded skills in a new session. Update Standards separately only if it was already selected.
For manual IDE installs, preserve edits and replace the selected plugin directory as a whole;
do not merge old and new trees and leave retired skill files behind. Removal targets only that
plugin's directory, never a shared skills/configuration directory.

## Maintainer acceptance checklist

Record the Antigravity surface/version, Qodo CLI version, release tag/commit, installation scope,
and observed skill names for each tested surface:

- Fresh core install discovers exactly four skills and can open their bundled references.
- Standards stays absent until explicitly installed, then adds exactly its two skills.
- Setup and one read workflow execute through the Qodo CLI with the recorded deployment.
- Any write workflow still requires the user's authorization; do not write merely to test discovery.
- Replacing a release and starting a new session loads the new bytes without widening membership.
- Disable/removal affects only the selected plugin; no duplicate or shadowed Qodo skills remain.

Run these checks separately in the CLI and IDE/2.0 before claiming support for each surface.
`npm test` checks the documented packaging contract but is not a native Antigravity validator.

## Manifest and runtime choices

The manifest emits only `name` and `description`. Google's embedded schema permits only those
fields, while its example recommends a `$schema` URL that returned 404 when checked, and
[Google's own plugin](https://github.com/google-gemini/gemini-skills/blob/main/plugin.json) uses
additional metadata. The conservative subset avoids depending on those inconsistencies; it is
not a claim that every host rejects `version`.

Generated Qodo invocations use `--distribution marketplace --host antigravity` for both surfaces.
Here `marketplace` denotes host/manual-plugin lifecycle ownership, not a curated listing.
Do not invent an unsupported distribution value. The inspected Qodo CLI 1.1.1 accepts this provenance
but suppresses update notices for unrecognized marketplace hosts. Antigravity-specific notice/update
guidance and ownership migration are separate runtime work; plugin updates remain manual here.
The enterprise schema-v1 archive remains unchanged and does not gain a native Antigravity projection.

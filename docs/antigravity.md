# Qodo plugins for Antigravity

Qodo generates native Antigravity plugins from the same canonical skills as its other adapters:

| Plugin directory in a release | Skills |
|---|---|
| `antigravity-plugins/qodo/` | `qodo-setup`, `qodo-codebase-wisdom`, `qodo-review`, `qodo-review-resolver` |
| `antigravity-plugins/qodo-standards/` | `qodo-get-rules`, `qodo-manage-standards` (optional) |

Each root has a Marketplace-ready `plugin.json`, a square transparent logo under `assets/`, a
release-identifying README, and complete skill directories with supporting references. The plugin
does not bundle the Qodo CLI, MCP servers, hooks, rules, or permission grants. The CLI continues to
own login, credentials, tool discovery, and execution.

## Availability and validation status

The adapter targets the [documented Antigravity plugin layout](https://antigravity.google/docs/plugins/),
[Agent Skills format](https://antigravity.google/docs/skills/), and Google's partner Marketplace
publishing contract, checked on October 7, 2026. Automated tests cover required publishing metadata,
the logo contract, packaging, canonical content, provenance, and release integration. Native
Antigravity install/discovery/runtime checks remain a release acceptance gate, not a result of CI.
Do not describe this as a curated Google listing or host-verified integration before provider-visible
evidence exists.

Source PRs change adapter code, tests, and documentation, not generated directories. The subsequent
release PR creates the plugin directories; use an immutable release that contains them. Older releases do not.
Contributors can run `npm test` before those directories exist: the
[local test runner](../CONTRIBUTING.md#test-locally) creates and cleans up an isolated release preview.
Prepared-release artifacts are checked without regeneration so drift cannot be repaired by testing.
Submission and Google review happen outside this repository; the release still contains the exact
reviewable plugin tree instead of a separate archive. Download the source archive from
[Qodo skills releases](https://github.com/qodo-ai/qodo-skills/releases), or check out that release's
exact tag, and retain its tag/commit for updates and rollback.

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

In Antigravity 2.0, open **Customizations → Plugins → + Install from URL** to install the same
plugin from a supported Git repository URL or local path. A curated Marketplace card becomes the
preferred install path only after Google makes the submitted listing visible.

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
and scope. The plugin manifest and README identify the source release; every published update bumps
the manifest version through the normal release PR. The Qodo CLI's runtime updater is not this
plugin's installer or updater.

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

The public plugin page historically described only the core `name` and `description` fields. The
partner Marketplace publishing guide requires `displayName`, `version`, `logo`, `suggestedPrompts`,
and `author`, and recommends category, search, homepage, repository, and license metadata. Generated
manifests now carry that complete publishing projection. Card descriptions and starter prompts live
in `distribution/catalog.json`; shared author, URL, license, keyword, and version values retain their
existing canonical sources. Starter prompts reuse the intent of the existing skill prompts but avoid
host-specific `$skill` syntax.

Generated Qodo invocations use `--distribution marketplace --host antigravity` for both surfaces.
Here `marketplace` denotes host/manual-plugin lifecycle ownership, not a curated listing.
Do not invent an unsupported distribution value. The inspected Qodo CLI 1.1.1 accepts this provenance
but suppresses update notices for unrecognized marketplace hosts. Antigravity-specific notice/update
guidance and ownership migration are separate runtime work; plugin updates remain manual here.
The enterprise schema-v1 archive remains unchanged and does not gain a native Antigravity projection.

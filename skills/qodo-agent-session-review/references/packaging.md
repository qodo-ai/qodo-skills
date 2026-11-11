# Component ownership and delivery

Agent Session Review's canonical engine/UI lives in this repository at `skills/qodo-agent-session-review/runtime/`.
Edit it directly and include its tests in the same PR. The standalone Cockpit repository (`qodo-ai/pr-review-cockpit`) is the historical
origin, not a build, installation or maintenance dependency. No source checkout, importer, runtime
commit pin or second-repository PR is required. Installed resources remain immutable; updates use
the existing skills distribution and preserve external reviewer sessions/config.

The separate optional `qodo-agent-session-review` package includes the skill, launcher, runtime, demo fixtures and
component LICENSE. It has no activation hook or installation-time startup. The stdlib launcher locates
resources relative to itself and does not clone, fetch or update them at runtime.

## Maintaining and testing

Run `node scripts/agent-session-review-runtime.mjs` to validate current maintained source. The source-local policy
in `scripts/agent-session-review-runtime-policy.json` rejects private/state files, internal markers, unsafe paths,
unreviewed assets and resources over 512 KiB. It verifies component terms and the reviewed favicon.
Edited source is validated as written, never silently sanitized. Inventory hashes are computed from
current source and compared across generated packages; existing release manifests provide package
provenance. There is no manually refreshed upstream hash receipt.

Runtime behavior tests and fixtures live in `test/agent-session-review/`. Run `node scripts/test-agent-session-review-runtime.mjs`
for the isolated Python 3.9+ suite, or `npm test -- --base <base-sha>` for the full source preview,
runtime, packaging and release checks. The runner keeps HOME, temporary files and reviewer data
separate from personal state. Tests require no standalone checkout or historical Agent Session Review Git objects.
CI owns preview generation; the release process owns versions and generated host packages.

Existing runtime files and the migrated legacy `test/agent-session-review/tests/test_cockpit.py` retain their structure
under the maintained-component line-count exception. New tooling and instructions keep the repository's
500-line guideline. The 512 KiB per-resource bound remains unchanged.

## Component terms

Canonical skill/launcher/packaging automation follows this repository's MIT license. Agent Session Review runtime
and its migrated original tests preserve their component LICENSE and Copyright Qodo terms. Optional
manifests declare `MIT AND LicenseRef-Qodo-Cockpit`; root MIT does not relicense the component.
See skill-local NOTICE, runtime/LICENSE and test/agent-session-review/LICENSE. Core/Standards terms remain unchanged.

## Install scope and current managed compatibility

Choose the optional Agent Session Review package explicitly; core and Standards membership/license stay unchanged.
Generated roots are packages/qodo-agent-session-review (Claude), codex-packages/qodo-agent-session-review,
antigravity-plugins/qodo-agent-session-review and kiro-power-agent-session-review. Native installers consume these roots
as complete packages. For Kiro, use Powers > Add Custom Power > Import power from a folder and
select the complete kiro-power-agent-session-review directory; see the [official local installation guide](https://kiro.dev/docs/powers/installation/#from-local-path).
No hooks start the server; invoke the skill after selecting its installation.
Both marketplace indexes and external provider listings exclude this early beta
(`providerListed: false`). It is installed only when explicitly selected.

With Qodo CLI 2.3.0 or newer:

```sh
qodo skills install qodo-agent-session-review
```

Select the intended agents when prompted. Installation is global unless `--project` is selected.
The CLI chooses the verified public or private distribution and maintains all package resources
under existing automatic-update preferences. A compatible private deployment must serve this
catalog release before its new name becomes available there.

For a supported skills.sh host, the existing explicit single-skill route is:

```sh
npx skills add https://github.com/qodo-ai/qodo-skills --skill qodo-agent-session-review --agent <host>
```

Run installation only with covering user authorization and use an approved release/source version.
No separate Agent Session Review checkout is needed. Start a new host session, invoke qodo-agent-session-review explicitly,
then use the skill-relative launcher. Do not overwrite a standalone review-prs alias or data home.

Agent Session Review stays outside legacy core/Standards bundles (`managed: false`), preserving
existing clients and ownership. Its complete-resource catalog is delivered separately. Copies
installed through skills.sh or a host remain owned by that channel; do not silently migrate
them into CLI maintenance. A passive update notice does not authorize a reinstall.

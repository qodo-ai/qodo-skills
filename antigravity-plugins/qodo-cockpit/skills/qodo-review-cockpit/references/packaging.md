# Component ownership and delivery

Cockpit's canonical engine/UI lives in this repository at `skills/qodo-review-cockpit/runtime/`.
Edit it directly and include its tests in the same PR. The standalone Cockpit repository is historical
origin, not a build, installation or maintenance dependency. No source checkout, importer, runtime
commit pin or second-repository PR is required. Installed resources remain immutable; updates use
the existing skills distribution and preserve external reviewer sessions/config.

The separate optional `qodo-cockpit` package includes the skill, launcher, runtime, demo fixtures and
component LICENSE. It has no activation hook or installation-time startup. The stdlib launcher locates
resources relative to itself and does not clone, fetch or update them at runtime.

## Maintaining and testing

Run `node scripts/cockpit-runtime.mjs` to validate current maintained source. The source-local policy
in `scripts/cockpit-runtime-policy.json` rejects private/state files, internal markers, unsafe paths,
unreviewed assets and resources over 512 KiB. It verifies component terms and the reviewed favicon.
Edited source is validated as written, never silently sanitized. Inventory hashes are computed from
current source and compared across generated packages; existing release manifests provide package
provenance. There is no manually refreshed upstream hash receipt.

Runtime behavior tests and fixtures live in `test/cockpit/`. Run `node scripts/test-cockpit-runtime.mjs`
for the isolated Python 3.9+ suite, or `npm test -- --base <base-sha>` for the full source preview,
runtime, packaging and release checks. The runner keeps HOME, temporary files and reviewer data
separate from personal state. Tests require no standalone checkout or historical Cockpit Git objects.
CI owns preview generation; the release process owns versions and generated host packages.

Existing runtime files and the migrated legacy `test/cockpit/tests/test_cockpit.py` retain their structure
under the maintained-component line-count exception. New tooling and instructions keep the repository's
500-line guideline. The 512 KiB per-resource bound remains unchanged.

## Component terms

Canonical skill/launcher/packaging automation follows this repository's MIT license. Cockpit runtime
and its migrated original tests preserve their component LICENSE and Copyright Qodo terms. Optional
manifests declare `MIT AND LicenseRef-Qodo-Cockpit`; root MIT does not relicense the component.
See skill-local NOTICE, runtime/LICENSE and test/cockpit/LICENSE. Core/Standards terms remain unchanged.

## Install scope and current managed compatibility

Choose the optional Cockpit package explicitly; core and Standards membership/license stay unchanged.
Generated roots are packages/qodo-cockpit (Claude), codex-packages/qodo-cockpit,
antigravity-plugins/qodo-cockpit and kiro-power-cockpit. Native installers consume these roots
as complete packages. For Kiro, use Powers > Add Custom Power > Import power from a folder and
select the complete kiro-power-cockpit directory; see the [official local installation guide](https://kiro.dev/docs/powers/installation/#from-local-path).
No hooks start the server; invoke the skill after selecting its installation.
External curated directory/provider submissions are deferred (`providerListed: false`). The
local Claude/Codex marketplace indexes intentionally expose the optional package for explicit
selection; that local discovery is distinct from an external curated directory submission.

For a supported skills.sh host, the existing explicit single-skill route is:

```sh
npx skills add https://github.com/qodo-ai/qodo-skills --skill qodo-review-cockpit --agent <host>
```

Run installation only with covering user authorization and use an approved release/source version.
No separate Cockpit checkout is needed. Start a new host session, invoke qodo-review-cockpit explicitly,
then use the skill-relative launcher. Do not overwrite a standalone review-prs alias or data home.

The current CLI/enterprise managed protocol supports only qodo and qodo-standards. Cockpit is
excluded from those legacy bundle/index projections (`managed: false`) to preserve current clients.
There is no supported `qodo agents install --cockpit` command yet. Optional managed delivery needs
a separately qualified CLI/QAR capability extension. All optional native/portable resources remain
complete; native installation and public directory visibility are separate acceptance gates.

CLI lifecycle inventory can report an unknown owner for optional skills.sh Cockpit installs;
it currently tracks the public core/Standards skill set. Use the original explicit installation
channel for authorized updates and preserve its agent/location scope. Marketplace installs remain
host-owned. A passive CLI notice does not establish Cockpit update support or authorize a reinstall.

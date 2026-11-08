# Package provenance and maintenance

The separate optional `qodo-cockpit` package includes this skill without activation hooks or installation-time startup.
`runtime-manifest.json` pins the Qodo Cockpit repository commit and every imported file's original
and sanitized SHA-256/size. `runtime/` holds the engine, app assets, shipped config and LICENSE.
The launcher locates it relative to its own installed file. No clone or network fetch occurs at
runtime. Manifest hashes are verified during import/build/tests for provenance and reproducibility;
they are not a runtime attestation or a new signed-updater trust anchor. Updates come through the existing Qodo skills distribution, never a Cockpit updater.

Canonical skill/launcher/import automation follows the qodo-skills repository MIT license.
The imported Cockpit payload remains Copyright Qodo, governed by the user's Qodo agreement or
Qodo Terms of Use, as its own `runtime/LICENSE` states. Optional Cockpit plugin manifests declare `MIT AND LicenseRef-Qodo-Cockpit`; the repository MIT
license does not relicense that payload. The skill-local NOTICE explains both components. See https://www.qodo.ai/terms/ for the Cockpit component terms.

Maintainers import only an explicit reviewed full commit SHA:

```sh
node scripts/import-cockpit-runtime.mjs --source /path/to/upstream --commit <40-hex-sha>
node scripts/import-cockpit-runtime.mjs --verify
```

The importer verifies the intended source remote, reads Git objects, rejects dirty relevant source
files, preserves LICENSE exactly, applies the pinned upstream
release manifest sanitization/scan policy and records exact hashes. It excludes real memory, sessions,
local config, caches, internal design, screenshots and install/update scripts. A committed public
demo fixture is allowed explicitly; no customer data is copied. Binary resources are rejected.
The existing 512 KiB per-file CLI limit remains in force. Imported upstream files retain their
upstream structure; newly authored packaging files remain below 500 lines.

Run source-preview `npm test -- --base <base-sha>` without editing generated packages, release
records or existing versions. CI owns preview generation; release preparation owns generated
host resources and final version/provenance stamping. Package qualification is separate from
live browser/provider acceptance and from merge/release/marketplace visibility.

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
No private Cockpit clone is needed. Start a new host session, invoke qodo-review-cockpit explicitly,
then use the skill-relative launcher. Do not overwrite a standalone review-prs alias or data home.

The current CLI/enterprise managed protocol supports only qodo and qodo-standards. Cockpit is
excluded from those legacy bundle/index projections (`managed: false`) to preserve current clients.
There is no supported `qodo agents install --cockpit` command yet. Optional managed delivery needs
a separately qualified CLI/QAR capability extension. All optional native/portable resources remain
complete; native installation and public directory visibility are separate acceptance gates.

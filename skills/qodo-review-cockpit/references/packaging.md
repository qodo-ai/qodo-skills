# Package provenance and maintenance

The core Qodo package includes this skill without activation hooks or installation-time startup.
`runtime-manifest.json` pins the Qodo Cockpit repository commit and every imported file's original
and sanitized SHA-256/size. `runtime/` holds the engine, app assets, shipped config and LICENSE.
The launcher locates it relative to its own installed file. No clone or network fetch occurs at
runtime. Updates come through the existing Qodo skills distribution, never a Cockpit updater.

Canonical skill/launcher/import automation follows the qodo-skills repository MIT license.
The imported Cockpit payload remains Copyright Qodo, governed by the user's Qodo agreement or
Qodo Terms of Use, as its own `runtime/LICENSE` states. The top-level MIT package declaration
does not relicense that payload. See https://www.qodo.ai/terms/ for the Cockpit component terms.

Maintainers import only an explicit reviewed full commit SHA:

```sh
node scripts/import-cockpit-runtime.mjs --source /path/to/upstream --commit <40-hex-sha>
node scripts/import-cockpit-runtime.mjs --verify
```

The importer reads Git objects, rejects dirty relevant source files, applies the pinned upstream
release manifest sanitization/scan policy and records exact hashes. It excludes real memory, sessions,
local config, caches, internal design, screenshots and install/update scripts. A committed public
demo fixture is allowed explicitly; no customer data is copied. Binary resources are rejected.
The existing 512 KiB per-file CLI limit remains in force. Imported upstream files retain their
upstream structure; newly authored packaging files remain below 500 lines.

Run source-preview `npm test -- --base <base-sha>` without editing generated packages, release
records or existing versions. CI owns preview generation; release preparation owns generated
host resources and final version/provenance stamping. Package qualification is separate from
live browser/provider acceptance and from merge/release/marketplace visibility.

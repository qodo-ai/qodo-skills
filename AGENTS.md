# Qodo skills repository rules

- Canonical skill behavior lives only in `skills/*/SKILL.md`.
- Marketplace adapters are generated from `distribution/catalog.json`; run
  `npm run adapters` instead of editing them.
- The `qodo` CLI owns login, credentials, transport, tool discovery, and runtime updates.
  Skills must not implement those concerns directly.
- All skill names use lowercase kebab case with the `qodo-` prefix.
- Every skill frontmatter includes `name`, `description`, and standard `metadata` containing
  `vendor`, `version`, and `recommended` string fields.
- Keep every source file below 500 lines; extract focused references or scripts when needed.
- Use Node built-ins for repository automation. Do not add a runtime dependency without a
  documented need and approval.
- Contributors edit canonical skills and catalog metadata in ordinary PRs, leaving existing
  versions and generated packages unchanged. CI builds a temporary preview; after merge,
  `Release: Prepare PR` collects changes into one bot-owned release PR. No local setup
  or commands are required for contributors.
- Only the release PR commits versions, generated packages, and `releases/v<version>.json`.
  Kiro reads the generated `main/kiro-power` and `main/kiro-power-standards` snapshots.
  Merging the release PR starts protected publication; provider visibility is checked separately.
- `npm run release:prepare` remains an optional maintainer tool for explicit minor/major releases
  and recovery. Existing skill changes default to patch; new skills use `initial` and a package minor.
- Run `npm test` and available host-native validators before handoff.
- Never push, tag, publish, submit to a marketplace, or change external state unless the user
  explicitly authorizes it.

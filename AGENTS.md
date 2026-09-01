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
- Prepare release-bound changes with `npm run release:prepare -- --summary ... --skill
  <name>=<initial|patch|minor|major>` so package, skill, adapter, and release-record versions stay
  atomic. Use `initial` only for a newly added skill.
- Run `npm test` and available host-native validators before handoff.
- Never push, tag, publish, submit to a marketplace, or change external state unless the user
  explicitly authorizes it.

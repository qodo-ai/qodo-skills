# Compatibility contract

## Supported package surfaces

| Surface | Manifest | Skill location | Update owner |
|---|---|---|---|
| Codex | `.codex-plugin/plugin.json` | `skills/` | Codex marketplace |
| Claude Code | `.claude-plugin/plugin.json` | `skills/` | Claude marketplace |
| Kiro / Agent Plugins 1.0 | `plugin.json` | `skills/` | Host power/plugin manager |
| Gemini CLI | `gemini-extension.json` | `skills/` | Gemini extension manager |

The package is skills-only. There is no `mcp.json`, `.mcp.json`, or hosted tool server.
Local agents execute the installed `qodo` binary and inherit its authenticated catalog.

## Versioning

There are two independent version streams:

- **Package version**: one semantic version shared by every host manifest and release tag.
- **Skill version**: the semantic version in each `SKILL.md`, mirrored in the distribution
  catalog. Change only when that skill's behavior or contract changes.

The package version changes for any released skill, adapter, discovery, or packaging change.
Unchanged skills keep their skill version. The release tag is `v<package-version>`.

## Compatibility rules

1. Existing CLI commands used by a released skill are a compatibility surface.
2. Additive CLI fields and tools are safe; removals or renames require a staged skill
   migration.
3. Release runtime support before releasing a skill that depends on it.
4. A skill detects missing login separately from a stale or missing catalog.
5. Host-only metadata may differ, but it must not change workflow semantics.
6. No adapter may contain a second copy of a `SKILL.md` body.
7. Source installs track the repository; stable marketplace listings should track releases.

## Support tiers

- **Validated**: manifest passes the host's native validator and a local install smoke test.
- **Package-ready**: manifest is generated and schema-checked, but its host is unavailable in
  CI or locally.
- **Listed**: the package has passed the marketplace owner's external review and is publicly
  discoverable.

Do not describe package-ready as listed, or a source install as marketplace acceptance.

# Compatibility contract

## Supported package surfaces

| Surface | Manifest | Skill location | Update owner |
|---|---|---|---|
| Codex | `packages/<name>/.codex-plugin/plugin.json` | `packages/<name>/skills/` | Codex marketplace, one entry per install package |
| Claude Code | `packages/<name>/.claude-plugin/plugin.json` | `packages/<name>/skills/` | Claude marketplace, one entry per install package |
| Kiro / Agent Plugins 1.0 | `kiro-power*/plugin.json` | `kiro-power*/skills/` | Separate core and standards Powers |
| Cursor / Agent Plugins 1.0 | `packages/<name>/plugin.json` | `packages/<name>/skills/` | Cursor Marketplace after provider acceptance; direct connection until then |
| Gemini CLI | `packages/<name>/gemini-extension.json` | `packages/<name>/skills/` | Gemini extension manager |
| Direct-connect agents | `distribution/qodo-skills-direct.json` | Agent-owned skills directory | Verified Qodo direct-connect updater |

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
8. Direct-connect installs consume only the immutable release artifact and its published SHA-256.
9. The core package contains only skills assigned to the single default install package; optional
   skills require a distinct marketplace package or explicit direct-channel selection.

## Support tiers

- **Validated**: manifest passes the host's native validator and a local install smoke test.
- **Package-ready**: manifest is generated and schema-checked, but its host is unavailable in
  CI or locally.
- **Listed**: the package has passed the marketplace owner's external review and is publicly
  discoverable.

Do not describe package-ready as listed, or a source install as marketplace acceptance.

## Generic direct-connect compatibility

The direct artifact is one agent-neutral Agent Skills tree. It contains no host IDs, aliases,
filesystem locations, or allowlist. The CLI decides eligibility from capabilities in its agent
registry:

1. the host is detected or identifies the current runtime;
2. the registry supplies a verified project or global skills directory;
3. the host does not declare an official Qodo marketplace channel.

Every registry entry satisfying those conditions receives the same verified artifact. A newly
supported agent needs a CLI registry entry and detection evidence, not a `qodo-skills` release.
CI projects the bundle into an arbitrary isolated skills root and verifies every file digest. This
proves package completeness and portable layout; native discovery and execution remain release
acceptance evidence, prioritized using production telemetry rather than encoded as an allowlist.

When a provider later accepts Qodo into a native marketplace, change that agent's CLI capability
only after the listing is visible and its in-place upgrade passes. Existing direct installs stay
owned by the direct channel until the user verifies the marketplace copy and explicitly cleans up;
the two channels must never update the same target concurrently.

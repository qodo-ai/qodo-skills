# Migration from CLI-managed skills

The previous design bundled editable skill sources in the CLI, copied them into every agent
directory, and refreshed those copies on ordinary CLI launches. That made the CLI a shadow
marketplace and coupled skill delivery to runtime releases.

## Initial import provenance

The canonical marketplace package was seeded from the newer skill implementations in
`qodo-ai/qodo-in-cli@4970ea83ae9d247c474215fa05648c899799f977`, not from the legacy
copies previously held in this repository. The five imported `SKILL.md` bodies and their
discovery descriptions are preserved verbatim. Only unsupported frontmatter fields were
normalized into portable Agent Skills metadata. `qodo-setup` is the one newly authored skill.

After this import, skill behavior is authored only in this repository. The CLI may consume a
generated fallback snapshot, but it must never become a second editable source.

## Target behavior

1. New users install the plugin through their agent and run `qodo-setup`.
2. Existing CLI-installed users receive an explicit migration notice with host-specific
   marketplace instructions.
3. The CLI keeps an explicit offline fallback for a bounded compatibility window.
4. Normal CLI startup stops refreshing, adding, or deleting installed skills.
5. After adoption and rollback gates are met, remove the fallback command and generated
   snapshot in a separate CLI release.

## Existing listing cutover

- Claude: preserve the official plugin id `qodo@claude-plugins-official`; update its pinned source
  SHA only after the canonical release passes validation.
- Kiro: preserve the listing's `kiro-power/` source path. That directory is now a generated Agent
  Plugins 1.0 adapter, so existing installs can upgrade without a registry path migration.
- Codex: preserve the `qodo-in-harness/codex-qodo` package identity. A release dispatch imports
  the exact `qodo-skills` tag into a PR, records source hashes, and removes the embedded CLI.

## Safety rules

- Never delete a skill directory merely because its contents differ; it may be user-owned.
- Never overwrite a marketplace cache or host settings from the CLI.
- Detect legacy Qodo-managed copies using their existing provenance marker and report them.
- Require a successful marketplace install before offering removal of a legacy copy.
- Preserve project-scoped skills unless the user explicitly chooses to migrate that project.
- Keep uninstall reversible or provide the exact recovery path.

## Exit gate for the fallback

Remove the CLI installer only after all supported hosts have a validated update path, the
official listings are accepted where applicable, migration telemetry is healthy, and the
support team has a tested rollback runbook. A merged manifest is not enough.

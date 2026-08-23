# Architecture

## The invariant

Qodo authors each skill once in this repository. Marketplaces distribute and update that
content. The `qodo` CLI supplies the authenticated, evolving runtime.

This separates three lifecycles that otherwise fight each other:

| Layer | Owns | Must not own |
|---|---|---|
| `qodo-skills` | Skill instructions, discovery copy, package version, host adapters | Credentials, API transport, binary updates |
| Marketplace host | Plugin install, cache, enablement, update UX | Qodo authentication or tool semantics |
| `qodo` CLI | Login, credential storage, tool catalog, API compatibility, runtime update | Rewriting marketplace-managed plugin files |

## Repository model

`skills/<name>/SKILL.md` is canonical product content. The distribution catalog is the
canonical package and presentation metadata. `npm run adapters` renders that metadata into:

- `plugin.json` for Agent Plugins 1.0 hosts;
- `kiro-power/` as the generated Agent Plugins projection at Kiro's existing listing path;
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` for Claude Code;
- `gemini-extension.json` for Gemini CLI;
- `skills/*/agents/openai.yaml` for Codex skill presentation.

Generated adapters are committed because hosts read the repository directly. They are
never edited by hand; CI rejects drift from the catalog.

The marketplace identities deliberately remain in their current repositories. Claude consumes
this repository root through its existing official `qodo` listing. Kiro consumes
`kiro-power/`. Codex consumes a generated, provenance-locked copy in
`qodo-in-harness/codex-qodo`. This repository must not expose a second Codex plugin, and the
Codex packaging repository must not author skills or bundle the CLI runtime.

## First-use state machine

```text
plugin installed
      │
      ▼
qodo-setup finds runtime ── missing ──▶ official verified installer guidance
      │ found
      ▼
qodo whoami ── logged out ──▶ qodo login ── failure/cancel ──▶ stop honestly
      │ authenticated
      ▼
qodo tools --refresh ── failure ──▶ authenticated, runtime not ready
      │ success
      ▼
agent ready; user chooses an operational skill
```

Marketplace installation is intentionally not coupled to a binary install. Plugin hosts
have different execution and trust models, and silently running a curl pipeline would be a
poor security boundary. The universal setup skill makes first use consistent without
pretending those systems are one updater.

## Runtime contract

Skills invoke documented `qodo` commands and inspect structured output. They authenticate
with `qodo whoami` before protected work. They do not:

- read or write credential material;
- construct Qodo service URLs;
- embed transport tokens;
- own provider-specific API clients;
- update their installed copies.

The CLI should keep command behavior backward compatible within the runtime protocol. When
a skill requires a new command contract, release the CLI first, then the skill with a clear
minimum-runtime check. Marketplace rollback must remain possible without rolling back the
CLI.

## CLI fallback

The CLI may carry a generated snapshot solely for explicit, offline legacy installation.
That snapshot is a build artifact exported from this repository, not another editable
`skills/` tree. It must not refresh or add marketplace-managed skills during normal command
startup. This fallback can be removed after marketplace adoption reaches the agreed gate.

Normal marketplace releases do not regenerate or release the CLI fallback. Update that snapshot
only when adding a fallback skill, delivering a critical or security correction to offline users,
or deliberately moving the compatibility baseline. A scheduled compatibility sync may batch
several marketplace releases; it is not part of the marketplace release transaction.

Generate the snapshot from a checkout of both repositories:

```sh
node scripts/export-cli-bundle.mjs ../qodo-in-cli/src/bundled-skills.generated.ts
```

The output embeds the source package version and a deterministic content digest. The CLI
build consumes the committed artifact without reaching the network or requiring this
repository to be adjacent.

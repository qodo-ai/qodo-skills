# Architecture

## The invariant

Qodo authors each skill once in this repository. Marketplaces distribute and update plugins;
agents without an official marketplace path consume the immutable direct-connect release.
The `qodo` CLI supplies the authenticated, evolving runtime and acts only as the verified
transport for direct-connect artifacts.

This separates three lifecycles that otherwise fight each other:

| Layer | Owns | Must not own |
|---|---|---|
| `qodo-skills` | Skill instructions, discovery copy, package version, host adapters | Credentials, API transport, binary updates |
| Marketplace host | Plugin install, cache, enablement, update UX | Qodo authentication or tool semantics |
| Direct-connect channel | Immutable release bundle, published checksum, agent skill-directory update | Authored skill copies, marketplace caches, user-owned files |
| `qodo` CLI | Login, credential storage, tool catalog, API compatibility, runtime update, verified direct-connect transport | Rewriting marketplace-managed plugin files or embedding direct-connect skill content |

## Repository model

`skills/<name>/SKILL.md` is canonical product content. The distribution catalog is the
canonical package and presentation metadata. `npm run adapters` renders the catalog into:

- `plugin.json` for Agent Plugins 1.0 hosts;
- `kiro-power/` as the generated Agent Plugins projection at Kiro's existing listing path;
- `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` for Codex;
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` for Claude Code;
- `gemini-extension.json` for Gemini CLI;
- `skills/*/agents/openai.yaml` for Codex skill presentation;
- `distribution/qodo-skills-direct.json` and its SHA-256 for agents without a marketplace.

Generated adapters are committed because hosts read the repository directly. They are
never edited by hand; CI rejects drift from the catalog.

The direct artifact has no agent allowlist, install path, or host adapter. Eligibility is
capability-based in the CLI: a recognized host is direct-connectable when its registry entry has
a verified project or global skills directory and does not declare an official Qodo marketplace
channel. Adding a compatible agent therefore changes only the CLI registry; routine skill releases
remain unchanged.

Claude and Codex consume this repository root through their existing official `qodo` listing
identities. Kiro consumes `kiro-power/`. Cursor can consume the root Agent Plugins package after
its marketplace submission is accepted; until then it remains direct-connected. The Codex listing
must be repointed from the deprecated `qodo-in-harness/codex-qodo` source only after an
existing-install upgrade test proves the provider preserves the plugin identity. No marketplace
package bundles the CLI runtime.

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

For a detected agent without an official Qodo marketplace path, setup instead asks “Connect Qodo
to <agent>?”, explains that Qodo will add its official skills and keep them updated, and downloads
the immutable direct-connect artifact. The CLI verifies both the published artifact checksum and
every file digest, records the installed paths and hashes, and checks for new releases in a
detached process at most once per day. A changed, removed, additional, or symlinked file pauses
updates for that target rather than overwriting it.

## Runtime contract

Skills invoke documented `qodo` commands and inspect structured output. They authenticate
with `qodo whoami` before protected work. They do not:

- read or write credential material;
- construct Qodo service URLs;
- embed transport tokens;
- own provider-specific API clients;
- update their installed copies.

The final rule applies to skill logic. Marketplace hosts update marketplace copies; the generic
direct-connect transport updates only the Qodo-owned files recorded in its local manifest.

The CLI should keep command behavior backward compatible within the runtime protocol. When
a skill requires a new command contract, release the CLI first, then the skill with a clear
minimum-runtime check. Marketplace rollback must remain possible without rolling back the
CLI.

## Branded value moments

Qodo's brand appears where it helps the user recognize a verified product outcome, not as a
repeated banner. Every operational skill renders at most one compact Markdown result block after
Qodo has produced or verified useful state. The header names Qodo and the outcome; the fields below
carry task-specific evidence such as scope, counts, freshness, coverage, or the next safe action.

The contract is:

- start with `# <emoji> Qodo <outcome>`;
- include only fields backed by structured command output or cited evidence;
- render once at the workflow's value moment, before detailed results;
- never render during progress, auth/setup failures, permission failures, or unverified success;
- keep the semantic labels useful without emoji or color, and never add promotional copy.

The skills intentionally use different outcome names—Ready, Rules Loaded, Codebase Insight,
Review Standards, Pre-PR Review, and PR Review—because the value must be recognizable before the
brand treatment is consistent. Validation pins those headings so generated adapters cannot drift.

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

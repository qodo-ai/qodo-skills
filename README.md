# Qodo for coding agents

Qodo's code intelligence, review, and organizational standards—packaged once for the
local coding agents developers already use.

> **Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.**

This repository is both the canonical source for Qodo's agent skills and a native package
for Codex, Claude Code, Kiro, Gemini CLI, and hosts that implement the Agent Plugins 1.0
format. It contains no MCP server and no copied credentials. Every skill calls the local
`qodo` runtime, which owns login, tool discovery, compatibility, and updates.

## Start here

Install the Qodo plugin from your coding agent, then ask:

```text
Set up Qodo
```

The `qodo-setup` skill verifies the runtime, opens `qodo login` when needed, confirms the
managed-tool catalog, and tells you when the agent is ready. The plugin can be installed
before login, but the operational skills stay unusable until authentication succeeds.

### Install from this repository

| Host | Install |
|---|---|
| Codex | Install **Qodo** from the official Codex marketplace |
| Claude Code | `claude plugin install qodo@claude-plugins-official --scope user` |
| Cursor | Use `qodo setup` until the Qodo Agent Plugin is accepted into Cursor Marketplace |
| Gemini CLI | Install the generated **Qodo** package through its accepted extension entry |
| Kiro | Install **Qodo** from the curated Powers marketplace |
| Agent Plugins hosts | Import the generated `packages/qodo/` package through the host's plugin UI |

These source-install commands are immediately usable after the branch is published.
Official marketplace listings are separate release operations; see
[Releasing](docs/releasing.md).

If the runtime is missing, `qodo-setup` routes the user to the checksum-verified installer
at [get.qodo.ai](https://get.qodo.ai). The plugin deliberately does not download or execute
a binary during marketplace installation.

## Skills

| Skill | Purpose | Default pack |
|---|---|:---:|
| `qodo-setup` | Connect the runtime and verify readiness | ✓ |
| `qodo-codebase-wisdom` | Understand current code, history, and cross-repo impact | ✓ |
| `qodo-get-rules` | Load the Qodo standards relevant to a coding task | Optional quality hold |
| `qodo-review` | Review local changes before opening a pull request | ✓ |
| `qodo-review-resolver` | Read and resolve Qodo pull-request findings | ✓ |
| `qodo-manage-standards` | Create and administer Qodo Review Standards | Optional standards package |

The skill instructions under [`skills/`](skills/) are the product source. Host-specific
files are generated from [`distribution/catalog.json`](distribution/catalog.json). The direct
bundle is agent-neutral: any CLI-recognized host with a verified project or global skills directory
and no official Qodo marketplace path can consume it without a host-specific package change.

The existing **Qodo** marketplace identity contains only the four default skills. Rules discovery
and standards administration are generated into the separately installed **Qodo Standards**
package. `qodo-get-rules` remains optional until its quality gate is explicitly reopened; publishing
a new optional package never adds it to an existing installation.

## The ownership boundary

```text
qodo-skills repository          coding-agent marketplace       qodo CLI
┌──────────────────────┐       ┌────────────────────────┐      ┌────────────────────┐
│ canonical SKILL.md   │──────▶│ install + update plugin│      │ login + credentials│
│ catalog + adapters   │       │ discover + invoke skill│─────▶│ tools + auto-update│
└──────────────────────┘       └────────────────────────┘      └────────────────────┘
```

- A skill change ships by releasing this repository, independent of a CLI release.
- A runtime change ships through the CLI updater, independent of marketplace review.
- Marketplaces own installed plugin copies. The CLI does not rewrite them on launch.
- Skills never read secret files or call Qodo endpoints directly; they invoke `qodo`.
- Canonical skills stamp `skills-sh`; generated marketplace and Kiro copies stamp their lifecycle
  owner. The runtime combines a generic marketplace stamp with the detected host, so Claude,
  Codex, and Cursor receive native update guidance while a skills.sh copy stays on skills.sh.

The detailed contracts are in [Architecture](docs/architecture.md),
[Compatibility](docs/compatibility.md), and [Releasing](docs/releasing.md). The ordered first
migration, provider gates, acceptance matrix, and rollback path are in
[Marketplace migration and release plan](docs/release-plan-v1.md).

## Development

Node 20.6 or newer is the only validation dependency.

```sh
npm run adapters   # regenerate every host manifest from the catalog
npm test           # validate skills, versions, security boundaries, and adapters
npm run release:prepare -- --summary "What changed" --skill qodo-review=patch
```

Also run the native validators for any host you have installed:

```sh
claude plugin validate .
gemini extensions validate .
```

See [Contributing](CONTRIBUTING.md) before changing a skill. No push, tag, marketplace
submission, or release is performed by these scripts.

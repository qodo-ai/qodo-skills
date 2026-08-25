# Qodo skills

The canonical, provider-neutral source for Qodo’s local coding-agent skills.

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

Every distributed skill contains its complete reviewed workflow. Coding agents do not fetch task
instructions from the Qodo CLI. The CLI provides authentication, managed tools, offline tool help,
runtime updates, and a compact stale-skill notice; it never installs or rewrites skills.

## Packages

| Package | Installed by default | Skills |
|---|---:|---|
| `qodo` | Yes | setup, codebase wisdom, local review, PR review resolver |
| `qodo-standards` | No | rules discovery and standards administration |

Qodo Standards stays a separate opt-in package. Updating the core package never installs it.

## Install

Use the official Qodo listing in Claude Code, Codex, or Kiro. The marketplace owns installation
and updates; install the Qodo CLI separately and complete `qodo login` on first use.

For a compatible local agent without an official Qodo listing, use skills.sh. One command can
target multiple agents:

```sh
npx skills add https://github.com/qodo-ai/qodo-skills \
  --skill qodo-setup \
  --skill qodo-codebase-wisdom \
  --skill qodo-review \
  --skill qodo-review-resolver \
  --agent cursor \
  --agent gemini-cli \
  --global \
  --yes
```

Install Qodo Standards only when requested:

```sh
npx skills add https://github.com/qodo-ai/qodo-skills \
  --skill qodo-get-rules \
  --skill qodo-manage-standards \
  --agent cursor \
  --global \
  --yes
```

The CLI can detect supported local agents and print the exact command without running it:

```sh
qodo agents status --json
qodo agents install --agent cursor,gemini-cli --json
```

## Update

- Marketplace install: apply the Qodo update in that host, then start a new session.
- skills.sh install: inventory the installed scope with `npx skills list --json` and
  `npx skills list -g --json`, then run a scope-preserving skills.sh update/re-add command.
- Qodo CLI: updates independently through `qodo update` and its background runtime updater.

When a skill is stale, a successful Qodo command may emit a structured `QODO_NOTICE` on stderr.
The loaded skill finishes the current task, inventories its lifecycle owner, shows the exact
scoped update action, and asks before any mutation.

## Repository layout

```text
skills/                         canonical authored skills
packages/                       generated Claude packages
codex-packages/                 generated Codex packages
kiro-power*/                    generated Kiro Powers
distribution/catalog.json      package membership and discovery metadata
distribution/marketplaces.json provider release adapters
distribution/qodo-skills-index.json  compact stale-version index
releases/                       immutable release records
scripts/                        generation, validation, and release automation
```

Generated provider roots are byte-equivalent projections of the canonical skill with only
distribution and host provenance stamped into commands/frontmatter. `npm test` rejects drift,
thin loaders, missing workflows, package leakage, unsafe paths, and inconsistent versions.

## Maintainers

Start with [architecture](docs/architecture.md), [releasing](docs/releasing.md), and the
[cutover and release strategy](docs/cutover-and-release-strategy.md).

```sh
npm run release:prepare -- --summary "Improve review guidance" --skill qodo-review=patch
npm test
```

Do not edit generated provider packages by hand.

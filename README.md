# Qodo skills

The canonical, provider-neutral source for Qodo’s local coding-agent skills.

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

Every distributed skill contains its complete reviewed workflow. Coding agents do not fetch task
instructions from the Qodo CLI. The CLI provides authentication, managed tools, offline tool help,
runtime updates, passive skill notices, and verified maintenance through each recorded lifecycle
owner. Enterprise and historical CLI-managed installations can update automatically; marketplace
plugins remain owned by their host.

## Packages

| Package | Installed by default | Skills |
|---|---:|---|
| `qodo` | Yes | setup, codebase wisdom, local review, PR review resolver |
| `qodo-standards` | No | rules discovery and standards administration |

Qodo Standards stays a separate opt-in package. Updating the core package never installs it.

## Contribute a skill update

Edit `skills/<name>/SKILL.md` directly in GitHub, open a PR, wait for CI, and merge.
Contributors do not need Node or local commands. Automation collects merged changes into one
separate release PR with versions and generated marketplace packages. A release owner merges
that PR to start protected publication. See [Contributing](CONTRIBUTING.md) for the complete flow.
The [Actions guide](.github/workflows/README.md) explains the six workflows and when to use them.

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

The CLI detects supported local agents and prints the exact command without running it. If none is
detected, it reads skills.sh's current supported-agent catalog, excludes the marketplace-owned
Claude Code, Codex, and Kiro IDs, and offers the remaining agents as a multi-select. The bundled
catalog remains a read-only offline fallback:

```sh
qodo agents status --json
qodo agents catalog --json
qodo agents install --agent cursor,gemini-cli --json
qodo agents install --agent cursor --standards --json
```

`--standards` adds a separate Qodo Standards command; it never broadens the core package.

## Update

- Marketplace install: apply the Qodo update in that host, then start a new session.
- skills.sh install: inventory the installed scope with `npx skills list --json` and
  `npx skills list -g --json`, then run a scope-preserving skills.sh update/re-add command.
- Verified enterprise install: Qodo maintains recorded copies under the disclosed automatic policy.
  Requested maintenance uses `qodo agents update --enterprise` for a full preview and confirmation;
  scripts use `--dry-run --json` followed by the returned `--apply-plan ... --yes` command.
- Qodo CLI: updates independently through `qodo update` and its background runtime updater.

Availability and completion notices on stderr are passive: continue the task without inventory
or an unsolicited update question. Automatic maintenance follows the existing disclosed policy,
source and opt-outs. Only requested manual maintenance requires resolving the full operation
before any additional consent; reuse approval that already covers it. New sessions load updated
files when convenient.

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

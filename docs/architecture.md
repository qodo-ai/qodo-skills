# Distribution architecture

## Invariant

> Qodo authors skills once; marketplaces update plugins; the CLI updates the runtime.

This is one architecture across every local coding agent. Providers differ only in packaging and
lifecycle UI—not in workflow content or authority.

## Ownership

| Surface | Owns | Must not own |
|---|---|---|
| `qodo-skills` | canonical workflow bodies, package membership, versions, provider projections, release packets | credentials, API transport, installed host state |
| Marketplace | install, cache, update, rollback, and removal of its Qodo plugin | Qodo runtime binary or login |
| skills.sh | install, link/copy, scope, update, and removal for agents without a Qodo listing | Qodo runtime binary or login |
| Qodo CLI | login, credentials, managed-tool catalog, tool invocation, offline tool help, runtime update, stale-skill notices | skill installation, task-time playbooks, marketplace caches |

The CLI may remove only byte-identical copies produced by its retired installer, after an explicit
migration command. It preserves edits, symlinks, extra files, and shared roots unless the user
acknowledges the shared ownership.

## Author once, generate everywhere

Canonical skills live in `skills/<name>/`. `distribution/catalog.json` defines two packages:

- `qodo`: the four core workflows, installed by default;
- `qodo-standards`: the two standards workflows, always optional.

`npm run adapters` generates the provider roots:

| Provider | Generated root | Provenance |
|---|---|---|
| Claude Code | `packages/<package>/` | `marketplace`, `claude-code` |
| Codex | `codex-packages/<package>/` | `marketplace`, `codex` |
| Kiro | `kiro-power/`, `kiro-power-standards/` | `kiro-power`, `kiro` |
| skills.sh | canonical `skills/` tree | `skills-sh`, host stamped by installer/use context |

Generation copies the complete canonical workflow. It changes only distribution/host provenance
and provider manifests. Validation byte-compares every generated skill against that deterministic
projection and rejects any `qodo help workflow` loader.

## Runtime contract

Every skill:

1. identifies itself on its first Qodo call with `--skill`, `--skill-version`, `--distribution`,
   and a provider-generated `--host` where applicable;
2. verifies authentication through `qodo whoami`;
3. discovers exact commands and READ/WRITE safety from `qodo tools help`;
4. invokes the authenticated runtime;
5. treats a `QODO_NOTICE` as non-fatal metadata after preserving the command result.

The CLI’s compact release index contains only package and skill versions. A daily bounded refresh
may discover staleness. It never downloads workflow text and never changes an agent skill root.

## Why workflows are embedded

A blinded Codex/Claude experiment compared embedded workflows with a thin skill that loaded the
playbook from the CLI. Quality remained near parity, but the loader failed absolute release gates:
invocation ordering was imperfect on both hosts, median latency regressed by more than 15%, and
resilience/authority cases were not uniformly safe. The release architecture therefore uses full
embedded provider skills.

Dynamic task-time loading can be reconsidered only after it passes the same absolute gates on all
supported hosts; it is not a hidden fallback in this design.

## New agents

The generic path is capability-based. The CLI registry tracks compatible skills directories and
detection signals. A new agent with no accepted Qodo marketplace listing is eligible for skills.sh
guidance automatically; adding a marketplace listing changes its lifecycle owner to marketplace
and excludes it from skills.sh suggestions. Production-usage data prioritizes smoke testing but
does not define an allowlist.

## Security boundaries

- Generated paths are repository-relative and validated against traversal.
- Release assets are checksummed and releases must be immutable.
- Marketplace packets contain no credentials.
- A stale notice never mutates; it requires read-only inventory and explicit approval.
- Optional packages are never pulled in by update.
- Provider-visible publication, fresh install, and upgrade tests are release gates; green source CI
  is necessary but not proof of marketplace acceptance.

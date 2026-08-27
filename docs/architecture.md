# Distribution architecture

## Invariant

> Qodo authors skills once; marketplaces or the enterprise bundle update plugins; the CLI updates the runtime.

This is one architecture across every local coding agent. Providers differ only in packaging and
lifecycle UI—not in workflow content or authority.

## Ownership

| Surface | Owns | Must not own |
|---|---|---|
| `qodo-skills` | canonical workflow bodies, package membership, versions, provider projections, release packets | credentials, API transport, installed host state |
| Marketplace | install, cache, update, rollback, and removal of its Qodo plugin | Qodo runtime binary or login |
| skills.sh | install, link/copy, scope, update, and removal for agents without a Qodo listing | Qodo runtime binary or login |
| Enterprise bundle / QAR | immutable offline skill package, reviewed pin, same-origin download, and customer-controlled plugin rollout | public CLI binary contents or silent agent-root mutation |
| Qodo CLI | login, credentials, managed-tool catalog, tool invocation, offline tool help, runtime update, stale-skill notices | skill installation, task-time playbooks, marketplace caches |

After an explicit migration command, the CLI may retire only byte-identical copies produced by a
shipped CLI release. It atomically moves them out of the host skill name into a recoverable hidden
quarantine; it never recursively deletes their bytes. Edits, symlinks, extra files, unknown
versions, and shared roots remain untouched unless the user acknowledges shared ownership.

## Author once, generate everywhere

Canonical skills live in `skills/<name>/`. `distribution/catalog.json` defines two packages:

- `qodo`: the four core workflows, installed by default;
- `qodo-standards`: the two standards workflows, always optional.

Every canonical `SKILL.md` carries a named Qodo owner, a single-line discovery description, and
the standard Description, Prerequisites, Instructions, Configuration, and Error Handling sections.
Validation enforces this authoring contract before generating any provider package. The catalog,
marketplace contract, and Codex submission metadata are also compiled against their checked-in JSON
Schemas rather than relying only on partial hand-written checks.

`npm run adapters` generates the provider roots:

| Provider | Generated root | Provenance |
|---|---|---|
| Claude Code | `packages/<package>/` | `marketplace`, `claude-code` |
| Codex | `codex-packages/<package>/` | `marketplace`, `codex` |
| Kiro | `kiro-power/`, `kiro-power-standards/` | `kiro-power`, `kiro` |
| skills.sh | canonical `skills/` tree | `skills-sh`, host stamped by installer/use context |
| On-prem | immutable `qodo-enterprise-bundle-v<version>.tar.gz` release asset | `enterprise-bundle`, host retained in each projection |

Generation copies the complete canonical workflow. It changes only distribution/host provenance
and provider manifests. Core marketplace packages also generate the temporary
`qodo-pr-resolver` compatibility alias from the canonical `qodo-review-resolver` body so existing
explicit invocations survive the rename without creating a second authored workflow. Validation
byte-compares every generated skill against that deterministic projection and rejects any
`qodo help workflow` loader. Kiro uses the current Agent Plugins contract (`plugin.json` plus
`skills/`); the retired `POWER.md`/`steering/` layout is not regenerated. Its public listing follows
only the protected `marketplace-kiro` release branch, never mutable day-to-day `main`.

## Runtime contract

Every skill:

1. checks the declared minimum runtime with an unadorned `qodo --version` call that older CLIs can
   parse and offers the runtime's recorded update path when needed;
2. identifies itself on its first post-gate Qodo call with `--skill`, `--skill-version`, `--distribution`,
   and a provider-generated `--host` where applicable;
3. verifies authentication through `qodo whoami`;
4. discovers exact commands and READ/WRITE safety from `qodo tools help`;
5. invokes the authenticated runtime;
6. treats a `QODO_NOTICE` as non-fatal metadata after preserving the command result.

The CLI’s compact release index contains only package, skill, and minimum-runtime versions. A daily
bounded refresh may discover staleness. It never downloads workflow text and never changes an agent
skill root. An on-prem QAR `version.json` advertises same-origin index paths; a private origin without
that pointer fails closed instead of reaching the public release host.

## Why workflows are embedded

A blinded Codex/Claude experiment compared embedded workflows with a thin skill that loaded the
playbook from the CLI. Quality remained near parity, but the loader failed absolute release gates:
invocation ordering was imperfect on both hosts, median latency regressed by more than 15%, and
resilience/authority cases were not uniformly safe. The release architecture therefore uses full
embedded provider skills.

Dynamic task-time loading can be reconsidered only after it passes the same absolute gates on all
supported hosts; it is not a hidden fallback in this design.

## New agents

The generic path is capability-based. The CLI detects known compatible skill directories; when no
agent is detected, it reads and strictly parses skills.sh's current public supported-agent table at
runtime. That makes a newly supported agent selectable without waiting for a Qodo CLI release,
while a bounded bundled snapshot keeps setup usable offline. Marketplace-owned IDs and the shared
`universal` alias are excluded so the fallback cannot create a second owner for Claude Code, Codex,
or Kiro. Adding a Qodo marketplace listing changes that agent's lifecycle owner to marketplace.
Production-usage data prioritizes smoke testing but does not define an allowlist.

## Security boundaries

- Generated paths are repository-relative and validated against traversal.
- Release assets are checksummed and releases must be immutable.
- Marketplace packets contain no credentials.
- A stale notice never mutates; it requires read-only inventory and explicit approval.
- Optional packages are never pulled in by update.
- Provider-visible publication, fresh install, and upgrade tests are release gates; green source CI
  is necessary but not proof of marketplace acceptance.
- Enterprise archives are deterministic, checksum-published, contain no CLI binary or credential,
  keep Standards opt-in, declare `DO_NOT_TRACK=1` for any skills-CLI-based enterprise import, and
  are independently pinned by QAR.

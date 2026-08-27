<p align="center">
  <img src="./Qodo-Kiro.png" alt="Qodo for Kiro — Qodo AI code review and governance in Kiro" width="840">
</p>

<h1 align="center">Qodo for Kiro</h1>

<p align="center">
  The Qodo <strong>Kiro Power</strong> — bring Qodo's AI code review and governance into your Kiro workspace.
</p>

<p align="center">
  <img alt="Kiro Power" src="https://img.shields.io/badge/Kiro-Power-5a3ecb">
  <img alt="Powered by Qodo CLI" src="https://img.shields.io/badge/powered%20by-Qodo%20CLI-7b4bd8">
  <img alt="No MCP server" src="https://img.shields.io/badge/MCP-none-blueviolet">
  <img alt="Read-only tools" src="https://img.shields.io/badge/managed%20tools-read--only-2ea44f">
</p>

> **What this README covers.** The Kiro-Power–specific parts (capabilities, architecture, setup, usage, examples, and workflows) are documented here — that is this repo's unique product. For everything else — company and product information, security, compliance, privacy, legal, licensing, and support — the single source of truth is the official Qodo website, **[qodo.ai](https://www.qodo.ai/)**. The sections below link to it rather than restating it.

---

## What this power does

**One consolidated Kiro Power** that routes each request to the right Qodo capability and runs it through the **Qodo CLI's managed tools**. It's a Knowledge Base Power — a `POWER.md` router plus one `steering/` file per capability. **No MCP server, no background daemon, no inbound listener.** Every capability is **read-only and git-provider-agnostic**, and **never posts to your git forge** — resolving a finding means editing local code, only after your confirmation.

## Capabilities

Just say what you want in Kiro — the power loads only the one capability that matches.

| Capability | Say something like… | Delegates to |
|---|---|---|
| **Get Rules** | *"get qodo rules for this task"* | `qodo rules search` |
| **Pre-PR Review** | *"qodo review my changes before I push"* | `qodo review` |
| **PR Resolver** | *"resolve my Qodo PR review"* / *"is this PR's review clean?"* | `qodo pr-review-session findings` |
| **Codebase Wisdom** | *"ask qodo how the payments flow works"* | `qodo codebase` / `pull-request` / `cross-repo` |

## Requirements

- **Kiro** with Powers support.
- **Qodo CLI** (requires **Node.js ≥ 20**). GUI-launched agents run a minimal `PATH`, so the power always calls the absolute path **`~/.qodo/bin/qodo`**. Install it with:
  ```bash
  curl -fsSL https://get.qodo.ai/install.sh | sh
  ```
- A **Qodo account**. Authentication is **on first use** — the power runs `qodo whoami` and, if you're not signed in, asks you to run `qodo login`.

## Getting started

1. **Install the Qodo CLI** (above) and, when prompted, sign in:
   ```bash
   ~/.qodo/bin/qodo login
   ```
2. **Add the power to Kiro.** This power is a plain `POWER.md` + `steering/` bundle (no server to run). Install it through Kiro's Powers — see the [Kiro Powers docs](https://kiro.dev/powers/). For local/development use, make the contents of this directory available as a power in your Kiro powers folder, then reload Kiro.
3. **Use it.** In Kiro chat, ask for a Qodo workflow in plain language, e.g.:
   > get qodo rules for this change
   >
   > qodo review my local changes
   >
   > resolve the Qodo findings on this PR

That's it — Kiro loads the matching capability and drives the Qodo CLI for you.

## How it works

- **Router.** Kiro loads `POWER.md` first, infers your intent, and loads **only** the one steering file that matches (never all of them).
- **Thin delegation.** Each capability is a short steering file that calls the Qodo CLI's managed tools — no bundled scripts, no provider-specific scraping.
- **CLI-first.** The CLI already gathers what you'd otherwise reach for `git`/`gh` for (`qodo review` self-collects the diff, branch, HEAD, and a commit-message summary; the `codebase` tools autodetect the repo and read server-side), so the power avoids redundant local commands.
- **Safe by construction.** Only **read** tools are used; the power never calls a forge-write tool (comment, approve, label, description). It asks before edits, commits, or pushes.

## What this power sends

Capability-level data flow (this is Kiro-Power–specific behavior; for Qodo's overall data-handling posture, see **[Security &amp; compliance](#security--compliance)** below):

- **Get Rules** sends your generated rule queries (and, optionally, the repo scope) to Qodo's rules search; it returns rules and changes nothing.
- **Pre-PR Review** sends your local diff plus any coding-session context you attach to Qodo's review engine; nothing is pushed and no PR is created.
- **PR Resolver / Codebase Wisdom** read review findings / code + history through the CLI's managed **read** tools.
- **Nothing is posted to your git forge.** Credentials live under `~/.qodo/` (written by `qodo login`) and are **never printed** — no capability echoes config, tokens, or raw tool JSON.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `qodo: command not found` | Use the absolute path `~/.qodo/bin/qodo` (GUI shells have a minimal `PATH`). If the file is missing, (re)install with the `curl` line above. |
| `not_logged_in` / `Not logged in` | Run `~/.qodo/bin/qodo login`. |
| `unknown command` on a tool right after install | The cached tool catalog is stale — run `~/.qodo/bin/qodo tools --refresh` and retry. |
| `qodo review` is slow or times out | Give the shell invocation a `1200000` ms (20-minute) timeout and scope it to the changed area, e.g. `qodo review backend/`. A large **gitignored** tree (`venv/`, `node_modules/`) slows the first, uncached run. |

---

## About Qodo

Qodo is the **AI code review and governance platform** for engineering teams shipping at the speed AI writes code. Qodo reviews every pull request with full, cross-repo codebase context, enforces your coding standards, and governs the AI tools and agents shaping how code gets built — across the IDE and Git. Learn more at **[qodo.ai](https://www.qodo.ai/)**.

## Security &amp; compliance

Qodo is built for enterprise-grade security, privacy, and compliance. Refer to **[qodo.ai](https://www.qodo.ai/)** and the **[Qodo Trust Center](https://trust.qodo.ai/)** as the source of truth; in summary:

- **Zero data retention** — your code is analyzed and discarded; nothing is stored, logged, or used to train models.
- **SOC 2 Type II certified** — independently audited security controls.
- **On-premises deployment** — deploy entirely within your own infrastructure.
- **Single-tenant deployment** — your own dedicated instance; no shared infrastructure.

More detail: [Qodo Trust Center](https://trust.qodo.ai/) · [Qodo's commitment to data privacy &amp; security](https://www.qodo.ai/blog/qodo-security-our-commitment-to-data-privacy-and-security/).

## Legal, licensing &amp; support

Qodo is a commercial, proprietary product. Use of Qodo — and of this power and the Qodo CLI it integrates with — is governed by the **[Qodo Terms of Use](https://www.qodo.ai/terms/)**. These official pages are authoritative:

- [Terms of Use](https://www.qodo.ai/terms/)
- [Privacy Policy](https://www.qodo.ai/privacy-policy/)
- [Security &amp; compliance — Trust Center](https://trust.qodo.ai/)
- [Contact &amp; support](https://www.qodo.ai/contact/)

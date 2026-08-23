# Releasing

Releases update skills through marketplaces; they never publish or update the `qodo` binary.

## Prepare

1. Edit canonical `SKILL.md` files.
2. Increment each changed skill's version in its frontmatter and in
   `distribution/catalog.json`.
3. Increment `package.version` in the catalog for every release.
4. Run `npm run adapters`.
5. If the CLI fallback is still supported, export its generated snapshot and review the
   recorded package version and digest.
6. Run `npm test` and all available native host validators.
7. Test a source install in each supported host and run “Set up Qodo”.
8. Confirm login, a read-only skill, and the approval gate of one write-capable skill.

The release pull request must include the compatibility impact, hosts actually tested, and
any package-ready-but-unvalidated surface. Generated changes should be reviewable as a pure
projection of the catalog.

## Publish

After the release commit is merged:

1. Create an annotated `v<package-version>` tag on the verified merge commit.
2. Create a GitHub release from that tag with changed skills and runtime requirements.
3. Refresh or submit each official marketplace listing according to that host's process.
4. Verify the marketplace-visible version and perform a fresh install—repository and CI
   success are not proof of listing acceptance.
5. Upgrade an existing installation and verify that the host, not the CLI, replaced it.

Tagging, GitHub releases, and marketplace submissions are deliberate external writes. The
repository's scripts do none of them.

## Update behavior users should see

| Host | Source refresh |
|---|---|
| Codex | `codex plugin marketplace upgrade qodo`; install the offered plugin update and restart when prompted |
| Claude Code | `claude plugin marketplace update qodo`, then `claude plugin update qodo@qodo` |
| Gemini CLI | Automatic when installed with `--auto-update`, or `gemini extensions update qodo` |
| Kiro | Power → Check for updates → Install updates |

The `qodo` runtime updates on its own channel with `qodo update`; a plugin update must never
overwrite it.

## Rollback

- Marketplace regression: repoint or republish the prior plugin release; do not downgrade
  the runtime unless the runtime itself is faulty.
- Runtime regression: use the CLI channel/rollback process; do not mutate skill packages to
  smuggle a binary fix.
- Compatibility break: restore the last compatible skill release first, then repair and
  release the runtime contract in the correct order.

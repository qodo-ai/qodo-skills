# Releasing

Releases update skills through marketplaces; they never publish or update the `qodo` binary.

## One pull request

1. Edit canonical `SKILL.md` files.
2. Run the release preparation command once, naming every affected skill:

   ```sh
   npm run release:prepare -- \
     --summary "Improve local review guidance." \
     --skill qodo-review=patch
   ```

3. Review the atomic version changes, generated adapters, and
   `releases/v<package-version>.json`.
4. Run `npm test` and all available native host validators.
5. Test a source install in each supported host and run “Set up Qodo”.
6. Confirm login, a read-only skill, and the approval gate of one write-capable skill.

The release pull request must include the compatibility impact, hosts actually tested, and
any package-ready-but-unvalidated surface. Generated changes should be reviewable as a pure
projection of the catalog.

There is no second human-authored release pull request. `main` must remain releasable, so the
version, notes, and generated package travel with the skill change that needs them. Pull-request
CI compares the branch with its base and rejects changed skill bodies without corresponding skill
and package version increments.

Use `--skill <name>=initial` when introducing a new skill at its authored starting version. The
package receives at least a minor increment; `initial` is rejected for a skill that already exists
on the base branch.

## Publish after merge

The `Release skills` workflow performs the GitHub-side publication:

1. Re-run the complete validation suite on the merged commit.
2. Create an annotated `v<package-version>` tag on that exact commit.
3. Render the immutable release record into a GitHub Release.
4. Dispatch a version-pinned import pull request to `qodo-in-harness` for Codex.
5. Refresh or submit each official marketplace listing according to that host's process.
6. Verify the marketplace-visible version and perform a fresh install—repository and CI
   success are not proof of listing acceptance.
7. Upgrade an existing installation and verify that the host, not the CLI, replaced it.

The workflow uses `QODO_IN_HARNESS_DISPATCH_TOKEN`, scoped only to dispatch the private
`qodo-in-harness` repository. A missing token fails the downstream-dispatch step without mutating
marketplace state. The import workflow opens a reviewable PR; it never publishes automatically.
Official marketplace submission and provider-visible verification remain explicit release gates.

## CLI fallback cadence

Do not export the CLI fallback for routine skill improvements. Sync it only for a new fallback
skill, a critical or security correction that must reach offline users, or an explicit
compatibility-baseline update. The CLI snapshot is a separately reviewed runtime release artifact,
never a hidden side effect of this repository's release workflow.

## Update behavior users should see

| Host | Source refresh |
|---|---|
| Codex | Install the update offered by the official Codex marketplace and restart when prompted |
| Claude Code | `claude plugin update qodo@claude-plugins-official` |
| Gemini CLI | Automatic when installed with `--auto-update`, or `gemini extensions update qodo` |
| Kiro | Power → Check for updates → Install updates |

The `qodo` runtime updates on its own channel with `qodo update`; a plugin update must never
overwrite it.

## Rollback

- Marketplace regression: publish a new patch that restores the last good content. Tags and
  release records are immutable; never repoint them. Do not downgrade the runtime unless the
  runtime itself is faulty.
- Runtime regression: use the CLI channel/rollback process; do not mutate skill packages to
  smuggle a binary fix.
- Compatibility break: restore the last compatible skill release first, then repair and
  release the runtime contract in the correct order.

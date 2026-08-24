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

Before the first release, a repository administrator must enable **Settings → Releases →
Enable release immutability**. GitHub applies this only to future releases. The release workflow
checks the published release's `immutable` API field and fails the release job unless it is true.
This makes the tag and attached direct-connect artifact non-replaceable after publication.

The `Release skills` workflow performs the GitHub-side publication:

1. Re-run the complete validation suite on the merged commit.
2. Create an annotated `v<package-version>` tag on that exact commit.
3. Render the immutable release record into a GitHub Release.
4. Attach `qodo-skills-index.json` and its SHA-256 for metadata-only version checks. During the
   migration window, also attach `qodo-skills-direct.json` and its SHA-256 for direct-connected agents.
5. Refresh or submit each official marketplace listing according to that host's process.
   Preserve the existing `qodo` core identity and treat `qodo-standards` as a separate optional
   listing/Power; never fold its skills back into core discovery.
6. Verify the marketplace-visible version and perform a fresh install—repository and CI
   success are not proof of listing acceptance.
7. Upgrade an existing installation and verify that the host, not the CLI, replaced it.

The workflow cannot alter marketplace accounts or publish the Qodo runtime. Official marketplace
submission and provider-visible verification remain explicit release gates. The
`qodo-in-harness` deprecation is a later, separately reviewed operation after the Codex listing
source cutover passes both install tests.

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
| Cursor | Cursor Marketplace after listing acceptance; verified direct connection before cutover |
| Gemini CLI | Automatic when installed with `--auto-update`, or `gemini extensions update qodo` |
| Kiro | Power → Check for updates → Install updates |
| Direct-connect agent | Qodo checks the immutable release feed in the background and applies the verified bundle for the next agent session |

Marketplace and direct updates replace only packages already installed or selected. A newly
published optional package is discoverable, not automatically installed.

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

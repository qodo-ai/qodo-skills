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
checks the repository setting before creating a tag or release, then checks the published release's
`immutable` API field and expected asset inventory. It fails closed before publication when
immutability is disabled.
This makes the tag and attached direct-connect artifact non-replaceable after publication.

The `Release skills` workflow performs the GitHub-side publication:

1. Re-run the complete validation suite on the merged commit.
2. Create an annotated `v<package-version>` tag on that exact commit.
3. Render the immutable release record into a GitHub Release.
4. Attach `qodo-skills-index.json` and its SHA-256 for metadata-only version checks. During the
   migration window, also attach `qodo-skills-direct.json` and its SHA-256 for direct-connected agents.
5. Stop. Marketplace promotion is a separate, selectable operation so one provider delay cannot
   silently change another provider's release state.

## Ship selected marketplaces

After the immutable GitHub Release exists, run **Actions → Ship marketplaces → Run workflow**.
Enter the exact release tag and check any combination of Claude, Codex, and Kiro, or check **all**.
The workflow reads [`distribution/marketplaces.json`](../distribution/marketplaces.json), prepares
one exact packet per provider, and will not accept an untagged, mutable, or version-mismatched
release.

| Provider | What the action can do | Green completion condition |
|---|---|---|
| Claude Code | Generate the two directory entries and inspect Anthropic's official SHA-pinned catalog | `qodo` and `qodo-standards` point to the selected commit and paths, and the legacy `qodo-skills` rename remains intact |
| Codex | Generate two portal packets with starter prompts and five positive plus three negative reviewer tests per listing | A required reviewer approves the protected `marketplace-codex` environment only after OpenAI review and portal publication |
| Kiro | Inspect Kiro's live Git-backed directory | `qodo` and `qodo-standards` expose the expected paths and repository `main` still equals the selected release commit |

Before selecting Codex, a repository administrator must create the `marketplace-codex` GitHub
environment with required reviewers. The workflow checks that protection rule before entering the
environment. OpenAI's documented public flow is portal submission, review, and an explicit publish
action; there is no documented publishing API, so the environment approval is deliberately a named
human attestation rather than a fake API success.
Supply reviewer credentials privately in the portal; artifacts contain only account requirements
and fixture descriptions, never secrets. Preserve the current brand assets for the core update and
use brand-approved assets for the new optional listing.

The core slug is `qodo` on Claude, Codex, and Kiro; Anthropic's directory maps the former
`qodo-skills` slug to `qodo`. `qodo-standards` is a separate optional listing everywhere and never
becomes part of a core update. Provider-visible
completion is still followed by a fresh install and an in-place upgrade acceptance test. The
`qodo-in-harness` deprecation remains blocked until the Codex source cutover passes both tests.

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

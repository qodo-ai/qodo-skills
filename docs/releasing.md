# Releasing Qodo skills

## 1. Prepare one atomic pull request

Edit only canonical files under `skills/` and catalog metadata, then run:

```sh
npm run release:prepare -- \
  --summary "Improve local review guidance" \
  --skill qodo-review=patch
npm test
```

`release:prepare` increments the affected skill and package versions, regenerates Claude, Codex,
Kiro, and release-index artifacts, and writes `releases/v<version>.json`. CI rejects a changed
workflow without a version bump, generated drift, a thin loader, package leakage, or an incomplete
release record.

The pull request must state:

- user-visible behavior and compatibility impact;
- canonical skills and packages changed;
- native hosts actually tested;
- any provider acceptance still pending.

## 2. Publish an immutable GitHub release

The repository administrator must enable GitHub release immutability before the first release.
After merge, run **Release skills** for the prepared version. The workflow:

1. validates the exact merged commit;
2. requires the repository immutability setting;
3. creates annotated tag `v<package-version>`;
4. creates the GitHub release;
5. uploads only `qodo-skills-index.json` and its SHA-256;
6. verifies the published release is immutable and has the exact asset inventory.

The index is metadata for stale-version notices. It contains no workflow body and grants no write
authority. GitHub release publication does not publish the Qodo CLI.

## 3. Ship selected marketplaces

Run **Ship marketplaces** with the immutable tag and any combination of `claude`, `codex`, `kiro`,
or `all`. The action validates the tag/version, regenerates the exact provider packet, and uploads
one artifact per selected provider.

| Provider | Automation | Completion evidence |
|---|---|---|
| Claude Code | packet generation, protected submission pause, then official catalog verification | both selected listings expose the released commit/path |
| Codex | exact portal packet plus protected release-owner gate | portal review/publish completed, then protected environment approved |
| Kiro | packet generation, protected submission pause, then live directory verification | selected Powers expose the expected repository, branch, and paths |

The action prepares every selected packet first. Claude and Kiro verification jobs then wait in
`marketplace-claude` and `marketplace-kiro` so a release owner can complete any provider submission
without starting a second workflow; after approval, the job verifies the live listing and fails if
it is not the selected release. Codex stays human-gated because its documented flow requires portal
submission, review, and explicit publication. Its `marketplace-codex` approval is an attestation
after provider publication, not a substitute for it. All three environments require reviewers.

Core listing identity remains `qodo`. Qodo Standards uses `qodo-standards` and is selected/released
separately. Never create a replacement core listing to perform a source migration.

## 4. Provider acceptance

For every selected provider, record:

1. provider-visible exact commit/path and version;
2. fresh core install with exactly four skills;
3. upgrade from the currently published version without duplicates;
4. Qodo Standards absent until explicitly installed;
5. `qodo-setup`, one read workflow, and one approval-gated write workflow;
6. host-owned update and new-session activation.

Source CI or packet creation alone is not release completion.

## 5. skills.sh channel

No publication API is required: skills.sh installs from this repository. After the immutable tag
and provider projections are validated, smoke-test a core install and update on representative
non-marketplace agents, including multi-agent and project/global scope. Use explicit `--skill`
selection so the optional package cannot appear by accident.

## Rollback

- Skill regression: prepare and publish a new patch restoring the last-good behavior, then ship
  that patch through the affected lifecycle owners.
- Provider packaging regression: keep the existing listing identity and repoint only through the
  provider’s supported reviewed update flow.
- Runtime regression: use the independent Qodo CLI rollback; do not smuggle a binary change into a
  skill release.

Never mutate a published tag, release asset, or provider cache in place.

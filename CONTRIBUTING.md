# Contributing

## Change a skill

You can update a skill entirely in GitHub. No Node installation or local commands are required.

1. Edit `skills/<name>/SKILL.md`. For Codebase Wisdom, use
   `skills/qodo-codebase-wisdom/SKILL.md`. Supporting material stays beside the skill;
   display metadata lives in `distribution/catalog.json`.
2. Open a PR, describe the behavior change, and leave existing versions and generated files alone.
3. Wait for CI, review, and merge. You are finished.

CI generates a temporary package to test your changes without committing it to your PR.
After a successful merge, **Release: Prepare PR** creates or refreshes one separate release
PR with all unreleased changes. It bumps each changed existing skill once by a patch, handles new
skills as initial versions, and regenerates every distribution. A release owner reviews and merges
that PR when ready. No special commit-message format is required.

Kiro reads `main/kiro-power` and `main/kiro-power-standards`. Those generated snapshots change when
the release PR merges. Canonical `skills/` on main may contain newer, unreleased instructions.
Publication and marketplace handoffs follow [the release process](docs/releasing.md).

Keep each source file below 500 lines. Skill removal requires an explicit supported immutable
removal design before it can merge. Intentional minor or major changes should be coordinated with
a release owner; ordinary automation defaults to patch releases.

## Maintainer preparation

Release owners can optionally use local tooling for explicit larger version bumps and recovery:

```sh
npm run release:prepare -- \
  --summary "Explain the user-visible improvement." \
  --skill qodo-review=patch
```

Repeat `--skill <name>=<patch|minor|major>` when one change affects several skills. Use
`<name>=initial` for a newly added skill; pull-request validation rejects `initial` for an
existing one. For marketplace-only packaging changes, use `--package patch` instead.

Review the generated catalog, manifests, skill frontmatter, and immutable
`releases/v<version>.json` record, then run `npm test`.

Do not edit generated manifests or `skills/*/agents/openai.yaml` by hand. Change their
source metadata in the catalog, then regenerate.

## Add a skill

A skill directory requires `SKILL.md` with `name`, `description`, and a `metadata` map
containing `vendor: qodo`, semantic `version`, and string-valued `recommended` fields. Add
its display metadata to the catalog. Prefer one
focused skill over a collection of unrelated modes, and keep supporting material beside the
skill only when progressive disclosure makes the main instructions clearer.

Every Qodo skill must:

- check authentication before protected operations;
- distinguish authentication failure from catalog or command-version failure;
- verify exact commands through CLI help where the catalog can evolve;
- invoke identity checks and every managed read through `qodo read`; the runtime admits only
  catalog entries explicitly marked `mutating: false`;
- invoke writes outside `qodo read`, state that they mutate, and preserve exact user approval;
- preserve user approval gates for local edits and external writes;
- avoid direct Qodo HTTP requests, credentials, provider tokens, and secret output.

Do not add individual Kiro allow patterns when a skill gains a read tool. The generated Power keeps
one stable `qodo read *` pattern, and the CLI catalog classification controls reachability. A new or
reclassified write therefore remains prompted automatically. CI regenerates and verifies the permission template.

Each canonical skill owns its result-presentation instructions in `skills/<name>/SKILL.md`.
Follow the skill's task-specific prose pattern and keep Qodo attribution tied to its actual
contribution. The validator checks that the delivery section exists, includes Qodo attribution,
and has no branded Markdown heading; it does not prescribe the response's exact wording or
establish its quality. When adding a skill, register its delivery section in the validator and
review representative outputs for useful content, accurate attribution, and preserved gates.

## Pull requests

Source PRs describe the user-visible behavior, compatibility impact, and hosts actually tested.
The separate release PR carries versions, generated files, and the immutable release record.
A release owner selects **Approve workflows to run** if GitHub shows that prompt on a bot update,
waits for checks on the latest commit, and merges. This starts **Release: Publish skills**, which retains its
protected approval and compatibility checks. Do not call a package published until publication
succeeds; provider visibility is reported separately by **Marketplaces: Verify listings**.

# Contributing

## Change a skill

You can update an existing skill entirely in GitHub. No Node installation or local commands are
required.

1. Open `skills/<name>/SKILL.md`, click the pencil, and edit the instructions. For Codebase Wisdom,
   the file is `skills/qodo-codebase-wisdom/SKILL.md`.
2. Choose **Create a new branch for this commit and start a pull request** in this repository.
   Describe the behavior you changed. Leave version numbers and generated files to automation.
3. **Prepare skill update** automatically bumps the changed skills and package by one patch,
   regenerates the marketplace copies, and adds the release record to the same PR.
4. A reviewer selects **Approve workflows to run** in the PR merge box after the bot commit.
   Wait for the checks on that commit, review the change, and merge. The first checks may report
   stale generated files while preparation is running; the checks on the bot commit are the ones
   that must pass.

Further instruction edits refresh that same prepared version. If main has advanced, use GitHub's
**Update branch** and resolve any conflicts before preparation runs again. Maintainers can rerun
the preparation action after a transient failure. Review the action summary if no commit appears.

Automatic preparation covers edits to existing `SKILL.md` files on same-repository PRs. New or
removed skills, supporting-file changes, catalog/display metadata, mixed code changes, and intentional
minor/major releases need maintainer preparation. Contributors can still open those PRs in GitHub;
a maintainer handles the packaging. Existing manually prepared releases are left intact. Never edit
the generated marketplace copies yourself.

Keep skill files below 500 lines and keep authentication and API transport behind the `qodo`
command. Merging updates Kiro's main source; immutable release publication and the remaining
marketplace handoffs still follow [the release process](docs/releasing.md).

## Maintainer preparation

The local tooling remains available for structural changes, larger version bumps, and recovery:

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
reclassified write therefore remains prompted automatically. Run `npm run adapters` and `npm test`
to regenerate and verify the permission template.

Each canonical skill owns its result-presentation instructions in `skills/<name>/SKILL.md`.
Follow the skill's task-specific prose pattern and keep Qodo attribution tied to its actual
contribution. The validator checks that the delivery section exists, includes Qodo attribution,
and has no branded Markdown heading; it does not prescribe the response's exact wording or
establish its quality. When adding a skill, register its delivery section in the validator and
review representative outputs for useful content, accurate attribution, and preserved gates.

## Pull requests

Every release-bound pull request is complete: it carries its version and release record. After
merge, the release workflow validates the exact commit, creates the annotated tag, and creates
the GitHub Release. Describe the user-visible behavior, compatibility impact, skill/package
versions, and hosts actually tested. Include native validator output when available. Do not call
a package “published” until the workflow and external marketplace both show the released version.

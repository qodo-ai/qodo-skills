# Contributing

## Change a skill

1. Edit only `skills/<name>/SKILL.md` for workflow behavior.
2. Keep the file below 500 lines and use the `qodo-` lowercase-kebab name.
3. Keep authentication and API transport behind the `qodo` command.
4. Prepare the release atomically:

   ```sh
   npm run release:prepare -- \
     --summary "Explain the user-visible improvement." \
     --skill qodo-review=patch
   ```

   Repeat `--skill <name>=<patch|minor|major>` when one change affects several skills. Use
   `<name>=initial` for a newly added skill; pull-request validation rejects `initial` for an
   existing one. For marketplace-only packaging changes, use `--package patch` instead.
5. Review the generated catalog, manifests, skill frontmatter, and immutable
   `releases/v<version>.json` record.
6. Run `npm test`.

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

Operational skills also expose one meaningful branded value moment. Follow
`docs/architecture.md`: one `# <emoji> Qodo <outcome>` block after a verified result, with useful
scope/count/freshness fields and no promotional or repeated banners. Add the expected heading to
the validator when introducing a skill.

## Pull requests

Every release-bound pull request is complete: it carries its version and release record. After
merge, the release workflow validates the exact commit, creates the annotated tag, and creates
the GitHub Release. Describe the user-visible behavior, compatibility impact, skill/package
versions, and hosts actually tested. Include native validator output when available. Do not call
a package “published” until the workflow and external marketplace both show the released version.

# Contributing

## Change a skill

1. Edit only `skills/<name>/SKILL.md` for workflow behavior.
2. Keep the file below 500 lines and use the `qodo-` lowercase-kebab name.
3. Keep authentication and API transport behind the `qodo` command.
4. Update the skill version in its frontmatter and `distribution/catalog.json`.
5. Update the package version for a release-bound change.
6. Run `npm run adapters` and `npm test`.

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
- state whether operations are read-only or mutating;
- preserve user approval gates for local edits and external writes;
- avoid direct Qodo HTTP requests, credentials, provider tokens, and secret output.

## Pull requests

Describe the user-visible behavior, compatibility impact, skill/package versions, and hosts
actually tested. Include native validator output when available. Do not call a package
“published” until the external marketplace shows the released version.

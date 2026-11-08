# Session operations

Use the same installed launcher as `<cockpit>` for every command. Confirm optional arguments
against `<cockpit> <command> --help` for the bundled snapshot.

| Action | Command |
|---|---|
| List styles | `<cockpit> styles` |
| Resume browser | `<cockpit> serve --session <id> [--style package]` |
| Save a reviewer note | `<cockpit> note --session <id> --pr owner/repo#12 'text'` |
| Save a local mark | `<cockpit> mark --session <id> --pr owner/repo#12 '👍'` |
| Refresh source, retaining local events | `<cockpit> refresh --session <id>` |
| Export locally | `<cockpit> export --session <id> --out /chosen/review.html` |
| Locate data/config | `<cockpit> home` |

Notes and marks are local reviewer feedback, distinct from author-supplied PR Review Notes and
Development Track Notes. Never add `--post` or promise provider synchronization. Local finding
accept/dismiss stances do not mutate Qodo review records. Use qodo-review-resolver when the user
explicitly asks to change stored dispositions, subject to its separate gates.

Refresh recollects evidence and reapplies saved enrichment. Check changed source HEADs, warnings,
review completeness and stale line citations before presenting readiness. A saved session is a
snapshot, not proof the PR has stayed unchanged. Preserve notes and custom style/config files.

Export stays local. It can be opened without the server, but fonts and Mermaid diagrams use
external CDNs; an HTML export is not a guarantee of full offline/air-gapped rendering. Tell the
recipient which external rendering features were actually verified. Review content for private
code, identities and local notes before any separately authorized sharing or publication.

Memory is optional. Fresh product defaults must not create or commit memory repositories.
Inspect `<cockpit> memory` only when needed; preserve existing enabled/disabled choices and data.
Do not run finish/dream to persist learned preferences without the user's intended memory scope.

# User migration

The migration changes the skill lifecycle owner without changing the Qodo account or runtime.

## User states

| Starting state | Action | Safe completion |
|---|---|---|
| CLI only, official listing available | Install Qodo from the host marketplace | New session loads the four core skills |
| CLI only, no listing | Select detected agents, or choose current IDs from `qodo agents catalog`, then run the exact skills.sh command printed by `qodo agents install` | New session loads the selected core skills |
| Plugin first, CLI missing | Follow `qodo-setup` to the checksum-verified CLI installer | `qodo read whoami` and tool refresh succeed |
| Plugin first, CLI logged out | Run `qodo login` | Identity and tool catalog verify |
| Plugin updated before the CLI | Run the skill's unadorned version gate, then approve `qodo update` from the already-recorded public or enterprise origin | The version satisfies the package's `minimumCliVersion` before authentication or managed-tool calls |
| Older CLI-managed copy plus marketplace plugin | Verify the plugin in a new session, then run explicit cleanup | Only byte-identical shipped copies are moved to recoverable hidden quarantine |
| Older CLI-managed copy with edits | Keep it; decide manually | Cleanup reports no retirement |

## Cleanup

The retired CLI installer is not an update path. Its only remaining command is migration cleanup:

```sh
qodo skills cleanup --agent claude-code --global
```

Shared roots such as `.agents/skills` require explicit acknowledgement after every consumer has
migrated:

```sh
qodo skills cleanup --agent codex --global --force-shared
```

Cleanup verifies the immutable CLI-release file set and SHA-256 fingerprints, holds a validated
root identity, then atomically moves the exact copy out of the host skill name. The bytes remain in
a recoverable hidden quarantine because recursively deleting after verification cannot be race-safe.
It never touches a modified file, symlink, unexpected file, unknown version, or current
marketplace/skills.sh package. Codex discovery checks both its current shared root and its historical
`$CODEX_HOME/skills` root.

## Update notices

The CLI emits passive, deduplicated availability and completion notices. Continue the task without
inventory or unsolicited update questions. Old loaded instructions do not prove installed files
are stale. Enterprise installations use their disclosed automatic-maintenance policy, verified
source and opt-outs; other installations keep their lifecycle owner.

For requested maintenance, inspect command support, preview the full packages and physical scope
with `qodo agents update --enterprise --dry-run --json`, then use the returned `--apply-plan` command
only with authorization covering that operation. Older CLIs use interactive enterprise maintenance.
Never expand a narrow approval or add optional packages. Dismissing a notice or declining a manual
update does not disable the existing automatic policy. New sessions load updated files when convenient.

## Runtime compatibility

Skill updates and runtime updates are independent. Every skill therefore runs `qodo --version`
without provenance flags before its first real Qodo command. An older runtime is a compatibility
state, not an authentication failure: the skill must preserve the current task, offer `qodo update`
from the runtime's recorded origin with consent, and stop if compatibility cannot be established.

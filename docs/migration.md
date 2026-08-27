# User migration

The migration changes the skill lifecycle owner without changing the Qodo account or runtime.

## User states

| Starting state | Action | Safe completion |
|---|---|---|
| CLI only, official listing available | Install Qodo from the host marketplace | New session loads the four core skills |
| CLI only, no listing | Select detected agents, or choose current IDs from `qodo agents catalog`, then run the exact skills.sh command printed by `qodo agents install` | New session loads the selected core skills |
| Plugin first, CLI missing | Follow `qodo-setup` to the checksum-verified CLI installer | `qodo whoami` and tool refresh succeed |
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

The CLI refreshes only a compact checksummed version index. When a loaded skill is older, the
command still succeeds and emits `QODO_NOTICE`. The skill must:

1. keep the successful result and finish the task;
2. inventory the lifecycle owner read-only;
3. preserve package, agent, and project/global scope;
4. show a fully resolved update command or host UI action;
5. ask once before mutation;
6. request a new agent session after update.

Declining an update leaves the current skill usable. The CLI never silently performs the update.

## Runtime compatibility

Skill updates and runtime updates are independent. Every skill therefore runs `qodo --version`
without provenance flags before its first real Qodo command. An older runtime is a compatibility
state, not an authentication failure: the skill must preserve the current task, offer `qodo update`
from the runtime's recorded origin with consent, and stop if compatibility cannot be established.

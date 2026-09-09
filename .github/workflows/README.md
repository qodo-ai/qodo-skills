# GitHub Actions guide

For a skill update, edit the canonical source, open a PR, wait for CI, and merge.
Automation prepares a separate release PR. A release owner reviews and merges it, then approves
the existing publication and marketplace gates. Contributors do not need to start any workflow.

| Workflow | Starts automatically when | Use **Run workflow** for |
| --- | --- | --- |
| [CI: Validate distribution](validate.yml) | A PR changes or main receives a push | No manual entry point; rerun a failed check |
| [Release: Prepare PR](prepare-skill-release.yml) | CI succeeds on a main push | Retry release-PR preparation |
| [Release: Publish skills](release.yml) | A release record merges to main | Recover a fully prepared release; normally rerun its captured release run |
| [Marketplaces: Start shipping](marketplace-auto-start.yml) | The hourly check finds a production-compatible release | Recheck readiness now |
| [Marketplaces: Ship release](ship-marketplaces.yml) | Start shipping dispatches a ready release | Retry a specific release/provider handoff |
| [Marketplaces: Verify listings](verify-marketplace-visibility.yml) | Shipping succeeds, or the 15-minute check runs | Inspect provider visibility now |

These six workflows cover separate steps. **Publish skills** creates the immutable GitHub release.
Its approval and App credentials belong to the **skills-release** environment. The
**marketplace-claude**, **marketplace-kiro**, and **marketplace-codex** environments gate provider handoffs.
The CLI repository then promotes its compatibility pointer through the existing production approval.
**Start shipping** waits for that pointer; **Ship release** prepares provider packets and waits for
handoff approvals. **Verify listings** reports when external directories expose the release.
A delayed directory update affects verification independently of shipping.

Workflow filenames remain stable because automation uses them to find previous runs and dispatch
the next step. Shipping run titles retain `Ship marketplaces v<version>` so existing shipments remain
discoverable. Display-name changes must also update matching `workflow_run.workflows` references.

Older E2E and skill-validation workflow entries came from experimental branches and unmerged
PRs #49/#50. They are absent from main and have been disabled in GitHub; their historical runs remain
available. They are not release entry points. GitHub-managed **Copilot code review** is separate
from these repository workflows.

See [Releasing Qodo skills](../../docs/releasing.md) for prerequisites, approvals, and recovery.

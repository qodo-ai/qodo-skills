# Test: 3-round flip-flop (oscillation) at the same file:line

This is a spec-style test case to validate the PR Resolver’s **convergence / oscillation** behavior across three review rounds.

## Setup (shared)

- Location key: `src/example.py:42`
- The resolver uses the decision log keyed by `file:line` as described in `resources/convergence.md`.
- Inline reply formats accepted: `✅ **Fixed** — ...` / `⏭️ **Deferred** — ...` (bolding optional).

## Round 1 (baseline fix)

**Given** a Qodo issue at `src/example.py:42` suggesting **adding** a guard clause.

**When** the resolver applies the fix.

**Then** it must:
- Commit using the resolver signature commit subject: `fix: resolve Qodo review findings`
- Include a structured T1 commit body line keyed by `file:line`, e.g.:
  - `- src/example.py:42 — intent:add-guard — ✅ fixed — <issue title> — <rationale>`
- Reply inline:
  - `✅ **Fixed** — added guard clause to prevent <X>.`

## Round 2 (first contradiction)

**Given** a new Qodo issue at the **same** `src/example.py:42` suggesting the opposite change (e.g., **remove** the guard clause).

**When** Step 3c reloads history and tags the issue.

**Then** it must:
- Detect this as **⚠️ Contradiction** via same `file:line` lookup.
- Default to AskUserQuestion option **Defer**, with options exactly: **Defer / Apply / Modify**.
- If **Defer** is chosen, post a **one-line** inline reply:
  - `🛑 **Defer to prevent oscillation** — deliberate prior-round change (<rationale>, round 1); not reversing automatically. If still a concern, explain why the prior approach is incorrect.`
- Record the outcome in the Step 8 summary under:
  - `Skipped to prevent oscillation — recommend human resolution.`

## Round 3 (2nd flip → hard stop)

**Given** another Qodo issue at the same `src/example.py:42` that would flip direction again.

**When** Step 3c reloads history.

**Then** it must:
- Compute `flip_count >= 2` for `src/example.py:42` (two prior direction flips at this location).
- Enforce the **hard stop**:
  - Refuse to auto-apply at this location even if the user selects **Apply**.
  - Only allow proceeding if the user provides the explicit override message:
    - `OVERRIDE_OSCILLATION_APPLY`
- If override is not provided, it must be summarized under:
  - `Skipped to prevent oscillation — recommend human resolution.`

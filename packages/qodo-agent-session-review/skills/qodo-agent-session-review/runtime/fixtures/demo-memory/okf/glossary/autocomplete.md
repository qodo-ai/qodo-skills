---
type: Glossary Term
title: Autocomplete is ghost_text in code
description: User-facing "Autocomplete" is implemented and logged as ghost_text.
paths: ["src/telemetry/**"]
sources: [{"resource": "session:20260903-141200-0a0a"}]
generated: {"by": "claude/review-prs", "at": "2026-09-03T14:12:00Z"}
status: draft
stale_after: 2026-11-05T00:00:00Z
---
Telemetry events are being renamed from ghost_text_* to autocomplete_*; old names are
emitted as aliases until 2026-11-05.

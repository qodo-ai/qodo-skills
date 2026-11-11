---
type: Invariant
title: Prices and totals are integer cents
description: Every price, line total and order total is an int number of cents. Never floats.
tags: ["payments", "money"]
paths: ["src/payments/**", "src/cache/**"]
sources: [{"resource": "https://github.com/qodo-ai/shop-demo/pull/58", "author": "human:joe"}]
generated: {"by": "claude/review-prs", "at": "2026-09-12T10:20:00Z"}
verified: [{"by": "human:demo-reviewer", "at": "2026-09-12T10:31:00Z"}]
status: stable
---
All money values are stored and computed as integer cents. Rounding happens once,
at the point a percentage is applied, using banker's rounding.

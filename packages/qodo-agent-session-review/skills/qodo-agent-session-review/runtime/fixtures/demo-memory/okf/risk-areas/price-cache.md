---
type: Risk Area
title: Price cache refresh
description: Full reloads of the 2GB price cache caused GC pauses that exhausted the checkout DB pool.
tags: ["performance", "checkout"]
paths: ["src/cache/**"]
sources: [{"resource": "https://github.com/qodo-ai/shop-demo/issues/77"}]
generated: {"by": "devin/2026-10", "at": "2026-09-28T18:40:00Z"}
verified: [{"by": "human:demo-reviewer", "at": "2026-09-29T08:00:00Z"}]
status: stable
---
Any change to cache refresh must say how it behaves on cold start and under stream lag.

---
okf_version: 0.2
---
# Review knowledge

Facts about the code learned while reviewing PRs. Drafts are unconfirmed.

## Glossary Term
- [Autocomplete is ghost_text in code](glossary/autocomplete.md) _(draft)_: User-facing "Autocomplete" is implemented and logged as ghost_text.

## Invariant
- [Prices and totals are integer cents](invariants/prices-in-cents.md): Every price, line total and order total is an int number of cents. Never floats.

## Risk Area
- [Price cache refresh](risk-areas/price-cache.md): Full reloads of the 2GB price cache caused GC pauses that exhausted the checkout DB pool.

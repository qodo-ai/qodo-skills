# Output Format

## Rule List (LIST operation)

Show a compact table followed by a count line. Only include columns that add value for the user's query.

```
**{totalCount} rules** (page {page}/{totalPages})

| ID | Name | Severity | Category | State | Source |
|----|------|----------|----------|-------|--------|
| 123 | No hardcoded credentials | ERROR | Security | active | Code Patterns |
| 456 | Use structured logging | WARNING | Observability | active | ofer@qodo.ai |
...

_Show `get rule <id>` for full content, or ask to filter/sort._
```

- Severity in UPPERCASE.
- Truncate long names at 60 chars with `…`.
- If `totalCount` > `pageSize`, note how to get the next page.

## Single Rule (GET / after CREATE or UPDATE)

**Concise view (default):**

```
**Rule {id}: {name}**
Severity: {SEVERITY} | Category: {category} | State: {state}
Source: {sourceType} — {source}
Scopes: {scopes joined by ", " or "universal (/)"}

{content — first 3 lines, then "… (truncated, ask to expand)"}
```

**Expanded view (on request):**

Show the full rule including `goodExamples` and `badExamples`, formatted as separate blocks.

## After CREATE

```
✅ Rule created — ID: {ruleId}

**{name}** [{SEVERITY}]
{first line of content}
```

## After UPDATE

```
✅ Rule {id} updated.

**{name}** [{SEVERITY}] — {state}
```

## After DELETE

```
✅ Rule {id} ("{name}") deleted.
```

## Similarity Results

```
**Similar rules found:**

| Score | ID | Name | Relationship |
|-------|----|------|--------------|
| 0.92  | 77 | Avoid logging secrets | DUPLICATE |
| 0.78  | 88 | Sanitize log output   | OVERLAPPING |
```

Show scores as percentages rounded to 0 decimal places (e.g. `92%`).

## Severities

Always display severity in UPPERCASE: `ERROR`, `WARNING`, `RECOMMENDATION`.

## Empty Results

```
No rules found matching your filters.
```

Never error on empty — it is a valid state.

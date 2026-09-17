# Admin-Only Operations

`PUT /rule/{id}` (update) and `DELETE /rule/{id}` (delete) require admin access.
Admin = organization owner or team owner.

## Admin Check

There is no dedicated `/me/is-admin` endpoint. The server returns **HTTP 403** when a non-admin calls these endpoints.

**Strategy:** attempt the operation and handle the response:

- **2xx** → success, show result.
- **403** → inform the user clearly (see below). Do not retry.

## 403 Response

When you receive a 403, show:

```
⛔ Admin access required.

This operation (update/delete rule) is only available to organization owners
and team owners. Your current API key does not have admin rights on this workspace.

If you believe this is wrong, check your role at:
  {APP_URL}/account/members
```

Where `APP_URL` is derived from the API URL (reverse the env extraction:
`https://qodo-platform.<env>.qodo.ai` → `https://app.<env>.qodo.ai`).

## Update Flow

1. `GET /rule/{id}` — fetch current rule, display it concisely.
2. Identify what the user wants to change (name, content, severity, state, scopes, etc.).
3. Build the updated rule by merging changes into the current values.
4. Display the proposed update and ask: _"Apply these changes to rule {id}?"_
5. On confirmation, `PUT /rule/{id}` with the full `RuleUpdateRequest` body.

**`RuleUpdateRequest` = `RuleCreateRequest` + `state`**

All fields required:
- `name`, `category`, `severity`, `content`, `goodExamples`, `badExamples` (from RuleCreateRequest)
- `state` — one of: `active`, `pending`, `inactive`

Optional:
- `scopes`, `source`, `sourceType`, `sourceUri`, `suggestionType`

**Common state changes:**

| User says | Set `state` to |
|---|---|
| "activate rule 123" | `active` |
| "deactivate rule 123" | `inactive` |
| "mark as pending" | `pending` |

## Delete Flow

1. `GET /rule/{id}` — fetch rule to confirm it exists and show the user what will be deleted.
2. Ask: _"Are you sure you want to permanently delete rule {id} '{name}'? This cannot be undone."_
3. Only proceed on explicit confirmation ("yes", "confirm", "delete it", etc.).
4. `DELETE /rule/{id}` — expect HTTP 204 on success.

## HTTP Status on Success

| Operation | Success status |
|---|---|
| PUT (update) | 200 — returns updated `Rule` object |
| DELETE | 204 — empty body |

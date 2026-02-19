---
name: qodo-setup
description: "PROACTIVE: Guide users through Qodo authentication when they first use Qodo features. Use when user tries qodo-rules but is not authenticated. Browser-based OIDC login that automatically obtains JWT and saves to ~/.qodo/skill_auth.json for automatic use by other Qodo skills."
---

# Qodo Setup - OIDC Authentication

Browser-based OIDC authentication for Qodo platform in Claude Code skills.

**Script:** `bash .claude/skills/qodo-setup/scripts/qodo-setup.sh`

**Prerequisites:** `curl`, `jq`, browser

---

## When to Use (PROACTIVE)

Use this skill **automatically** when:

1. User tries `/qodo-rules` but gets authentication error
2. User mentions wanting to use Qodo features
3. User asks "how do I set up Qodo?"
4. Any Qodo skill fails due to missing authentication

**Check first:**
```bash
bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --check
```
- Exit code 0 = authenticated (skip setup)
- Exit code 1 = not authenticated (run setup)

---

## Setup Flow

### Check Authentication Status

```bash
bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --check
```

Silent check — returns exit code only:
- **0**: Token is valid, or was expired but successfully refreshed via refresh token
- **1**: Token expired and refresh failed (or no token stored) → re-run `--login`

If the token is expired, `--check` automatically attempts a silent refresh via `POST /auth/v1/oidc/token`. The auth file is updated transparently on success.

### Interactive Browser Login (Primary Method)

```bash
bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --login
```

This command:
1. Initializes OIDC login session with Qodo platform
2. Opens browser to login URL
3. Waits for user to authenticate in browser
4. Polls for authentication completion
5. Receives JWT token and refresh token
6. Detects tenant-specific platform URL (via redirect check)
7. Saves to `~/.qodo/skill_auth.json` (mode 600)
8. Displays user info, platform URL (if tenant-specific), and token expiration

**OIDC Flow:**
- **Init**: POST `/auth/v1/oidc/init_login` with trace_id and init_client=command
- **Open**: Browser opens login_url from response
- **Poll**: Continuously polls `/auth/v1/oidc/poll_token` until HTTP 200
- **Detect**: Calls API to check for tenant redirect (HTTP 409). If redirected, extracts the correct platform URL by replacing `app.` subdomain with `qodo-platform.`
- **Save**: Stores id_token, refresh_token, and platform_url (if tenant-specific)
- **Auto-refresh**: On subsequent `--check`, refreshes expired tokens automatically via `/auth/v1/oidc/token` (preserves platform_url)

### Manual JWT Token (Fallback)

```bash
bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --set-token "eyJhbG..."
```

Use this if browser login fails. Manually validates and saves JWT token.

### Clear Stored Token

```bash
bash .claude/skills/qodo-setup/scripts/qodo-setup.sh --clear
```

Removes stored authentication.

---

## What Gets Saved

After successful token validation:

**Token Storage:** `~/.qodo/skill_auth.json`

```json
{
  "id_token": "eyJhbG...",
  "refresh_token": "",
  "platform_url": "https://qodo-platform.acme-corp.qodo.ai",
  "expires_at": 1234567890,
  "updated_at": 1234567890
}
```

**Fields:**
- `id_token` - JWT for authentication
- `refresh_token` - Token for auto-refresh
- `platform_url` - API base URL, detected automatically after login. Defaults to `https://qodo-platform.qodo.ai`; set to a tenant-specific URL when the user belongs to a dedicated tenant. Used by qodo-rules and other Qodo skills.
- `expires_at` - Token expiration timestamp
- `updated_at` - Last update timestamp

**JWT Claims Extracted:**
- `email` - User identification
- `workspace_id` - **Automatically used by qodo-rules**
- `exp` - Token expiration

**Security:**
- File mode 600 (owner read/write only)
- Directory `~/.qodo/` mode 700

---

## After Setup

Once authenticated, qodo-rules works automatically:

```bash
bash .claude/skills/qodo-rules/scripts/qodo-rules.sh --get
```

The script automatically:
- Reads JWT from `~/.qodo/skill_auth.json`
- Uses token as Bearer authentication for API requests

---

## Guidelines for Claude

- **Always check first** with `--check` before suggesting setup
- **Don't interrupt** if already authenticated
- **When authentication needed:**
  1. Run `--login` to start browser-based OIDC flow
  2. Script will open browser automatically
  3. Wait for polling to complete (shows dots while waiting)
  4. Confirm success by showing extracted user info
- **If login fails:**
  - Offer manual fallback with `--set-token`
  - Guide user to obtain JWT from browser DevTools
- **Guide to next steps** - suggest trying `/qodo-rules --get`
- **If token expires** - `--check` auto-refreshes using the stored refresh token
- **If refresh token also expired** - run `--login` again for full re-authentication

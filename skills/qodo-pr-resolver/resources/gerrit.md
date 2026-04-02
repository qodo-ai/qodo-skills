# Gerrit Provider Reference

Gerrit uses **Changes** (not Pull Requests). All API interactions use `curl` + HTTP Basic Auth — there is no official Gerrit CLI.

**Key differences from other providers:**
- Changes are identified by a `Change-Id` in the commit message (not a branch name)
- Push for review: `git push origin HEAD:refs/for/<target-branch>` (not `git push`)
- All comment operations go through a **single unified endpoint** (`POST /revisions/current/review`)
- Automated tools post as **robot comments** with structured `fix_suggestions`
- All API responses are prefixed with `)]}'` — must strip before JSON parsing

## Provider Detection

Gerrit detection is multi-signal (checked after GitHub/GitLab/Bitbucket/Azure DevOps):

1. **`.gitreview` file** in repo root (strongest signal) — parse `host` and `project` from it
2. **Port `29418`** in SSH remote URL
3. **`googlesource.com`** in remote URL (Google-hosted Gerrit)

```bash
# Check for .gitreview file
if [ -f .gitreview ]; then
  GERRIT_HOST=$(git config -f .gitreview gerrit.host 2>/dev/null)
  GERRIT_PROJECT=$(git config -f .gitreview gerrit.project 2>/dev/null)
fi

# Check remote URL patterns
REMOTE_URL=$(git remote get-url origin)
echo "$REMOTE_URL" | grep -qE ':29418/' && echo "Gerrit (SSH)"
echo "$REMOTE_URL" | grep -q 'googlesource.com' && echo "Gerrit (Google)"
```

## Prerequisites

### Authentication

HTTP Basic Auth with a password generated from Gerrit's settings page.

**Qodo config** (`~/.qodo/config.json`) — store credentials persistently:
```json
{
  "GERRIT_URL": "https://review.example.com",
  "GERRIT_USERNAME": "your-username",
  "GERRIT_HTTP_PASSWORD": "your-http-password"
}
```
- `GERRIT_URL`: Gerrit instance base URL (always required — there is no default host)
- `GERRIT_USERNAME`: Your Gerrit username
- `GERRIT_HTTP_PASSWORD`: HTTP password from **Settings → HTTP Credentials** (this is NOT your account password)

### Extract project info from `.gitreview`

```bash
GERRIT_PROJECT=$(git config -f .gitreview gerrit.project 2>/dev/null)
TARGET_BRANCH=$(git config -f .gitreview gerrit.defaultbranch 2>/dev/null || echo "main")
```

### Magic JSON prefix

All Gerrit REST API responses start with `)]}'` on the first line (XSS protection). Strip it before parsing:
```bash
| tail -c +6 | python3 -m json.tool
```

Every `curl` command in this file includes this pipe.

### Verify

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/accounts/self" | tail -c +6 | python3 -m json.tool
```

**Note:** All authenticated endpoints use the `/a/` prefix in the path.

## Find Open Change

Gerrit has no "source branch" concept. Changes are identified by `Change-Id` from the commit message.

### Extract Change-Id from commit

```bash
CHANGE_ID=$(git log -1 --format=%b | grep -oP 'Change-Id: \K(I[0-9a-f]{40})')
```

### Query by Change-Id (preferred)

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=change:$CHANGE_ID+status:open&o=CURRENT_REVISION&o=MESSAGES" \
  | tail -c +6 | python3 -m json.tool
```

### Query by project + owner (fallback)

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=status:open+project:$GERRIT_PROJECT+owner:self&o=CURRENT_REVISION" \
  | tail -c +6 | python3 -m json.tool
```

Response is a JSON array. Key fields: `_number` (change number), `project`, `branch`, `current_revision`.

## Fetch Review Comments

Gerrit has **three separate comment endpoints**. Fetch all three.

### Robot comments (Qodo reviews)

Qodo posts as robot comments with `robot_id` and optional `fix_suggestions`.

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/<change-id>/robotcomments" \
  | tail -c +6 | python3 -m json.tool
```

Response: map of file paths to arrays of robot comment objects.
Key fields: `id`, `robot_id`, `path`, `line`, `message`, `fix_suggestions`.

Filter for Qodo: check `robot_id` contains `"qodo"`, `"pr-agent"`, or `"codium"`.

### Human comments

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/<change-id>/comments" \
  | tail -c +6 | python3 -m json.tool
```

Same structure as robot comments but without `robot_id` or `fix_suggestions`.

### Change messages (top-level)

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/<change-id>/messages" \
  | tail -c +6 | python3 -m json.tool
```

Returns array of message objects with `id`, `author`, `message`, `date`.

### Robot comment `fix_suggestions`

Robot comments may include structured fix data — prefer these over parsing text:
```json
{
  "fix_suggestions": [{
    "description": "Use secure comparison",
    "replacements": [{
      "path": "src/auth/service.py",
      "range": {
        "start_line": 42, "start_character": 0,
        "end_line": 42, "end_character": 50
      },
      "replacement": "if hmac.compare_digest(token, expected):"
    }]
  }]
}
```

## Reply to Comments

All comment operations use a **single unified endpoint**:

```
POST /a/changes/<change-id>/revisions/current/review
```

### Reply to an inline comment (human or robot)

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X POST \
  "$GERRIT_URL/a/changes/<change-id>/revisions/current/review" \
  -d '{
    "comments": {
      "<file-path>": [{
        "in_reply_to": "<comment-id>",
        "message": "<reply-body>",
        "unresolved": false
      }]
    }
  }' | tail -c +6
```

- `in_reply_to`: the comment's `id` field (works for both robot and human comments)
- `unresolved: false` resolves the thread in the same call — no separate resolve step needed

**Reply format** (same as other providers):
- **Fixed:** `✅ **Fixed** — <brief description>`
- **Deferred:** `⏭️ **Deferred** — <reason>`

### Batch multiple replies

Multiple replies across files can be combined in a single request:
```json
{
  "comments": {
    "file1.py": [{"in_reply_to": "id1", "message": "Fixed", "unresolved": false}],
    "file2.py": [{"in_reply_to": "id2", "message": "Deferred", "unresolved": true}]
  }
}
```

## Post Summary Comment

Uses the same unified endpoint with the `message` field:

```bash
curl -s -u "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X POST \
  "$GERRIT_URL/a/changes/<change-id>/revisions/current/review" \
  -d '{"message": "<summary-comment-body>"}' | tail -c +6
```

**Optimization:** Summary and all inline replies can be batched in a single request:
```json
{
  "message": "## Qodo Fix Summary\n...",
  "comments": {
    "file1.py": [{"in_reply_to": "id1", "message": "Fixed", "unresolved": false}]
  }
}
```

Summary format: same as [providers.md § Summary format](./providers.md#post-summary-comment).

## Resolve Comments

Resolution is part of the reply — set `"unresolved": false` in the reply payload.

No separate resolve API call is needed. If replies in the Reply step already set `"unresolved": false`, all resolved issues are handled automatically.

To resolve without replying (empty message):
```json
{
  "comments": {
    "<file-path>": [{
      "in_reply_to": "<comment-id>",
      "message": "",
      "unresolved": false
    }]
  }
}
```

## Push Changes

Gerrit does **not** use normal `git push`.

### Push to existing change (new patch set)

```bash
TARGET_BRANCH=$(git config -f .gitreview gerrit.defaultbranch 2>/dev/null || echo "main")
git push origin HEAD:refs/for/$TARGET_BRANCH
```

This creates a new patch set on the existing change (matched by `Change-Id` in commit message).

### Push with topic

```bash
git push origin HEAD:refs/for/$TARGET_BRANCH%topic=qodo-fixes
```

## Create Change

No API call needed — pushing creates the change automatically:

```bash
TARGET_BRANCH=$(git config -f .gitreview gerrit.defaultbranch 2>/dev/null || echo "main")
git push origin HEAD:refs/for/$TARGET_BRANCH
```

The commit must have a `Change-Id` footer. If missing, install the commit-msg hook:
```bash
scp -p -P 29418 $GERRIT_USERNAME@$GERRIT_HOST:hooks/commit-msg .git/hooks/
```

## Error Handling

### Missing environment variables

If `GERRIT_URL`, `GERRIT_USERNAME`, or `GERRIT_HTTP_PASSWORD` is unset:
- Inform: "Missing Gerrit authentication. Add these to `~/.qodo/config.json`:"
- List all three keys with descriptions
- Exit the skill

### No Change-Id in commit

If `Change-Id` grep returns empty:
- Inform: "No Change-Id found in commit message."
- Suggest installing the hook: `scp -p -P 29418 <user>@<host>:hooks/commit-msg .git/hooks/`
- Exit the skill

### API authentication failure (HTTP 401)

- Inform: "Gerrit authentication failed. Check `GERRIT_USERNAME` and `GERRIT_HTTP_PASSWORD`."
- Note: HTTP password is generated at **Settings → HTTP Credentials**, not the account password
- Exit the skill

### Change URL format

For Step 10 (Show PR URL), the Gerrit change URL is:
```
🔗 Change: https://<gerrit-host>/c/<project>/+/<change-number>
```

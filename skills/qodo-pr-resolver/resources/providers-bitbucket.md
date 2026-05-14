# Bitbucket Provider Commands

Concrete `curl`-based commands for the Qodo PR Resolver skill on Bitbucket Cloud. For cross-cutting principles (body-via-file, reply format, atomic publish rationale, summary template) see [providers.md](./providers.md).

## Prerequisites

**Authentication:** Bitbucket REST API with an App Password (there is no official `bb` CLI).

- Create an App Password: Bitbucket → **Settings → App passwords**
  - Required scopes: **Repositories: Read**, **Pull requests: Read, Write**
- **Qodo config** (`~/.qodo/config.json`) — store credentials persistently:
  ```json
  {
    "BB_USERNAME": "your-bitbucket-username",
    "BB_APP_PASSWORD": "your-app-password",
    "BB_URL": "https://bitbucket.example.com"
  }
  ```
  `BB_URL` is optional — only needed for self-hosted Bitbucket (defaults to `https://api.bitbucket.org`).
- Workspace and repo slug are extracted from the remote URL at runtime:
  ```bash
  BB_REMOTE=$(git remote get-url origin)
  BB_WORKSPACE=$(echo "$BB_REMOTE" | sed -E 's|.*bitbucket\.org[:/]([^/]+)/.*|\1|')
  BB_REPO=$(echo "$BB_REMOTE" | sed -E 's|.*bitbucket\.org[:/][^/]+/([^/.]+)(\.git)?$|\1|')
  ```
- **Verify:**
  ```bash
  curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
    "https://api.bitbucket.org/2.0/user" | python3 -m json.tool
  ```

## Find Open PR/MR

```bash
BRANCH=$(git branch --show-current)
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests?state=OPEN" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
branch = '$BRANCH'
for pr in data.get('values', []):
    if pr['source']['branch']['name'] == branch:
        print(json.dumps({'id': pr['id'], 'title': pr['title']}, indent=2))
"
```

## Fetch Review Comments

Bitbucket returns inline and top-level comments through a single endpoint.

```bash
# All PR comments including inline comments
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments"
```

## Reply to Inline Comments

```bash
# JSON body file: {"content": {"raw": "<reply-body>"}, "parent": {"id": <inline-comment-id>}}
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments" \
  -d @<path-to-bitbucket-reply.json>
```

## Post Summary Comment

```bash
# JSON body file: {"content": {"raw": "<comment-body>"}}
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments" \
  -d @<path-to-bitbucket-summary.json>
```

## Edit Posted Summary in Place

```bash
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X PUT \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments/<comment-id>" \
  -d '{"content":{"raw":"<fixed-body>"}}'
```

## Atomic Publish (push + summary + replies)

```bash
git push && \
  curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" -X POST \
    "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments" \
    -H "Content-Type: application/json" -d @<summary.json> && \
  curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" -X POST \
    "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments" \
    -H "Content-Type: application/json" -d @<reply.json>
```

Repeat the reply curl for each inline comment. If all issues were deferred and no commits were created, drop the `git push &&` prefix.

## Resolve Qodo Review Comment

```bash
# Resolve a comment using the dedicated /resolve endpoint (POST, no body required)
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>/comments/<comment-id>/resolve"
```

## Create PR/MR

```bash
BRANCH=$(git branch --show-current)
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests" \
  -d "{
    \"title\": \"<title>\",
    \"description\": \"<body>\",
    \"source\": {\"branch\": {\"name\": \"$BRANCH\"}},
    \"destination\": {\"branch\": {\"name\": \"main\"}}
  }"
```

**Note:** Bitbucket Cloud has no native draft PR API. When creating in draft mode, prefix the title with `[DRAFT]` as a convention (e.g. `[DRAFT] <title>`).

## Mark PR Ready for Review

If the title was prefixed with `[DRAFT]`, update it to remove the prefix:

```bash
curl -s -u "$BB_USERNAME:$BB_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -X PUT \
  "https://api.bitbucket.org/2.0/repositories/$BB_WORKSPACE/$BB_REPO/pullrequests/<pr-id>" \
  -d '{"title": "<title-without-draft-prefix>"}'
```

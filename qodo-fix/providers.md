# Provider CLI Reference

## Provider Detection

Match `git remote get-url origin` against:

| Remote URL contains | Provider | CLI |
|---|---|---|
| `github.com` | GitHub | `gh` |
| `gitlab.com` | GitLab | `glab` |
| `bitbucket.org` | Bitbucket | `bb` |
| `dev.azure.com` | Azure DevOps | `az` |

## Bot Identifiers

Look for comments from: **`pr-agent-pro`**, **`pr-agent-pro-staging`**, **`qodo-merge[bot]`**, **`qodo-ai[bot]`**

## Find Open PR/MR

**GitHub:**
```bash
gh pr list --head <branch-name> --state open --json number,title
```

**GitLab:**
```bash
glab mr list --source-branch <branch-name> --state opened
```

**Bitbucket:**
```bash
bb pr list --source-branch <branch-name> --state OPEN
```

**Azure DevOps:**
```bash
az repos pr list --source-branch <branch-name> --status active --output json
```

## Get Review Comments

Qodo posts both a **summary comment** (PR-level, all issues) and **inline review comments** (per-line). Fetch both.

**GitHub:**
```bash
# PR-level comments (summary)
gh pr view <pr-number> --json comments

# Inline review comments (per-line)
gh api repos/{owner}/{repo}/pulls/<pr-number>/comments
```

**GitLab:**
```bash
# All MR notes including inline comments
glab mr view <mr-iid> --comments
```

**Bitbucket:**
```bash
# All PR comments including inline comments
bb pr view <pr-id> --comments
```

**Azure DevOps:**
```bash
# PR-level threads (includes summary comments)
az repos pr show --id <pr-id> --output json

# All PR threads including inline comments
az repos pr policy list --id <pr-id> --output json
az repos pr thread list --id <pr-id> --output json
```

## Inline Reply to Issue Comment

Use the inline comment ID preserved during deduplication.

**GitHub:**
```bash
gh api repos/{owner}/{repo}/pulls/<pr-number>/comments/<inline-comment-id>/replies -X POST -f body='<reply-body>'
```

**GitLab:**
```bash
glab api "/projects/:id/merge_requests/<mr-iid>/discussions/<discussion-id>/notes" -X POST -f body='<reply-body>'
```

**Bitbucket:**
```bash
bb api "/2.0/repositories/{workspace}/{repo}/pullrequests/<pr-id>/comments" -X POST -f 'content.raw=<reply-body>' -f 'parent.id=<inline-comment-id>'
```

**Azure DevOps:**
```bash
az repos pr thread comment add --id <pr-id> --thread-id <thread-id> --content '<reply-body>'
```

Reply format:
- **Fixed:** `✅ **Fixed** — <brief description of what was changed>`
- **Deferred:** `⏭️ **Deferred** — <reason for deferring>`

Keep replies short (one line). If a reply fails, log it and continue.

## Post Summary Comment

**GitHub:**
```bash
gh pr comment <pr-number> --body '<summary>'
```

**GitLab:**
```bash
glab mr comment <mr-iid> --message '<summary>'
```

**Bitbucket:**
```bash
bb pr comment <pr-id> --message '<summary>'
```

**Azure DevOps:**
```bash
az repos pr thread create --id <pr-id> --content '<summary>'
```

## Resolve Qodo Review Comment

Find the Qodo "Code Review by Qodo" comment by fetching all PR/MR comments, matching a Qodo bot author whose body contains "Code Review by Qodo".

**GitHub:** Fetch comments via `gh pr view <pr-number> --json comments`, find the comment ID, then react with:
```bash
gh api "repos/{owner}/{repo}/issues/comments/<comment-id>/reactions" -X POST -f content='+1'
```

**GitLab:** Fetch discussions via `glab api "/projects/:id/merge_requests/<mr-iid>/discussions"`, find the discussion ID, then resolve:
```bash
glab api "/projects/:id/merge_requests/<mr-iid>/discussions/<discussion-id>" -X PUT -f resolved=true
```

**Bitbucket:** Fetch comments via `bb api`, find the comment ID, then update to resolved status.

If resolve fails (comment not found, API error), continue -- the summary comment is the important part.

## CLI Installation

- **GitHub `gh`**: `brew install gh` or [cli.github.com](https://cli.github.com/) -- authenticate with `gh auth login`
- **GitLab `glab`**: `brew install glab` or [glab.readthedocs.io](https://glab.readthedocs.io/) -- authenticate with `glab auth login`
- **Bitbucket `bb`**: See [bitbucket.org/product/cli](https://bitbucket.org/product/cli)
- **Azure DevOps `az`**: `brew install azure-cli` or [docs.microsoft.com/cli/azure](https://docs.microsoft.com/cli/azure) -- then `az extension add --name azure-devops`, `az login`, `az devops configure --defaults organization=https://dev.azure.com/yourorg project=yourproject`

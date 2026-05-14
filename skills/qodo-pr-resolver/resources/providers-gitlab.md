# GitLab Provider Commands

Concrete `glab`-based commands for the Qodo PR Resolver skill on GitLab. For cross-cutting principles (body-via-file, reply format, atomic publish rationale, summary template) see [providers.md](./providers.md).

## Prerequisites

**CLI:** `glab`
- **Install:** `brew install glab` or [glab.readthedocs.io](https://glab.readthedocs.io/)
- **Authenticate:** `glab auth login`
- **Verify:**
  ```bash
  glab --version && glab auth status
  ```

## Find Open PR/MR

```bash
glab mr list --source-branch <branch-name>
```

## Fetch Review Comments

GitLab returns inline and top-level comments through a single endpoint. Run as a parallel tool call alongside the other fetches in the skill's Step 3.

```bash
# All MR notes including inline comments
glab mr view <mr-iid> --comments
```

## Reply to Inline Comments

```bash
glab api "/projects/:id/merge_requests/<mr-iid>/discussions/<discussion-id>/notes" \
  -X POST \
  -F body=@<path-to-reply-body>
```

## Post Summary Comment

```bash
glab api "/projects/:id/merge_requests/<mr-iid>/notes" \
  -X POST \
  -F body=@<path-to-summary>
```

(Use `glab api` rather than `glab mr comment` since the latter has no `--message-file` flag.)

## Edit Posted Summary in Place

```bash
glab api "/projects/:id/merge_requests/<mr-iid>/notes/<note-id>" \
  -X PUT -F body=@<path-to-fixed-body>
```

## Atomic Publish (push + summary + replies)

```bash
git push && \
  glab api "/projects/:id/merge_requests/<mr-iid>/notes" -X POST -F body=@<summary-path> && \
  glab api "/projects/:id/merge_requests/<mr-iid>/discussions/<id>/notes" -X POST -F body=@<reply-path>
```

Repeat the inline-reply line for each discussion. If all issues were deferred and no commits were created, drop the `git push &&` prefix.

## Resolve Qodo Review Comment

```bash
# 1. Fetch discussions to find the discussion ID
glab api "/projects/:id/merge_requests/<mr-iid>/discussions"

# 2. Resolve the discussion
glab api "/projects/:id/merge_requests/<mr-iid>/discussions/<discussion-id>" \
  -X PUT \
  -f resolved=true
```

## Create PR/MR

```bash
glab mr create --title '<title>' --description '<body>'
```

Add `--draft` flag when creating in draft mode.

## Mark PR Ready for Review

```bash
glab mr update <mr-iid> --ready
```

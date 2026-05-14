# GitHub Provider Commands

Concrete `gh`-based commands for the Qodo PR Resolver skill on GitHub. For cross-cutting principles (body-via-file, reply format, atomic publish rationale, summary template) see [providers.md](./providers.md).

## Prerequisites

**CLI:** `gh`
- **Install:** `brew install gh` or [cli.github.com](https://cli.github.com/)
- **Authenticate:** `gh auth login`
- **Verify:**
  ```bash
  gh --version && gh auth status
  ```

## Find Open PR/MR

```bash
gh pr list --head <branch-name> --state open --json number,title
```

## Fetch Review Comments

Run these three calls in parallel (single multi-tool-call message, not serially). On rate-limit (403), retry just the failed call.

```bash
# PR-level comments (includes the summary comment with all issues)
gh pr view <pr-number> --json comments

# Inline review comments (per-line comments on specific code)
gh api repos/{owner}/{repo}/pulls/<pr-number>/comments

# Review submission bodies (Qodo's main review sometimes lands here, esp. CHANGES_REQUESTED)
# Skip entries with empty body unless state is CHANGES_REQUESTED.
gh api repos/{owner}/{repo}/pulls/<pr-number>/reviews
```

## Reply to Inline Comments

```bash
gh api repos/{owner}/{repo}/pulls/<pr-number>/comments/<inline-comment-id>/replies \
  -X POST \
  -F body=@<path-to-reply-body>
```

## Post Summary Comment

```bash
gh pr comment <pr-number> --body-file <path-to-summary>
```

## Edit Posted Summary in Place

```bash
gh api -X PATCH repos/{owner}/{repo}/issues/comments/<comment-id> \
  -F body=@<path-to-fixed-body>
```

## Atomic Publish (push + summary + replies)

```bash
git push && \
  gh pr comment <pr-number> --body-file <summary-path> && \
  gh api repos/<owner>/<repo>/pulls/<pr-number>/comments/<inline-id-A>/replies -X POST -F body=@<reply-A-path> && \
  gh api repos/<owner>/<repo>/pulls/<pr-number>/comments/<inline-id-B>/replies -X POST -F body=@<reply-B-path> && \
  gh api -X POST repos/<owner>/<repo>/issues/comments/<qodo-summary-id>/reactions -f content=+1
```

Repeat the inline-reply line for each comment. If a reply fails the chain stops — intentional, don't leave the bot acknowledging a fix that never published. If all issues were deferred and no commits were created, drop the `git push &&` prefix.

## Resolve Qodo Review Comment

```bash
# 1. Fetch comments to find the comment ID
gh pr view <pr-number> --json comments

# 2. React with thumbs up to acknowledge
gh api "repos/{owner}/{repo}/issues/comments/<comment-id>/reactions" \
  -X POST \
  -f content='+1'
```

## Create PR/MR

```bash
gh pr create --title '<title>' --body '<body>'
```

Add `--draft` flag when creating in draft mode.

## Mark PR Ready for Review

```bash
gh pr ready <pr-number>
```

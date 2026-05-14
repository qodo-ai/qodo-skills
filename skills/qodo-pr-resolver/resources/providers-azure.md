# Azure DevOps Provider Commands

Concrete `az`-based commands for the Qodo PR Resolver skill on Azure DevOps. For cross-cutting principles (body-via-file, reply format, atomic publish rationale, summary template) see [providers.md](./providers.md).

## Prerequisites

**CLI:** `az` with DevOps extension
- **Install:** `brew install azure-cli` or [docs.microsoft.com/cli/azure](https://docs.microsoft.com/cli/azure)
- **Install extension:** `az extension add --name azure-devops`
- **Qodo config** (`~/.qodo/config.json`) — optional, for non-interactive auth:
  ```json
  {
    "AZURE_DEVOPS_EXT_PAT": "your-personal-access-token",
    "AZURE_DEVOPS_URL": "https://dev.azure.com"
  }
  ```
  `AZURE_DEVOPS_EXT_PAT` replaces `az login`. `AZURE_DEVOPS_URL` is optional — only needed for on-premises Azure DevOps Server.
- **Authenticate and configure:**
  ```bash
  az login
  # Extract org/project from remote URL and configure defaults:
  ADO_REMOTE=$(git remote get-url origin)
  ADO_ORG=$(echo "$ADO_REMOTE" | sed -E 's|https://[^@]*@?dev\.azure\.com/([^/]+)/.*|\1|')
  ADO_PROJECT=$(echo "$ADO_REMOTE" | sed -E 's|https://[^/]*/[^/]+/([^/]+)/.*|\1|')
  ADO_REPO=$(echo "$ADO_REMOTE" | sed -E 's|.*/([^/]+)$|\1|')
  az devops configure --defaults organization=https://dev.azure.com/$ADO_ORG project=$ADO_PROJECT
  # Get repository ID (required for thread API calls):
  ADO_REPO_ID=$(az repos show --name $ADO_REPO --query id -o tsv)
  ```
- **Verify:**
  ```bash
  az --version && az devops configure --list
  ```

## Find Open PR/MR

```bash
az repos pr list --source-branch <branch-name> --status active --output json
```

## Fetch Review Comments

Azure DevOps returns inline and top-level comments via the threads endpoint.

```bash
# List all PR threads (includes both summary and inline comments)
# Note: az repos pr thread subcommands do not exist — use az devops invoke
az devops invoke \
  --area git \
  --resource pullRequestThreads \
  --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> \
  --http-method GET \
  --api-version 7.1 \
  --output json
```

## Reply to Inline Comments

```bash
# Add a reply comment to an existing thread (az repos pr thread does not exist)
echo '{"content": "<reply-body>", "commentType": 1}' > /tmp/ado_comment.json
az devops invoke \
  --area git \
  --resource pullRequestThreadComments \
  --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> threadId=<thread-id> \
  --http-method POST \
  --api-version 7.1 \
  --in-file /tmp/ado_comment.json \
  --output json
```

## Post Summary Comment

```bash
# Create a new top-level comment thread (az repos pr thread create does not exist)
cat > /tmp/ado_thread.json << 'EOF'
{"comments": [{"content": "<comment-body>", "commentType": 1}], "status": "active"}
EOF
az devops invoke \
  --area git \
  --resource pullRequestThreads \
  --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> \
  --http-method POST \
  --api-version 7.1 \
  --in-file /tmp/ado_thread.json \
  --output json
```

## Edit Posted Summary in Place

```bash
az devops invoke --area git --resource pullRequestThreadComments \
  --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> threadId=<thread-id> commentId=<comment-id> \
  --http-method PATCH --api-version 7.1 --in-file /tmp/ado_comment_patch.json --output json
```

## Atomic Publish (push + summary + replies)

```bash
git push && \
  az devops invoke --area git --resource pullRequestThreads \
    --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> \
    --http-method POST --api-version 7.1 --in-file <summary.json> --output json && \
  az devops invoke --area git --resource pullRequestThreadComments \
    --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> threadId=<thread-id> \
    --http-method POST --api-version 7.1 --in-file <reply.json> --output json
```

Repeat the reply invocation for each inline comment thread. If all issues were deferred and no commits were created, drop the `git push &&` prefix.

## Resolve Qodo Review Comment

```bash
# Mark the thread as fixed (Azure DevOps uses "fixed" not "resolved"; az repos pr thread update does not exist)
echo '{"status": "fixed"}' > /tmp/ado_status.json
az devops invoke \
  --area git \
  --resource pullRequestThreads \
  --route-parameters project=$ADO_PROJECT repositoryId=$ADO_REPO_ID pullRequestId=<pr-id> threadId=<thread-id> \
  --http-method PATCH \
  --api-version 7.1 \
  --in-file /tmp/ado_status.json \
  --output json
```

## Create PR/MR

```bash
az repos pr create \
  --title '<title>' \
  --description '<body>' \
  --source-branch <branch-name> \
  --target-branch main
```

Add `--draft` flag when creating in draft mode.

## Mark PR Ready for Review

```bash
az repos pr update --id <pr-id> --draft false
```

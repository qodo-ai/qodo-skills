#!/usr/bin/env bash
# Fail closed before a release tag or draft can be created.
# The administrator-only bypass audit is scripts/audit-release-protections.sh.
# Usage: GH_TOKEN=<workflow-token> GITHUB_REPOSITORY=owner/repo scripts/verify-release-prerequisites.sh
set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  echo "Release preflight requires 'gh', but it is not available." >&2
  exit 1
}

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo 'An installation-wide, read-only GitHub App token with Administration:read is required for release preflight.' >&2
  exit 1
fi

INSTALLATION_REPOSITORIES="$(gh api --paginate 'installation/repositories?per_page=100' \
  --jq '.repositories[].full_name')"
if [[ "${INSTALLATION_REPOSITORIES}" != "${GITHUB_REPOSITORY}" ]]; then
  echo 'qodo-skills-release-bot must be installed on qodo-ai/qodo-skills and no other repository.' >&2
  exit 1
fi

if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/immutable-releases" --jq '.enabled')" != 'true' ]]; then
  echo 'Release immutability is disabled. Enable it before creating a tag or release.' >&2
  exit 1
fi

RULESET_IDS="$(gh api --paginate "repos/${GITHUB_REPOSITORY}/rulesets?per_page=100" --jq '.[] | select(
  .name == "Immutable release tags" and .target == "tag" and .enforcement == "active"
) | .id')"
if [[ -z "${RULESET_IDS}" ]]; then
  echo 'Exactly one active Immutable release tags ruleset is required.' >&2
  exit 1
fi
RULESET_COUNT=0
RULESET_ID=''
while IFS= read -r candidate; do
  if [[ -n "${candidate}" ]]; then
    RULESET_COUNT=$((RULESET_COUNT + 1))
    RULESET_ID="${candidate}"
  fi
done <<< "${RULESET_IDS}"
if [[ "${RULESET_COUNT}" -ne 1 ]]; then
  echo 'Exactly one active Immutable release tags ruleset is required.' >&2
  exit 1
fi
if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/rulesets/${RULESET_ID}" --jq '
  (.conditions.ref_name.include == ["refs/tags/v*"]) and
  (.conditions.ref_name.exclude | type == "array" and length == 0) and
  ([.rules[].type] | sort == ["deletion", "update"]) and
  ([.rules[].type] | index("creation")) == null and
  ((has("bypass_actors") | not) or (.bypass_actors | type == "array" and length == 0))
')" != 'true' ]]; then
  echo 'The active, exact-target Immutable release tags ruleset must protect only update/deletion, permit creation, and expose no bypass actors when visible.' >&2
  exit 1
fi

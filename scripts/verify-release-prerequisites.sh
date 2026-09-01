#!/usr/bin/env bash
# Fail closed before a release tag or draft can be created.
# Usage: GH_TOKEN=<release-token> GITHUB_REPOSITORY=owner/repo scripts/verify-release-prerequisites.sh
set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  echo "Release preflight requires 'gh', but it is not available." >&2
  exit 1
}

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo 'QODO_RELEASE_ADMIN_TOKEN is required with repository Administration:read and Contents:read/write.' >&2
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
  (.conditions.ref_name.include | index("refs/tags/v*")) != null and
  (.conditions.ref_name.exclude | type == "array" and length == 0) and
  ([.rules[].type] | contains(["update", "deletion"])) and
  ([.rules[].type] | index("creation")) == null and
  (.bypass_actors | type == "array" and length == 0)
')" != 'true' ]]; then
  echo 'The active, no-exclusion, no-bypass Immutable release tags ruleset must protect update/deletion, permit creation, and cover refs/tags/v*.' >&2
  exit 1
fi

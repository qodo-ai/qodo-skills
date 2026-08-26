#!/usr/bin/env bash
# Fail closed before creating or advancing Kiro's provider-visible release branch.
# Usage: GH_TOKEN=<release-token> GITHUB_REPOSITORY=<owner/repo> scripts/verify-kiro-release-source.sh
set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  echo "Kiro release-source preflight requires 'gh', but it is not available." >&2
  exit 1
}
if [[ -z "${GH_TOKEN:-}" ]]; then
  echo 'QODO_RELEASE_ADMIN_TOKEN is required with repository Administration:read and Contents:read/write.' >&2
  exit 1
fi

RELEASE_ACTOR_ID="$(gh api user --jq '.id')"
if [[ ! "${RELEASE_ACTOR_ID}" =~ ^[0-9]+$ ]]; then
  echo 'QODO_RELEASE_ADMIN_TOKEN must identify one GitHub user with a numeric actor id.' >&2
  exit 1
fi

RULESET_IDS="$(gh api --paginate "repos/${GITHUB_REPOSITORY}/rulesets?per_page=100" --jq '.[] | select(
  .name == "Kiro marketplace release" and .target == "branch" and .enforcement == "active"
) | .id')"
RULESET_COUNT=0
RULESET_ID=''
while IFS= read -r candidate; do
  if [[ -n "${candidate}" ]]; then
    RULESET_COUNT=$((RULESET_COUNT + 1))
    RULESET_ID="${candidate}"
  fi
done <<< "${RULESET_IDS}"
if [[ "${RULESET_COUNT}" -ne 1 ]]; then
  echo 'Exactly one active Kiro marketplace release branch ruleset is required.' >&2
  exit 1
fi

if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/rulesets/${RULESET_ID}" --jq '
  (.conditions.ref_name.include == ["refs/heads/marketplace-kiro"]) and
  (.conditions.ref_name.exclude | type == "array" and length == 0) and
  ([.rules[].type] | contains(["update", "deletion", "non_fast_forward"])) and
  ([.rules[].type] | index("creation")) == null and
  (.bypass_actors | type == "array" and length == 1) and
  (.bypass_actors[0].bypass_mode == "always") and
  (.bypass_actors[0].actor_id == '"${RELEASE_ACTOR_ID}"')
')" != 'true' ]]; then
  echo 'Kiro marketplace release ruleset must protect update/deletion/force-push, permit creation, cover only refs/heads/marketplace-kiro, and have exactly one always-bypass release identity.' >&2
  exit 1
fi

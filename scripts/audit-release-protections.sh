#!/usr/bin/env bash
# Administrator-only audit for repository settings hidden from workflow tokens.
# Usage: GITHUB_REPOSITORY=qodo-ai/qodo-skills scripts/audit-release-protections.sh
set -euo pipefail

for tool in gh grep jq; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Release protection audit requires '${tool}', but it is not available." >&2
    exit 1
  }
done

if [[ "${GITHUB_REPOSITORY:-}" != 'qodo-ai/qodo-skills' ]]; then
  echo 'GITHUB_REPOSITORY must be qodo-ai/qodo-skills.' >&2
  exit 1
fi

if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/immutable-releases" --jq '.enabled')" != 'true' ]]; then
  echo 'Release immutability is disabled.' >&2
  exit 1
fi

ENVIRONMENT_JSON="$(gh api "repos/${GITHUB_REPOSITORY}/environments/marketplace-kiro")"
if [[ "$(jq '
  any(.protection_rules[]?;
    .type == "required_reviewers" and
    (.reviewers | type == "array" and length >= 1)
  )
' <<< "${ENVIRONMENT_JSON}")" != 'true' ]]; then
  echo 'marketplace-kiro must require at least one release reviewer.' >&2
  exit 1
fi

RELEASE_APP_ID="$(gh api \
  "repos/${GITHUB_REPOSITORY}/environments/marketplace-kiro/variables/QODO_SKILLS_RELEASE_APP_ID" \
  --jq '.value')"
if [[ ! "${RELEASE_APP_ID}" =~ ^[0-9]+$ ]]; then
  echo 'marketplace-kiro must define numeric QODO_SKILLS_RELEASE_APP_ID.' >&2
  exit 1
fi

if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/environments/marketplace-kiro/secrets" --jq '
  [.secrets[].name] | index("QODO_SKILLS_RELEASE_APP_PRIVATE_KEY") != null
')" != 'true' ]]; then
  echo 'marketplace-kiro must define QODO_SKILLS_RELEASE_APP_PRIVATE_KEY.' >&2
  exit 1
fi

APP_JSON="$(gh api /apps/qodo-skills-release-bot)"
if [[ "$(jq --argjson release_app_id "${RELEASE_APP_ID}" '
  (.id == $release_app_id) and
  (.slug == "qodo-skills-release-bot") and
  (.owner.login == "qodo-ai") and
  (.permissions == {"administration":"read","contents":"write","metadata":"read"})
' <<< "${APP_JSON}")" != 'true' ]]; then
  echo 'qodo-skills-release-bot must be owned by qodo-ai and have only Administration:read, Contents:write, and Metadata:read.' >&2
  exit 1
fi

INSTALLATION_IDS="$(gh api --paginate "orgs/qodo-ai/installations?per_page=100" --jq ".installations[] | select(
  .app_id == ${RELEASE_APP_ID} and .suspended_at == null
) | .id")"
INSTALLATION_COUNT=0
INSTALLATION_ID=''
while IFS= read -r candidate; do
  if [[ -n "${candidate}" ]]; then
    INSTALLATION_COUNT=$((INSTALLATION_COUNT + 1))
    INSTALLATION_ID="${candidate}"
  fi
done <<< "${INSTALLATION_IDS}"
if [[ "${INSTALLATION_COUNT}" -ne 1 ]]; then
  echo 'qodo-skills-release-bot must have exactly one active qodo-ai installation.' >&2
  exit 1
fi
if ! INSTALLATION_REPOSITORIES="$(gh api --paginate \
  "user/installations/${INSTALLATION_ID}/repositories?per_page=100" \
  --jq '.repositories[].full_name')"; then
  echo 'Could not inspect the release App installation; authenticate gh with read:user and retry.' >&2
  exit 1
fi
if ! grep -Fxq "${GITHUB_REPOSITORY}" <<< "${INSTALLATION_REPOSITORIES}"; then
  echo 'qodo-skills-release-bot is not installed on qodo-ai/qodo-skills.' >&2
  exit 1
fi

ruleset_json() {
  local name="$1"
  local target="$2"
  local ids count id
  ids="$(gh api --paginate "repos/${GITHUB_REPOSITORY}/rulesets?per_page=100" --jq ".[] | select(
    .name == \"${name}\" and .target == \"${target}\" and .enforcement == \"active\"
  ) | .id")"
  count=0
  id=''
  while IFS= read -r candidate; do
    if [[ -n "${candidate}" ]]; then
      count=$((count + 1))
      id="${candidate}"
    fi
  done <<< "${ids}"
  if [[ "${count}" -ne 1 ]]; then
    echo "Exactly one active ${name} ${target} ruleset is required." >&2
    return 1
  fi
  gh api "repos/${GITHUB_REPOSITORY}/rulesets/${id}"
}

TAG_RULESET="$(ruleset_json 'Immutable release tags' 'tag')"
if [[ "$(jq '
  has("bypass_actors") and
  (.conditions.ref_name.include == ["refs/tags/v*"]) and
  (.conditions.ref_name.exclude == []) and
  ([.rules[].type] | sort == ["deletion", "update"]) and
  (.bypass_actors == [])
' <<< "${TAG_RULESET}")" != 'true' ]]; then
  echo 'Immutable release tags must target only refs/tags/v*, protect update/deletion, permit creation, and have no bypass actors.' >&2
  exit 1
fi

KIRO_RULESET="$(ruleset_json 'Kiro marketplace release' 'branch')"
if [[ "$(jq --argjson release_app_id "${RELEASE_APP_ID}" '
  has("bypass_actors") and
  (.conditions.ref_name.include == ["refs/heads/marketplace-kiro"]) and
  (.conditions.ref_name.exclude == []) and
  ([.rules[].type] | sort == ["creation", "deletion", "non_fast_forward", "update"]) and
  (.bypass_actors == [{"actor_id":$release_app_id,"actor_type":"Integration","bypass_mode":"always"}])
' <<< "${KIRO_RULESET}")" != 'true' ]]; then
  echo 'Kiro marketplace release must protect creation/update/deletion/force-push, target only refs/heads/marketplace-kiro, and grant its sole always-bypass to qodo-skills-release-bot.' >&2
  exit 1
fi

printf 'Release protections verified: repository=%s app_id=%s tag_ruleset=%s kiro_ruleset=%s\n' \
  "${GITHUB_REPOSITORY}" \
  "${RELEASE_APP_ID}" \
  "$(jq -r '.id' <<< "${TAG_RULESET}")" \
  "$(jq -r '.id' <<< "${KIRO_RULESET}")"

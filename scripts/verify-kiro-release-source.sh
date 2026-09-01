#!/usr/bin/env bash
# Fail closed before creating or advancing Kiro's provider-visible release branch.
# The administrator-only bypass audit is scripts/audit-release-protections.sh.
# Usage: GH_TOKEN=<app-installation-token> QODO_SKILLS_RELEASE_APP_ID=<id> GITHUB_REPOSITORY=<owner/repo> scripts/verify-kiro-release-source.sh
set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  echo "Kiro release-source preflight requires 'gh', but it is not available." >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "Kiro release-source preflight requires 'jq', but it is not available." >&2
  exit 1
}
if [[ -z "${GH_TOKEN:-}" ]]; then
  echo 'The short-lived qodo-skills release App token is required.' >&2
  exit 1
fi

RELEASE_APP_ID="${QODO_SKILLS_RELEASE_APP_ID:-}"
if [[ ! "${RELEASE_APP_ID}" =~ ^[0-9]+$ ]]; then
  echo 'QODO_SKILLS_RELEASE_APP_ID must be the dedicated GitHub App numeric id.' >&2
  exit 1
fi

APP_JSON="$(gh api /apps/qodo-skills-release-bot)"
if [[ "$(jq --argjson release_app_id "${RELEASE_APP_ID}" '
  (.id == $release_app_id) and
  (.slug == "qodo-skills-release-bot") and
  (.permissions == {"contents":"write","metadata":"read"})
' <<< "${APP_JSON}")" != 'true' ]]; then
  echo 'The configured release App must be qodo-skills-release-bot with only Contents:write and Metadata:read.' >&2
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

RULESET_JSON="$(gh api "repos/${GITHUB_REPOSITORY}/rulesets/${RULESET_ID}")"
if [[ "$(jq --argjson release_app_id "${RELEASE_APP_ID}" '
  (.conditions.ref_name.include == ["refs/heads/marketplace-kiro"]) and
  (.conditions.ref_name.exclude | type == "array" and length == 0) and
  ([.rules[].type] | sort == ["creation", "deletion", "non_fast_forward", "update"]) and
  ((has("bypass_actors") | not) or (
    (.bypass_actors | type == "array" and length == 1) and
    (.bypass_actors[0].bypass_mode == "always") and
    (.bypass_actors[0].actor_type == "Integration") and
    (.bypass_actors[0].actor_id == $release_app_id)
  ))
' <<< "${RULESET_JSON}")" != 'true' ]]; then
  echo 'Kiro marketplace release ruleset must protect creation/update/deletion/force-push only, cover only refs/heads/marketplace-kiro, and expose only the dedicated Integration bypass when visible.' >&2
  exit 1
fi

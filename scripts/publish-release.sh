#!/usr/bin/env bash
# Create or resume a verified draft, then publish and re-verify immutable bytes.
# Usage: GH_TOKEN=<contents-write-token> GITHUB_REPOSITORY=owner/repo GITHUB_SHA=<sha> RUNNER_TEMP=<dir> scripts/publish-release.sh
set -euo pipefail

for tool in gh git node mktemp sha256sum cmp grep cat rm; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Release publication requires '${tool}', but it is not available." >&2
    exit 1
  }
done

VERSION="$(node -p "require('./distribution/catalog.json').package.version")"
TAG="v${VERSION}"
NOTES="${RUNNER_TEMP}/qodo-release-notes.md"
node scripts/release-notes.mjs "${NOTES}"

git fetch origin main --no-tags
if [[ "$(git rev-parse origin/main)" != "${GITHUB_SHA}" ]]; then
  echo 'Refusing to publish: main advanced while this release was being validated.' >&2
  exit 1
fi

RELEASE_EXISTS=false
RELEASE_LOOKUP="$(mktemp "${RUNNER_TEMP}/qodo-release-lookup.XXXXXX")"
if gh api --include "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" >"${RELEASE_LOOKUP}" 2>&1; then
  RELEASE_EXISTS=true
elif ! grep -Eq '^HTTP/[0-9.]+ 404([[:space:]]|$)' "${RELEASE_LOOKUP}"; then
  cat "${RELEASE_LOOKUP}" >&2
  rm -f -- "${RELEASE_LOOKUP}"
  echo "Could not determine whether ${TAG} already exists; refusing to create a release." >&2
  exit 1
fi
rm -f -- "${RELEASE_LOOKUP}"
if [[ "${RELEASE_EXISTS}" == 'true' ]]; then
  git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" --force
  test "$(git rev-list -n 1 "${TAG}")" = "${GITHUB_SHA}"
  if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.draft')" != 'true' ]]; then
    test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.immutable')" = 'true'
    test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
      'qodo-skills-index.json qodo-skills-index.json.sha256'
    VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-release-verify.XXXXXX")"
    trap 'rm -rf -- "${VERIFY_DIR}"' EXIT
    gh release download "${TAG}" --dir "${VERIFY_DIR}" --pattern 'qodo-skills-index.json*'
    (
      cd "${VERIFY_DIR}"
      sha256sum --check qodo-skills-index.json.sha256
    )
    cmp --silent "${VERIFY_DIR}/qodo-skills-index.json" distribution/qodo-skills-index.json
    cmp --silent "${VERIFY_DIR}/qodo-skills-index.json.sha256" distribution/qodo-skills-index.json.sha256
    exit 0
  fi
fi

if git rev-parse --verify --quiet "refs/tags/${TAG}" >/dev/null; then
  if [[ "$(git rev-list -n 1 "${TAG}")" != "${GITHUB_SHA}" ]]; then
    echo "${TAG} already points to a different commit; refusing to publish." >&2
    exit 1
  fi
else
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git tag --no-sign -a "${TAG}" "${GITHUB_SHA}" -m "Qodo skills ${TAG}"
fi

git push origin "refs/tags/${TAG}:refs/tags/${TAG}"

if [[ "${RELEASE_EXISTS}" == 'true' ]]; then
  gh release upload "${TAG}" --clobber \
    distribution/qodo-skills-index.json \
    distribution/qodo-skills-index.json.sha256
else
  gh release create "${TAG}" --draft --verify-tag --title "Qodo skills ${TAG}" --notes-file "${NOTES}" \
    distribution/qodo-skills-index.json \
    distribution/qodo-skills-index.json.sha256
fi

test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.draft')" = 'true'
test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
  'qodo-skills-index.json qodo-skills-index.json.sha256'
VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-release-verify.XXXXXX")"
trap 'rm -rf -- "${VERIFY_DIR}"' EXIT
gh release download "${TAG}" --dir "${VERIFY_DIR}" --pattern 'qodo-skills-index.json*'
(
  cd "${VERIFY_DIR}"
  sha256sum --check qodo-skills-index.json.sha256
)
cmp --silent "${VERIFY_DIR}/qodo-skills-index.json" distribution/qodo-skills-index.json
cmp --silent "${VERIFY_DIR}/qodo-skills-index.json.sha256" distribution/qodo-skills-index.json.sha256

git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" --force
if [[ "$(git rev-list -n 1 "${TAG}")" != "${GITHUB_SHA}" ]]; then
  echo "Remote ${TAG} no longer resolves to the validated release commit." >&2
  exit 1
fi
gh release edit "${TAG}" --draft=false
if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.immutable')" != 'true' ]]; then
  echo 'Published release is mutable. Enable repository release immutability before any consumer rollout.' >&2
  exit 1
fi
test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
  'qodo-skills-index.json qodo-skills-index.json.sha256'
git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" --force
test "$(git rev-list -n 1 "${TAG}")" = "${GITHUB_SHA}"
PUBLISHED_VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-published-release-verify.XXXXXX")"
trap 'rm -rf -- "${VERIFY_DIR:-}" "${PUBLISHED_VERIFY_DIR:-}"' EXIT
gh release download "${TAG}" --dir "${PUBLISHED_VERIFY_DIR}" --pattern 'qodo-skills-index.json*'
(
  cd "${PUBLISHED_VERIFY_DIR}"
  sha256sum --check qodo-skills-index.json.sha256
)
cmp --silent "${PUBLISHED_VERIFY_DIR}/qodo-skills-index.json" distribution/qodo-skills-index.json
cmp --silent "${PUBLISHED_VERIFY_DIR}/qodo-skills-index.json.sha256" distribution/qodo-skills-index.json.sha256

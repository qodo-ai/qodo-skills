#!/usr/bin/env bash
# Create or resume a verified draft, then publish and re-verify immutable bytes.
# Usage: GH_TOKEN=<contents-write-token> GITHUB_REPOSITORY=owner/repo GITHUB_SHA=<sha> \
#   RUNNER_TEMP=<dir> QODO_ENTERPRISE_RELEASE_DIR=<prepared-assets-dir> scripts/publish-release.sh
set -euo pipefail

for tool in gh git node mktemp cmp grep cat rm basename; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Release publication requires '${tool}', but it is not available." >&2
    exit 1
  }
done

if command -v sha256sum >/dev/null 2>&1; then
  verify_sha256() { sha256sum --check "$1"; }
elif command -v shasum >/dev/null 2>&1; then
  verify_sha256() { shasum -a 256 --check "$1"; }
else
  echo "Release publication requires 'sha256sum' or 'shasum', but neither is available." >&2
  exit 1
fi

VERSION="$(node -p "require('./distribution/catalog.json').package.version")"
TAG="v${VERSION}"
NOTES="${RUNNER_TEMP}/qodo-release-notes.md"
ENTERPRISE_DIR="${QODO_ENTERPRISE_RELEASE_DIR:?QODO_ENTERPRISE_RELEASE_DIR is required}"
ARCHIVE_NAME="qodo-enterprise-bundle-v${VERSION}.tar.gz"
RELEASE_ASSETS=(
  "${ENTERPRISE_DIR}/${ARCHIVE_NAME}"
  "${ENTERPRISE_DIR}/${ARCHIVE_NAME}.sha256"
  "${ENTERPRISE_DIR}/qodo-enterprise-manifest.json"
  "${ENTERPRISE_DIR}/qodo-enterprise-manifest.json.sha256"
  distribution/qodo-skills-index.json
  distribution/qodo-skills-index.json.sha256
)
EXPECTED_ASSETS="$(node -e \
  'console.log(process.argv.slice(1).map((asset) => require("node:path").basename(asset)).sort().join(" "))' \
  "${RELEASE_ASSETS[@]}")"
node scripts/release-notes.mjs "${NOTES}"

for asset in "${RELEASE_ASSETS[@]}"; do
  test -f "${asset}" || { echo "Release asset is missing: ${asset}" >&2; exit 1; }
done

verify_release_assets() {
  local directory="$1"
  (
    cd "${directory}"
    verify_sha256 qodo-skills-index.json.sha256
    verify_sha256 "${ARCHIVE_NAME}.sha256"
    verify_sha256 qodo-enterprise-manifest.json.sha256
  )
  cmp --silent "${directory}/qodo-skills-index.json" distribution/qodo-skills-index.json
  cmp --silent "${directory}/qodo-skills-index.json.sha256" distribution/qodo-skills-index.json.sha256
  cmp --silent "${directory}/${ARCHIVE_NAME}" "${ENTERPRISE_DIR}/${ARCHIVE_NAME}"
  cmp --silent "${directory}/${ARCHIVE_NAME}.sha256" "${ENTERPRISE_DIR}/${ARCHIVE_NAME}.sha256"
  cmp --silent "${directory}/qodo-enterprise-manifest.json" "${ENTERPRISE_DIR}/qodo-enterprise-manifest.json"
  cmp --silent "${directory}/qodo-enterprise-manifest.json.sha256" "${ENTERPRISE_DIR}/qodo-enterprise-manifest.json.sha256"
}

require_current_main() {
  git fetch origin main --no-tags
  if [[ "$(git rev-parse origin/main)" != "${GITHUB_SHA}" ]]; then
    echo 'Refusing to publish: main advanced while this release was being validated.' >&2
    exit 1
  fi
}

require_annotated_release_tag() {
  if [[ "$(git cat-file -t "refs/tags/${TAG}" 2>/dev/null)" != 'tag' ]]; then
    echo "${TAG} is not an annotated tag; refusing to publish." >&2
    exit 1
  fi
  if [[ "$(git rev-parse "refs/tags/${TAG}^{}")" != "${GITHUB_SHA}" ]]; then
    echo "${TAG} does not resolve to the validated release commit; refusing to publish." >&2
    exit 1
  fi
}

require_current_main

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
  require_annotated_release_tag
  if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.draft')" != 'true' ]]; then
    if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.immutable')" != 'true' ]]; then
      echo "Existing public release ${TAG} is mutable; refusing to overwrite its assets." >&2
      exit 1
    fi
    test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
      "${EXPECTED_ASSETS}"
    VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-release-verify.XXXXXX")"
    trap 'rm -rf -- "${VERIFY_DIR}"' EXIT
    gh release download "${TAG}" --dir "${VERIFY_DIR}" --pattern 'qodo-*'
    verify_release_assets "${VERIFY_DIR}"
    exit 0
  fi
fi

if git rev-parse --verify --quiet "refs/tags/${TAG}" >/dev/null; then
  require_annotated_release_tag
else
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git tag --no-sign -a "${TAG}" "${GITHUB_SHA}" -m "Qodo skills ${TAG}"
fi
require_annotated_release_tag

# Minimize the freshness window after draft discovery. Release integrity does
# not depend on main staying still: the tag and every asset remain bound to the
# exact commit this job checked out and validated.
require_current_main
git push origin "refs/tags/${TAG}:refs/tags/${TAG}"

if [[ "${RELEASE_EXISTS}" == 'true' ]]; then
  if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.draft')" != 'true' ]]; then
    echo "Existing release ${TAG} left draft state before asset verification; refusing to mutate it." >&2
    exit 1
  fi
  EXISTING_ASSETS=()
  while IFS= read -r existing_asset; do
    [[ -n "${existing_asset}" ]] && EXISTING_ASSETS+=("${existing_asset}")
  done < <(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.assets[].name')
  for existing_asset in "${EXISTING_ASSETS[@]}"; do
    expected=false
    for release_asset in "${RELEASE_ASSETS[@]}"; do
      if [[ "$(basename "${release_asset}")" == "${existing_asset}" ]]; then
        expected=true
        break
      fi
    done
    if [[ "${expected}" == 'false' ]]; then
      echo "Existing draft ${TAG} has an unexpected asset inventory; refusing to replace anything." >&2
      exit 1
    fi
  done
  for release_asset in "${RELEASE_ASSETS[@]}"; do
    asset_name="$(basename "${release_asset}")"
    present=false
    for existing_asset in "${EXISTING_ASSETS[@]}"; do
      if [[ "${asset_name}" == "${existing_asset}" ]]; then
        present=true
        break
      fi
    done
    if [[ "${present}" == 'false' ]]; then
      gh release upload "${TAG}" "${release_asset}"
    fi
  done
else
  gh release create "${TAG}" --draft --verify-tag --title "Qodo skills ${TAG}" --notes-file "${NOTES}" \
    "${RELEASE_ASSETS[@]}"
fi

test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.draft')" = 'true'
test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
  "${EXPECTED_ASSETS}"
VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-release-verify.XXXXXX")"
trap 'rm -rf -- "${VERIFY_DIR}"' EXIT
gh release download "${TAG}" --dir "${VERIFY_DIR}" --pattern 'qodo-*'
verify_release_assets "${VERIFY_DIR}"

git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" --force
require_annotated_release_tag
gh release edit "${TAG}" --draft=false
if [[ "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '.immutable')" != 'true' ]]; then
  echo 'Published release is mutable. Enable repository release immutability before any consumer rollout.' >&2
  if ! gh release edit "${TAG}" --draft=true; then
    echo 'CRITICAL: could not return the mutable release to draft; stop all consumer rollout.' >&2
  fi
  exit 1
fi
test "$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${TAG}" --jq '[.assets[].name] | sort | join(" ")')" = \
  "${EXPECTED_ASSETS}"
git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" --force
require_annotated_release_tag
PUBLISHED_VERIFY_DIR="$(mktemp -d "${RUNNER_TEMP}/qodo-published-release-verify.XXXXXX")"
trap 'rm -rf -- "${VERIFY_DIR:-}" "${PUBLISHED_VERIFY_DIR:-}"' EXIT
gh release download "${TAG}" --dir "${PUBLISHED_VERIFY_DIR}" --pattern 'qodo-*'
verify_release_assets "${PUBLISHED_VERIFY_DIR}"

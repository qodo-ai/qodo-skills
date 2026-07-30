#!/bin/sh
# Regression test for repository scope detection (Step 2 of SKILL.md).
#
# Guards the bug where `sed 's|^https\?://[^/]*/||'` silently no-opped on BSD sed
# (macOS): `\?` is a GNU BRE extension, so the substitution matched nothing, exited 0,
# and the entire remote URL became the scope path — halving retrieval quality with no
# error. Run this on macOS *and* Linux; POSIX sh only, no frameworks.
#
# Usage: sh skills/qodo-get-rules/tests/scope-parse.sh

set -eu

DOC_DIR=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
failures=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

# --- the parse under test: must stay in sync with SKILL.md Step 2 -------------
# Mirrors the snippet in SKILL.md / references/repository-scope.md. check_no_gnuisms
# below fails if either doc drifts back to sed/grep, which is the failure mode that
# actually bit us.
parse_repo_path() {
  REPO_PATH="${1%/}"
  REPO_PATH="${REPO_PATH%.git}"

  case "$REPO_PATH" in
    file://*)
      REPO_PATH=""
      ;;
    *://*)
      REPO_PATH="${REPO_PATH#*://}"
      REPO_PATH="${REPO_PATH#*/}"
      ;;
    *:*/*)
      REPO_PATH="${REPO_PATH#*:}"
      ;;
    *)
      REPO_PATH=""
      ;;
  esac

  case "$REPO_PATH" in
    /*|*\\*) REPO_PATH="" ;;
    */*)     ;;
    *)       REPO_PATH="" ;;
  esac

  printf '%s' "$REPO_PATH"
}

parse_module() {
  MODULE=""
  case "$1" in
    modules/*/*)
      MODULE="${1#modules/}"
      MODULE="${MODULE%%/*}"
      ;;
  esac
  printf '%s' "$MODULE"
}

expect_path() {
  got=$(parse_repo_path "$1")
  [ "$got" = "$2" ] || fail "remote '$1' -> '$got', expected '$2'"
}

expect_module() {
  got=$(parse_module "$1")
  [ "$got" = "$2" ] || fail "prefix '$1' -> module '$got', expected '$2'"
}

# --- remote URL formats -------------------------------------------------------
expect_path 'https://github.com/qodo-se/acme-billing-service' 'qodo-se/acme-billing-service'
expect_path 'https://github.com/org/repo.git'                 'org/repo'
expect_path 'http://git.internal/org/repo'                    'org/repo'
expect_path 'git@github.com:org/repo.git'                     'org/repo'
expect_path 'git@github.com:org/repo'                         'org/repo'
expect_path 'ssh://git@github.com/org/repo.git'               'org/repo'
expect_path 'git://host/org/repo'                             'org/repo'
expect_path 'https://user:token@github.com/org/repo.git'      'org/repo'
expect_path 'https://github.com/org/repo/'                    'org/repo'
# .git AND a trailing slash together — strip order matters here
expect_path 'https://github.com/org/repo.git/'                'org/repo'
expect_path 'git@github.com:org/repo.git/'                    'org/repo'
expect_path 'https://gitlab.com/group/subgroup/repo.git/'     'group/subgroup/repo'

# deeper paths must survive — do not collapse to two segments
expect_path 'https://gitlab.com/group/subgroup/repo.git'      'group/subgroup/repo'
expect_path 'https://dev.azure.com/org/proj/_git/repo'        'org/proj/_git/repo'
expect_path 'git@ssh.dev.azure.com:v3/org/proj/repo'          'v3/org/proj/repo'

# --- must degrade to no scope rather than emit a nonsense one -----------------
expect_path 'https://github.com/onlyorg' ''
expect_path '/Users/me/local-repo'       ''
# a local clone has no hosted org/repo path, in any spelling
expect_path 'file:///Users/me/local-repo'    ''
expect_path 'file://localhost/Users/me/repo' ''
expect_path 'file:///c/repos/foo'            ''
expect_path 'C:\repos\foo'               ''
expect_path 'C:/repos/foo'               ''
expect_path ''                           ''

# --- module narrowing (git rev-parse --show-prefix output) --------------------
expect_module ''                     ''
expect_module 'modules/'             ''
expect_module 'modules/billing/'     'billing'
expect_module 'modules/billing/src/' 'billing'
expect_module 'modulesfoo/bar/'      ''
expect_module 'src/'                 ''

# --- the docs must not reintroduce the non-portable constructs ----------------
# These skills are prose an agent executes, so the shell to guard lives in the
# fenced code blocks. Prose *about* the bad constructs (the Portability section)
# is fine and must not trip this.
check_no_gnuisms() {
  doc="$DOC_DIR/$1"
  [ -f "$doc" ] || { fail "missing doc: $doc"; return; }

  code=$(awk '/^```/ { inblock = !inblock; next } inblock' "$doc")

  # GNU BRE extensions: silently no-op on BSD sed instead of erroring.
  # \( \) \1 are valid BRE and stay allowed; only \? \+ \| are GNU-only.
  # `sed -E` opts into ERE, where ? + | are bare and portable, so skip those lines.
  if printf '%s\n' "$code" | grep 'sed ' | grep -v 'sed -[A-Za-z]*E' \
       | grep -q '\\[?+|]'; then
    fail "$1 uses GNU-only BRE (\\? \\+ \\|) in sed — use sed -E, or no sed at all"
  fi
  # GNU coreutils only; BSD realpath rejects it
  if printf '%s\n' "$code" | grep -q 'realpath --relative-to'; then
    fail "$1 uses realpath --relative-to (GNU only) — use git rev-parse --show-prefix"
  fi
}

check_no_gnuisms 'SKILL.md'
check_no_gnuisms 'references/repository-scope.md'

# --- end-to-end against a real repo, so the parse is exercised as written -----
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
mkdir -p "$tmp/modules/billing/src"
(
  cd "$tmp"
  git init -q
  git remote add origin 'https://github.com/qodo-se/acme-billing-service.git'
)

# NB: not named `path` — in zsh that is tied to $PATH and assigning to it
# would wipe the command search path.
live_scope() (
  cd "$1"
  repo_path=$(parse_repo_path "$(git remote get-url origin 2>/dev/null)")
  [ -n "$repo_path" ] || return 0
  module=$(parse_module "$(git rev-parse --show-prefix)")
  if [ -n "$module" ]; then
    printf '/%s/modules/%s/' "$repo_path" "$module"
  else
    printf '/%s/' "$repo_path"
  fi
)

got=$(live_scope "$tmp")
[ "$got" = '/qodo-se/acme-billing-service/' ] \
  || fail "repo-root scope -> '$got', expected '/qodo-se/acme-billing-service/'"

got=$(live_scope "$tmp/modules/billing/src")
[ "$got" = '/qodo-se/acme-billing-service/modules/billing/' ] \
  || fail "module scope -> '$got', expected '/qodo-se/acme-billing-service/modules/billing/'"

# ------------------------------------------------------------------------------
if [ "$failures" -ne 0 ]; then
  printf '\n%s check(s) failed\n' "$failures" >&2
  exit 1
fi

printf 'ok — scope parsing portable on %s\n' "$(uname -s)"

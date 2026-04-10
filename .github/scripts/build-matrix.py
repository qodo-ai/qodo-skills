#!/usr/bin/env python3
"""
build-matrix.py -- Build GitHub Actions test matrix for qodo-skills CI

Two modes:

  PR mode (detect changed skills from a changed-files list):
    python3 build-matrix.py pr "skills/qodo-get-rules/SKILL.md skills/qodo-pr-resolver/support.yml"

  On-demand mode (test a specific skill):
    python3 build-matrix.py skill qodo-get-rules
    python3 build-matrix.py skill qodo-get-rules --os ubuntu
    python3 build-matrix.py skill qodo-get-rules --os all

Output is written to $GITHUB_OUTPUT in the format expected by GitHub Actions:
  matrix={"include": [{"skill": "...", "os": "..."}, ...]}
  has_matrix=true|false

When $GITHUB_OUTPUT is not set (local dev), output is printed to stdout.
"""

import sys
import json
import pathlib
import os

# Maps declared OS names (in support.yml) to GitHub Actions runner labels
OS_TO_RUNNER = {
    "ubuntu": "ubuntu-latest",
    "macos": "macos-latest",
    "windows": "windows-latest",
}


# ---------------------------------------------------------------------------
# Minimal YAML parser -- duplicated from validate-skill.py to keep scripts
# self-contained with zero dependencies.
# ---------------------------------------------------------------------------

def parse_simple_yaml(text):
    result = {}
    current_list_key = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is not None:
                result[current_list_key].append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" in stripped:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest == "[]":
                result[key] = []
                current_list_key = None
            elif rest == "":
                result[key] = []
                current_list_key = key
            else:
                result[key] = rest.strip("\"'")
                current_list_key = None

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_support_yml(skill_dir):
    """Parse support.yml for a skill directory. Returns None if not found."""
    support_file = pathlib.Path(skill_dir) / "support.yml"
    if not support_file.exists():
        return None
    return parse_simple_yaml(support_file.read_text(encoding="utf-8"))


def runners_for_skill(skill_name, requested_os="all"):
    """Return a list of GitHub Actions runner labels for the given skill.

    Uses declared os list from support.yml when available.
    Falls back to all three runners if support.yml is missing.
    """
    skill_dir = pathlib.Path("skills") / skill_name
    support = read_support_yml(skill_dir)

    if support and isinstance(support.get("os"), list) and support["os"]:
        declared_os = support["os"]
    else:
        # Missing or invalid support.yml -- run on all OSes so the validator
        # can report the missing file on each platform.
        declared_os = list(OS_TO_RUNNER.keys())

    if requested_os != "all":
        # Honor explicit override even if not in declared list
        if requested_os in OS_TO_RUNNER:
            return [OS_TO_RUNNER[requested_os]]
        else:
            print(f"Warning: unknown OS '{requested_os}', using all", file=sys.stderr)
            return list(OS_TO_RUNNER.values())

    return [OS_TO_RUNNER[o] for o in declared_os if o in OS_TO_RUNNER]


def extract_skills_from_changed_files(changed_files_str):
    """Extract unique skill names from a space-separated list of changed paths.

    e.g. "skills/qodo-get-rules/SKILL.md skills/qodo-get-rules/support.yml"
    yields {"qodo-get-rules"}
    """
    skills = set()
    for path_str in changed_files_str.split():
        parts = pathlib.PurePosixPath(path_str).parts
        if len(parts) >= 2 and parts[0] == "skills":
            skills.add(parts[1])
    return sorted(skills)


# ---------------------------------------------------------------------------
# Matrix builders
# ---------------------------------------------------------------------------

def build_pr_matrix(changed_files_str):
    """Build include matrix from changed files detected in a PR."""
    skills = extract_skills_from_changed_files(changed_files_str)
    includes = []
    for skill in skills:
        for runner in runners_for_skill(skill):
            includes.append({"skill": skill, "os": runner})
    return includes


def build_skill_matrix(skill_name, requested_os="all"):
    """Build include matrix for a single named skill."""
    includes = []
    for runner in runners_for_skill(skill_name, requested_os):
        includes.append({"skill": skill_name, "os": runner})
    return includes


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_output(includes):
    """Write matrix and has_matrix to $GITHUB_OUTPUT or stdout."""
    matrix_json = json.dumps({"include": includes})
    has_matrix = "true" if includes else "false"

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"matrix={matrix_json}\n")
            fh.write(f"has_matrix={has_matrix}\n")
    else:
        # Local development -- print to stdout
        print(f"matrix={matrix_json}")
        print(f"has_matrix={has_matrix}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        _usage()

    mode = sys.argv[1]

    if mode == "pr":
        changed_files = sys.argv[2] if len(sys.argv) > 2 else ""
        includes = build_pr_matrix(changed_files)

    elif mode == "skill":
        if len(sys.argv) < 3:
            print("Error: 'skill' mode requires a skill name", file=sys.stderr)
            _usage()
        skill_name = sys.argv[2]
        requested_os = "all"
        if "--os" in sys.argv:
            idx = sys.argv.index("--os")
            if idx + 1 < len(sys.argv):
                requested_os = sys.argv[idx + 1]
        includes = build_skill_matrix(skill_name, requested_os)

    else:
        print(f"Error: unknown mode '{mode}'", file=sys.stderr)
        _usage()

    write_output(includes)


def _usage():
    prog = pathlib.Path(sys.argv[0]).name
    print(f"Usage:", file=sys.stderr)
    print(f"  {prog} pr \"<space-separated changed file paths>\"", file=sys.stderr)
    print(f"  {prog} skill <skill-name> [--os all|ubuntu|macos|windows]", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

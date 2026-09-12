#!/usr/bin/env python3
"""
validate-skill.py -- Structural validator for qodo-skills

Verifies that a skill directory meets all requirements:
  - support.yml exists and is schema-valid
  - SKILL.md exists with valid frontmatter
  - Names match across support.yml, SKILL.md frontmatter, and directory name
  - All markdown files are within the 500-line size limit
  - All relative links in SKILL.md resolve to existing files
  - Declared agent/OS/git_provider values use the known controlled vocabulary
  - Python scripts (if any) have valid syntax

Usage:
  python3 validate-skill.py <skill-dir>
  python3 validate-skill.py skills/qodo-get-rules

Exit code: 0 on success, 1 on failure, 2 on usage error
"""

import sys
import re
import pathlib
import subprocess

# Controlled vocabulary -- must stay in sync with SKILL_SUPPORT.md
KNOWN_AGENTS = {"claude-code", "cursor", "windsurf", "cline", "copilot", "codex"}
KNOWN_OS = {"ubuntu", "macos", "windows"}
KNOWN_GIT_PROVIDERS = {"github", "gitlab", "bitbucket", "azure-devops"}

MAX_FILE_LINES = 500


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib only -- no PyYAML dependency)
# Handles the simple YAML subset used in support.yml and SKILL.md frontmatter:
#   scalar fields:  key: value
#   empty lists:    key: []
#   block lists:    key:\n  - item
# ---------------------------------------------------------------------------

def parse_simple_yaml(text):
    """Parse a simple YAML subset. Returns a dict of scalars and lists."""
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


def parse_frontmatter(text):
    """Extract and parse YAML frontmatter between --- delimiters.

    Returns (dict, None) on success, (None, error_string) on failure.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "no opening '---' delimiter found"

    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, "no closing '---' delimiter found"

    fm_text = "\n".join(lines[1:end_idx])
    return parse_simple_yaml(fm_text), None


def extract_relative_links(text):
    """Return relative file paths from Markdown links, excluding http(s) and anchor links."""
    links = re.findall(r"\[([^\]]+)\]\(([^)#]+)\)", text)
    return [
        target.strip()
        for _, target in links
        if not target.startswith("http://")
        and not target.startswith("https://")
        and not target.startswith("#")
        and not target.startswith("mailto:")
        and target.strip()
    ]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class Validator:
    def __init__(self, skill_dir):
        self.skill_dir = pathlib.Path(skill_dir)
        self.skill_name = self.skill_dir.name
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, label, condition, error_msg):
        if condition:
            print(f"  [PASS] {label}")
            self.passed += 1
            return True
        else:
            print(f"  [FAIL] {label}")
            print(f"         {error_msg}")
            self.failed += 1
            self.errors.append(f"{label}: {error_msg}")
            return False

    def info(self, msg):
        print(f"  [INFO] {msg}")

    # --- individual check groups ---

    def check_skill_dir(self):
        return self.check(
            "Skill directory exists",
            self.skill_dir.is_dir(),
            f"Directory not found: {self.skill_dir}",
        )

    def check_support_yml(self):
        support_file = self.skill_dir / "support.yml"

        exists = self.check(
            "support.yml exists",
            support_file.exists(),
            (
                "Missing support.yml -- create this file to declare supported environments.\n"
                "         See SKILL_SUPPORT.md for the format."
            ),
        )
        if not exists:
            return None

        content = support_file.read_text(encoding="utf-8")
        data = parse_simple_yaml(content)

        self.check(
            "support.yml: schema_version present",
            "schema_version" in data,
            "Missing required field: schema_version",
        )
        self.check(
            "support.yml: skill field present",
            "skill" in data,
            "Missing required field: skill",
        )
        has_agents = self.check(
            "support.yml: agents field present",
            "agents" in data,
            "Missing required field: agents",
        )
        has_os = self.check(
            "support.yml: os field present",
            "os" in data,
            "Missing required field: os",
        )

        if "skill" in data:
            self.check(
                f"support.yml: skill name matches directory ('{data['skill']}')",
                data["skill"] == self.skill_name,
                f"skill: '{data['skill']}' does not match directory name '{self.skill_name}'",
            )

        if has_agents and isinstance(data.get("agents"), list):
            agents = data["agents"]
            invalid = [a for a in agents if a not in KNOWN_AGENTS]
            self.check(
                f"support.yml: agents use known vocabulary ({', '.join(agents) or 'none'})",
                not invalid,
                f"Unknown agent(s): {', '.join(invalid)}. Known: {', '.join(sorted(KNOWN_AGENTS))}",
            )
            self.check(
                "support.yml: agents list is not empty",
                len(agents) > 0,
                "agents must declare at least one supported agent",
            )

        if has_os and isinstance(data.get("os"), list):
            os_list = data["os"]
            invalid = [o for o in os_list if o not in KNOWN_OS]
            self.check(
                f"support.yml: os uses known vocabulary ({', '.join(os_list) or 'none'})",
                not invalid,
                f"Unknown OS(es): {', '.join(invalid)}. Known: {', '.join(sorted(KNOWN_OS))}",
            )
            self.check(
                "support.yml: os list is not empty",
                len(os_list) > 0,
                "os must declare at least one supported OS",
            )

        git_providers = data.get("git_providers")
        if git_providers is None:
            self.info("git_providers: not declared (no git provider dependency assumed)")
        elif isinstance(git_providers, list) and git_providers:
            invalid = [gp for gp in git_providers if gp not in KNOWN_GIT_PROVIDERS]
            self.check(
                f"support.yml: git_providers use known vocabulary ({', '.join(git_providers)})",
                not invalid,
                f"Unknown provider(s): {', '.join(invalid)}. Known: {', '.join(sorted(KNOWN_GIT_PROVIDERS))}",
            )
        else:
            self.info("git_providers: [] (no git provider CLI dependency)")

        return data

    def check_skill_md(self):
        skill_md = self.skill_dir / "SKILL.md"
        exists = self.check(
            "SKILL.md exists",
            skill_md.exists(),
            "Missing SKILL.md -- every skill requires a SKILL.md file",
        )
        if not exists:
            return

        content = skill_md.read_text(encoding="utf-8")
        lines = content.splitlines()
        self.check(
            f"SKILL.md within {MAX_FILE_LINES}-line limit ({len(lines)} lines)",
            len(lines) <= MAX_FILE_LINES,
            f"SKILL.md has {len(lines)} lines (max {MAX_FILE_LINES}). Extract sections to references/",
        )

        fm, fm_err = parse_frontmatter(content)
        fm_ok = self.check(
            "SKILL.md: valid YAML frontmatter",
            fm is not None,
            f"Frontmatter parse error: {fm_err}",
        )

        if fm_ok:
            self.check(
                "SKILL.md frontmatter: 'name' field present",
                "name" in fm,
                "Missing required frontmatter field: name",
            )
            self.check(
                "SKILL.md frontmatter: 'description' field present",
                "description" in fm,
                "Missing required frontmatter field: description",
            )
            if "name" in fm:
                self.check(
                    f"SKILL.md frontmatter: name matches directory ('{fm['name']}')",
                    fm["name"] == self.skill_name,
                    f"frontmatter name: '{fm['name']}' does not match directory '{self.skill_name}'",
                )

        # Check relative links
        links = extract_relative_links(content)
        if links:
            broken = [lnk for lnk in links if not (self.skill_dir / lnk).exists()]
            self.check(
                f"SKILL.md: all relative links resolve ({len(links)} checked)",
                not broken,
                f"Broken link(s): {', '.join(broken)}",
            )
        else:
            self.info("SKILL.md: no relative links to check")

    def check_file_sizes(self):
        md_files = [
            f for f in self.skill_dir.rglob("*.md") if f.name != "SKILL.md"
        ]
        if not md_files:
            return

        oversized = []
        for md_file in md_files:
            try:
                lines = md_file.read_text(encoding="utf-8").splitlines()
                if len(lines) > MAX_FILE_LINES:
                    rel = md_file.relative_to(self.skill_dir)
                    oversized.append(f"{rel} ({len(lines)} lines)")
            except Exception:
                pass

        self.check(
            f"Reference/resource files within {MAX_FILE_LINES}-line limit ({len(md_files)} checked)",
            not oversized,
            f"Oversized: {', '.join(oversized)}",
        )

    def check_python_syntax(self):
        scripts_dir = self.skill_dir / "scripts"
        if not scripts_dir.is_dir():
            return

        py_scripts = list(scripts_dir.glob("*.py"))
        if not py_scripts:
            return

        failed = []
        for script in py_scripts:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script)],
                capture_output=True,
            )
            if result.returncode != 0:
                failed.append(script.name)

        self.check(
            f"Python scripts valid syntax ({len(py_scripts)} checked)",
            not failed,
            f"Syntax errors in: {', '.join(failed)}",
        )

    # --- main entry point ---

    def run(self):
        print(f"\nValidating skill: {self.skill_name}")
        print(f"  Path: {self.skill_dir}")
        print()

        if not self.check_skill_dir():
            print("\n[ERROR] Skill directory not found -- cannot continue.")
            return False

        self.check_support_yml()
        self.check_skill_md()
        self.check_file_sizes()
        self.check_python_syntax()

        total = self.passed + self.failed
        print()
        if self.failed == 0:
            print(f"All checks passed! ({self.passed}/{total})")
        else:
            print(f"{self.failed} check(s) FAILED ({self.passed}/{total} passed)")
            print()
            print("Failures:")
            for err in self.errors:
                print(f"  - {err}")

        return self.failed == 0


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <skill-dir>", file=sys.stderr)
        print(f"  e.g. {sys.argv[0]} skills/qodo-get-rules", file=sys.stderr)
        sys.exit(2)

    validator = Validator(sys.argv[1])
    success = validator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch Qodo rules and output them as context for Claude.
This script's stdout becomes part of Claude's context automatically.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, List, Dict


def run_git_command(args: List[str]) -> Optional[str]:
    """Run a git command and return its output, or None on error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def load_config() -> Tuple[Optional[str], Optional[str]]:
    """Load API key and environment name from config file or environment variables."""
    api_key = None
    environment_name = None

    # Try to read from config file first
    config_path = Path.home() / ".qodo" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get("API_KEY", "")
                environment_name = config.get("ENVIRONMENT_NAME", "")
        except Exception:
            pass

    # Environment variables take precedence
    api_key = os.environ.get("QODO_API_KEY", api_key or "")
    environment_name = os.environ.get("QODO_ENVIRONMENT_NAME", environment_name or "")

    return api_key or None, environment_name or None


def build_api_url(environment_name: Optional[str]) -> str:
    """Build API URL based on environment name."""
    if environment_name:
        return f"https://qodo-platform.{environment_name}.qodo.ai/rules/v1"
    return "https://qodo-platform.qodo.ai/rules/v1"


def parse_repo_scope(remote_url: str) -> Optional[str]:
    """
    Parse repository scope from git remote URL.
    Examples:
      git@github.com:org/repo.git -> /org/repo/
      https://github.com/org/repo.git -> /org/repo/
      https://github.com/org/repo -> /org/repo/
    """
    pattern = r'^.*[:/]([^/]+/[^/]+?)(?:\.git)?$'
    match = re.match(pattern, remote_url)
    if match:
        return f"/{match.group(1)}/"
    return None


def detect_scope() -> Tuple[str, str]:
    """
    Detect the query scope based on current working directory.
    Returns (query_scope, scope_context).
    """
    # Get repository scope from git remote
    remote_url = run_git_command(["config", "--get", "remote.origin.url"])
    if not remote_url:
        sys.exit(0)  # No git remote, exit silently

    repo_scope = parse_repo_scope(remote_url)
    if not repo_scope:
        print(f"⚠️  Could not parse repository from git remote: {remote_url}")
        sys.exit(0)

    # Get repo root and current directory
    repo_root = run_git_command(["rev-parse", "--show-toplevel"])
    if not repo_root:
        return repo_scope, "Scope: Repository-wide"

    cwd = os.getcwd()

    # Calculate relative path from repo root
    try:
        rel_path = os.path.relpath(cwd, repo_root)
    except ValueError:
        # Different drives on Windows
        return repo_scope, "Scope: Repository-wide"

    # Convert to Path for cross-platform handling
    rel_path_obj = Path(rel_path)

    # Check if we're in a module directory (modules/*)
    # Use path parts to avoid separator issues across platforms
    if len(rel_path_obj.parts) >= 2 and rel_path_obj.parts[0] == "modules" and rel_path != ".":
        # Extract module path: modules/rules/src/service.py → modules/rules
        # Convert to POSIX format for API (always use / in URLs)
        module_path_posix = str(PurePosixPath(*rel_path_obj.parts[:2]))
        query_scope = f"{repo_scope}{module_path_posix}/"
        # Use native path format for display
        module_path_display = str(Path(*rel_path_obj.parts[:2]))
        scope_context = f"Module: `{module_path_display}`"
        return query_scope, scope_context

    return repo_scope, "Scope: Repository-wide"


def fetch_rules(api_url: str, api_key: str, query_scope: str) -> List[Dict]:
    """Fetch all rules from API with pagination."""
    all_rules = []
    page = 1
    page_size = 50

    while True:
        # URL-encode the query_scope parameter to handle spaces and special characters
        encoded_scope = urllib.parse.quote(query_scope, safe='')
        url = f"{api_url}/rules?scopes={encoded_scope}&state=active&page={page}&page_size={page_size}"

        try:
            request = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {api_key}"}
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode('utf-8')
                data = json.loads(body)

                page_rules = data.get("rules", [])
                all_rules.extend(page_rules)

                # If we got fewer than PAGE_SIZE rules, we've reached the last page
                if len(page_rules) < page_size:
                    break

                page += 1

        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("⚠️  Invalid or expired Qodo API key. Please check your API key at https://app.qodo.ai/settings/api-keys")
            else:
                print(f"⚠️  Failed to fetch Qodo rules (HTTP {e.code})")
            sys.exit(0)
        except urllib.error.URLError:
            print(f"⚠️  Could not connect to Qodo API at {api_url}")
            sys.exit(0)
        except Exception:
            print("⚠️  Failed to fetch Qodo rules")
            sys.exit(0)

    return all_rules


def format_rules_by_severity(rules: List[Dict]) -> None:
    """Format and print rules grouped by severity."""
    # Group rules by severity
    error_rules = [r for r in rules if r.get("severity") == "error"]
    warning_rules = [r for r in rules if r.get("severity") == "warning"]
    rec_rules = [r for r in rules if r.get("severity") == "recommendation"]

    # Format ERROR rules
    if error_rules:
        print(f"## ❌ ERROR Rules (Must Comply) - {len(error_rules)}")
        print()
        for rule in error_rules:
            name = rule.get("name", "")
            category = rule.get("category", "")
            description = rule.get("description", "")
            print(f"- **{name}** ({category}): {description}")
        print()

    # Format WARNING rules
    if warning_rules:
        print(f"## ⚠️  WARNING Rules (Should Comply) - {len(warning_rules)}")
        print()
        for rule in warning_rules:
            name = rule.get("name", "")
            category = rule.get("category", "")
            description = rule.get("description", "")
            print(f"- **{name}** ({category}): {description}")
        print()

    # Format RECOMMENDATION rules
    if rec_rules:
        print(f"## 💡 RECOMMENDATION Rules (Consider) - {len(rec_rules)}")
        print()
        for rule in rec_rules:
            name = rule.get("name", "")
            category = rule.get("category", "")
            description = rule.get("description", "")
            print(f"- **{name}** ({category}): {description}")
        print()


def main():
    """Main entry point."""
    # Check if git is available
    if not shutil.which("git"):
        print("⚠️  Git is not installed or not in PATH. Please install Git:")
        print("   - macOS: brew install git or download from https://git-scm.com")
        print("   - Ubuntu/Debian: apt-get install git")
        print("   - Windows: Download from https://git-scm.com/download/win")
        sys.exit(0)

    # Check if we're in a git repository
    if not run_git_command(["rev-parse", "--git-dir"]):
        sys.exit(0)  # Not in a git repo, exit silently

    # Load configuration
    api_key, environment_name = load_config()

    if not api_key:
        print("ℹ️  No Qodo API key configured. To enable repository-specific coding rules:")
        print("   - Set QODO_API_KEY environment variable, or")
        print("   - Create ~/.qodo/config.json with your API key")
        print()
        print("Get your API key at: https://app.qodo.ai/settings/api-keys")
        sys.exit(0)

    # Build API URL
    api_url = build_api_url(environment_name)

    # Detect scope
    query_scope, scope_context = detect_scope()

    # Fetch rules
    rules = fetch_rules(api_url, api_key, query_scope)

    if not rules:
        print(f"ℹ️  No Qodo rules configured for repository: {query_scope}")
        print()
        print("Set up rules at: https://app.qodo.ai")
        sys.exit(0)

    # Output formatted rules
    print("# 📋 Qodo Rules Loaded")
    print()
    print(f"Repository: `{query_scope}`")
    print(scope_context)
    print(f"Rules loaded: **{len(rules)}** (universal, org level, repo level, and path level rules)")
    print()
    print("These rules must be applied during code generation based on severity:")
    print()

    format_rules_by_severity(rules)

    print("---")
    print()


if __name__ == "__main__":
    main()

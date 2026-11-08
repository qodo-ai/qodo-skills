#!/usr/bin/env python3
"""Launch immutable, skill-local Cockpit resources without installing or updating anything."""
import sys

sys.dont_write_bytecode = True
if sys.version_info < (3, 9):
    sys.exit("Cockpit prerequisite: Python 3.9 or newer is required.")

import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess

SKILL = Path(__file__).resolve().parent.parent
RUNTIME = SKILL / "runtime"


def provenance():
    """Read generated version/distribution/host stamps, never the multi-skill plugin root."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    header = text.split("\n---", 1)[0]
    values = {}
    for key in ("version", "distribution", "host"):
        match = re.search(r"^  " + key + r":\s*[\"']?([a-zA-Z0-9.-]+)", header, re.M)
        if match:
            values[key] = match.group(1)
    if not values.get("version") or not values.get("distribution"):
        sys.exit("Cockpit package error: installed skill provenance is missing.")
    args = ["--skill", "qodo-review-cockpit", "--skill-version", values["version"],
            "--distribution", values["distribution"]]
    # Generated hosts carry the host on the provenance-bearing invocation.
    host = re.search(r"--distribution [a-z0-9-]+ --host ([a-z0-9-]+)", text)
    host_value = values.get("host") or (host.group(1) if host else None)
    if host_value:
        args += ["--host", host_value]
    return args


def probe(command, gate):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        sys.exit("Cockpit " + gate + " failed; inspect the installed CLI connection before retrying.")
    if result.returncode:
        # Identity/catalog payloads may contain user data: do not echo them into launch logs.
        sys.exit("Cockpit " + gate + " failed (CLI exit " + str(result.returncode)
                 + "); inspect that CLI operation. Stop on authentication or permission denial.")
    return result.stdout


def main():
    if not (RUNTIME / "cockpit" / "__main__.py").is_file():
        sys.exit("Cockpit package error: pinned runtime resources are missing; reinstall through your existing skills channel.")
    cli = shutil.which(os.environ.get("REVIEW_COCKPIT_QODO") or "qodo")
    if not cli:
        sys.exit("Cockpit CLI prerequisite: Qodo CLI 2.0.0 or newer is required; use qodo-setup.")
    version = probe([cli, "--version"], "CLI version probe")
    match = re.fullmatch(r"(?:qodo(?: version)?\s+)?v?(\d+)\.(\d+)\.(\d+)(?:[-+][\w.-]+)?\s*", version, re.I)
    if not match or int(match.group(1)) < 2:
        sys.exit("Cockpit CLI prerequisite: Qodo CLI 2.0.0 or newer is required; preserve your update origin.")
    stamp = provenance()
    for command, gate in (([cli, "read", "whoami", "--json", *stamp], "authentication probe"),
                          ([cli, "read", "tools", "--json"], "read catalog probe")):
        payload = probe(command, gate)
        try:
            value = json.loads(payload)
            if not isinstance(value, (dict, list)) or (isinstance(value, dict) and value.get("error")):
                raise ValueError()
        except ValueError:
            sys.exit("Cockpit " + gate + " failed: invalid or error payload. Inspect that CLI operation.")
    home = Path(os.environ.get("REVIEW_COCKPIT_HOME") or os.environ.get("PR_COCKPIT_HOME")
                or Path.home() / ".qodo" / "review-cockpit").expanduser().resolve()
    if home == SKILL or SKILL in home.parents:
        sys.exit("Cockpit data-home error: choose a state directory outside installed skill resources.")
    os.environ["REVIEW_COCKPIT_HOME"] = str(home)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["REVIEW_COCKPIT_QODO"] = cli
    sys.path.insert(0, str(RUNTIME))
    sys.argv = ["cockpit", "--product", *sys.argv[1:]]
    runpy.run_module("cockpit", run_name="__main__")


if __name__ == "__main__":
    main()

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


def state_home():
    """Preserve explicit aliases and an older external home pointer; never migrate stored reviews."""
    selected = os.environ.get('REVIEW_COCKPIT_HOME') or os.environ.get('PR_COCKPIT_HOME')
    legacy = RUNTIME / 'config.local.json'
    if not selected and legacy.is_file():
        try:
            config = json.loads(legacy.read_text(encoding='utf-8'))
            selected = config.get('home') if isinstance(config, dict) else None
            if selected is not None and (not isinstance(selected, str) or not selected.strip()):
                raise ValueError()
        except (OSError, ValueError):
            sys.exit('Cockpit data-home error: inspect the existing config.local.json home pointer.')
    if not selected and (RUNTIME / 'sessions').is_dir():
        sys.exit('Cockpit found reviews in its old runtime directory. Select an external data home and '
                 'migrate them explicitly; no reviews were moved.')
    return Path(selected or Path.home() / '.qodo' / 'review-cockpit').expanduser().resolve()


def resolve_cli():
    explicit = os.environ.get('REVIEW_COCKPIT_QODO')
    if explicit:
        return shutil.which(explicit) or (explicit if Path(explicit).is_file() else None)
    found = shutil.which('qodo')
    if found:
        return found
    root = Path(os.environ.get('QODO_HOME') or Path.home() / '.qodo') / 'bin'
    names = ('qodo.exe', 'qodo.cmd', 'qodo') if sys.platform == 'win32' else ('qodo',)
    return next((str(root / name) for name in names if (root / name).is_file()), None)


def main():
    # The pinned runtime reads/writes UTF-8 review content. Windows otherwise uses
    # a legacy code page; enable Python's process-wide mode before any probes or IO.
    if not sys.flags.utf8_mode:
        os.environ["PYTHONUTF8"] = "1"
        command = [sys.executable, "-X", "utf8", "-B",
                   str(Path(__file__).resolve()), *sys.argv[1:]]
        if sys.platform == "win32":
            # Windows execv does not preserve child status/argument quoting like POSIX.
            raise SystemExit(subprocess.call(command))
        os.execv(sys.executable, command)
    if not (RUNTIME / "cockpit" / "__main__.py").is_file():
        sys.exit("Cockpit package error: runtime resources are missing; reinstall through your existing skills channel.")
    cli = resolve_cli()
    if not cli:
        sys.exit("Cockpit CLI prerequisite: Qodo CLI 2.0.0 or newer is required; use qodo-setup.")
    sys.path.insert(0, str(RUNTIME))
    from cockpit.cli_process import argv
    try:
        invocation = argv(cli)
    except OSError as error:
        sys.exit('Cockpit CLI prerequisite: ' + str(error))
    version = probe(invocation + ["--version"], "CLI version probe")
    match = re.fullmatch(r"(?:qodo(?: version)?\s+)?v?(\d+)\.(\d+)\.(\d+)(?:[-+][\w.-]+)?\s*", version, re.I)
    if not match or int(match.group(1)) < 2:
        sys.exit("Cockpit CLI prerequisite: Qodo CLI 2.0.0 or newer is required; preserve your update origin.")
    stamp = provenance()
    for command, gate in ((invocation + ["read", "whoami", "--json", *stamp], "authentication probe"),
                          (invocation + ["read", "tools", "--json"], "read catalog probe")):
        payload = probe(command, gate)
        try:
            value = json.loads(payload)
            if not isinstance(value, dict) or value.get("error"):
                raise ValueError()
            if gate == "authentication probe":
                if not (isinstance(value.get('workspace_id'), str) and value['workspace_id'].strip()
                        and any(isinstance(value.get(k), str) and value[k].strip()
                                for k in ('user_id', 'account_id', 'tenant_id'))):
                    raise ValueError()
            else:
                tools = value.get('tools')
                if not isinstance(tools, list) or not any(
                        isinstance(t, dict) and t.get('access') == 'read' and not t.get('mutating')
                        and isinstance(t.get('group'), str) and t['group'].strip()
                        and isinstance(t.get('leaf'), str) and t['leaf'].strip() for t in tools):
                    raise ValueError()
        except ValueError:
            sys.exit("Cockpit " + gate + " failed: invalid or error payload. Inspect that CLI operation.")
    home = state_home()
    if home == SKILL or SKILL in home.parents:
        sys.exit("Cockpit data-home error: choose a state directory outside installed skill resources.")
    os.environ["REVIEW_COCKPIT_HOME"] = str(home)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["REVIEW_COCKPIT_QODO"] = cli
    sys.argv = ["cockpit", "--product", *sys.argv[1:]]
    runpy.run_module("cockpit", run_name="__main__")


if __name__ == "__main__":
    main()

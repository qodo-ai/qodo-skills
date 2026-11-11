"""Shared helpers: paths, config, gh calls, tiny frontmatter parser."""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the code: skill, engine, app (replaced on every update)
DEFAULT_HOME = Path.home() / ".qodo" / "agent-session-review"
LEGACY_HOME = Path.home() / ".qodo" / "review-cockpit"
if not DEFAULT_HOME.exists() and LEGACY_HOME.is_dir():
    DEFAULT_HOME = LEGACY_HOME


def data_home() -> Path:
    """Where your reviews, memory and config live, apart from the code so an update never touches them:
    $QODO_AGENT_SESSION_REVIEW_HOME (legacy aliases remain accepted), else `home` in config.local.json,
    else a checkout holding its sessions, else the current or pre-existing legacy external data home.
    Fresh installations use ~/.qodo/agent-session-review; this selection never moves stored data."""
    env = (os.environ.get("QODO_AGENT_SESSION_REVIEW_HOME") or os.environ.get("REVIEW_COCKPIT_HOME")) or os.environ.get("PR_COCKPIT_HOME")
    if env:
        return Path(env).expanduser()
    local = ROOT / "config.local.json"
    if local.is_file():
        try:
            home = json.loads(local.read_text()).get("home")
        except ValueError:
            home = None
        if home:
            return Path(home).expanduser()
    if (ROOT / "sessions").is_dir():
        return ROOT
    return DEFAULT_HOME


HOME = data_home()


def config_file() -> Path:
    """Your config file: config.json in the data home, or config.local.json when the data lives in the checkout."""
    return HOME / "config.json" if HOME != ROOT else ROOT / "config.local.json"


def sessions_home() -> Path:
    """Where work packages are collected and listed: `sessions` in your config file, else <data home>/sessions."""
    f = config_file()
    try:
        v = json.loads(f.read_text()).get("sessions") if f.is_file() else None
    except ValueError:
        v = None
    return Path(v).expanduser() if isinstance(v, str) and v.strip() else HOME / "sessions"


SESSIONS = sessions_home()


def set_sessions(path: str | None) -> Path:
    """Point the work package folder somewhere else (None or "" goes back to the default), saved in your config
    file, and swapped in for every cockpit module that read it, so a running server lists the new folder."""
    import sys
    f = config_file()
    try:   # a damaged or non-object config is replaced, as sessions_home() already reads it
        raw = json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    if path:
        raw["sessions"] = str(Path(path).expanduser())
    else:
        raw.pop("sessions", None)
    f.parent.mkdir(parents=True, exist_ok=True)
    write_json(f, raw)   # swapped in whole: a reader never sees half a config
    new = sessions_home()
    for m in list(sys.modules.values()):
        if (getattr(m, "__name__", "") or "").startswith(__package__ + ".") or m is sys.modules.get(__name__):
            if hasattr(m, "SESSIONS"):
                m.SESSIONS = new
    return new

# Emoji marks: one table used by the app, GitHub comment prefixes and the distiller.
EMOJI = {
    "🚫": {"meaning": "blocking", "label": "Blocking", "prefix": "**Blocking:**"},
    "❓": {"meaning": "question", "label": "Question", "prefix": "**Question:**"},
    "🧹": {"meaning": "nit", "label": "Nit", "prefix": "nit:"},
    "🐛": {"meaning": "bug", "label": "Bug", "prefix": "**Bug:**"},
    "🔒": {"meaning": "security", "label": "Security", "prefix": "**Security:**"},
    "👏": {"meaning": "praise", "label": "Praise", "prefix": "👏"},
    "👍": {"meaning": "useful", "label": "Useful", "prefix": None},
    "👎": {"meaning": "not_useful", "label": "Not useful", "prefix": None},
    "🤔": {"meaning": "unsure", "label": "Unsure", "prefix": None},
}


def today() -> str:
    return _dt.date.today().isoformat()


def write_text(path, text, *, preserve_mode=False) -> None:
    """Replace one text file atomically, preserving the caller’s default text encoding."""
    import os, secrets, stat, tempfile
    path = Path(path)
    mode = stat.S_IMODE(path.stat().st_mode) if preserve_mode and path.exists() else None
    if preserve_mode:
        tmp = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
        # Match ordinary text-file creation under the caller's umask without changing it.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode if mode is not None else 0o666)
    else:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path, data) -> None:
    import json
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config() -> dict:
    """config.json (the defaults that ship), overlaid by your config.json in the data home, then by
    config.local.json next to the code (older installs, and the `home` pointer)."""
    cfg = json.loads((ROOT / "config.json").read_text())
    from .product import enabled
    if enabled():
        cfg['memory'] = {**cfg.get('memory', {}), 'enabled': False, 'auto_commit': False}
    for over in ([HOME / "config.json"] if HOME != ROOT else []) + [ROOT / "config.local.json"]:
        if over.is_file():
            cfg = _merge(cfg, json.loads(over.read_text()))
    cfg.setdefault("emoji", EMOJI)
    return cfg


def memory_on(cfg: dict) -> bool:
    """Memory (learned preferences and team knowledge) is optional: `memory.enabled` in the config."""
    return str((cfg.get("memory") or {}).get("enabled", True)).lower() != "false"


def session_config(sdir: Path) -> dict:
    """Config with the memory locations recorded in a session (demo sessions use a copy)."""
    data = json.loads((sdir / "review-data.json").read_text())
    from .product import scope
    with scope(data):
        cfg = load_config()
    if data.get("memory"):
        mem = dict(data["memory"])
        mem["auto_commit"] = str(mem.get("auto_commit")).lower() == "true"
        mem["enabled"] = str(mem.get("enabled", True)).lower() != "false"
        cfg["memory"] = mem
    return cfg


def mem_path(cfg: dict, kind: str) -> Path:
    """Where memory lives; with memory off, a folder that is never created, so it reads as empty."""
    if not memory_on(cfg):
        return HOME / ".memory-off" / kind
    p = Path(cfg["memory"][kind]).expanduser()
    return p if p.is_absolute() else HOME / p


def gh(args: list[str], input_text: str | None = None) -> str:
    """Run gh and return stdout. Raises RuntimeError with stderr on failure."""
    from .product import enabled
    if enabled():
        raise RuntimeError('gh is unavailable in product mode; use managed Qodo reads')
    p = subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def gh_json(args: list[str]):
    out = gh(args).strip()
    if not out:
        return None
    # `--paginate` prints one JSON array per page back to back: "[...][...]".
    dec, pos, pages = json.JSONDecoder(), 0, []
    while pos < len(out):
        val, pos = dec.raw_decode(out, pos)
        pages.append(val)
        while pos < len(out) and out[pos].isspace():
            pos += 1
    if len(pages) > 1 and all(isinstance(p, list) for p in pages):
        return [x for p in pages for x in p]
    return pages[0]


def slug(s: str, n: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n] or "item"


# ---------- frontmatter (YAML subset; JSON flow values are valid YAML) ----------

def _scalar(v: str):
    v = v.strip()
    if v == "":
        return None
    if v[0] in "[{\"" or v in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", v):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    if v[0] in "[{":  # YAML flow without quotes, e.g. [a, b] or { by: x, at: y }
        inner = v[1:-1].strip()
        if v[0] == "[":
            return [_scalar(x) for x in _split_flow(inner)] if inner else []
        out = {}
        for part in _split_flow(inner):
            k, _, val = part.partition(":")
            out[k.strip()] = _scalar(val)
        return out
    if v[0] == "'" and v[-1] == "'":
        return v[1:-1]
    return v


def _split_flow(s: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    """Return (meta, body). meta is None when there is no frontmatter block."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    block, body = text[3:end].strip("\n"), text[end + 4:].lstrip("\n")
    try:
        import yaml  # type: ignore
        return (yaml.safe_load(block) or {}), body
    except ImportError:
        pass
    meta: dict = {}
    key = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2)
            meta[key] = _scalar(val) if val.strip() else []
            continue
        item = re.match(r"^\s*-\s*(.*)$", line)
        if item and key is not None:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            body_item = item.group(1)
            kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", body_item)
            if kv and not body_item.startswith(("{", "[", '"')):
                meta[key].append({kv.group(1): _scalar(kv.group(2))})
            else:
                meta[key].append(_scalar(body_item))
            continue
        cont = re.match(r"^\s+([A-Za-z_][\w-]*):\s*(.*)$", line)
        if cont and key is not None:
            target = meta.get(key)
            if isinstance(target, list) and target and isinstance(target[-1], dict):
                target[-1][cont.group(1)] = _scalar(cont.group(2))
            elif isinstance(target, dict) or target in (None, []):
                if not isinstance(target, dict):
                    meta[key] = {}
                meta[key][cont.group(1)] = _scalar(cont.group(2))
    return meta, body


def dump_frontmatter(meta: dict) -> str:
    """Write each key on one line; complex values as JSON flow (valid YAML)."""
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        elif isinstance(v, str) and (v == "" or re.search(r"[:#\[\]{}\n\"']|^[\s`*&!|>%@?,-]|\s$", v)
                                     or re.fullmatch(r"(?i)-?\d+(\.\d+)?|true|false|null|yes|no|on|off|~", v)):
            # anything YAML could misread (indicators at the start, quotes, booleans) is JSON-quoted
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def glob_to_regex(glob: str) -> "re.Pattern[str]":
    """`**/` matches zero or more directories, `**` anything, `*` within one segment."""
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif glob.startswith("**", i):
            out += ".*"; i += 2
        elif glob[i] == "*":
            out += "[^/]*"; i += 1
        elif glob[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(glob[i]); i += 1
    return re.compile("^" + out + "$")


def glob_match(path: str, glob: str) -> bool:
    return bool(glob_to_regex(glob).match(path))

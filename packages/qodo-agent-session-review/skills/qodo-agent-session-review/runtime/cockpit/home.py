"""The data home: your reviews, memory and config, kept apart from the code (a plugin or CLI update replaces
the code's folder). `describe` says where things are; `migrate` copies a checkout's data out of it."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from . import util


def describe() -> dict:
    cfg = util.load_config()
    return {"home": str(util.HOME), "code": str(util.ROOT), "sessions": str(util.SESSIONS),
            "config": str(util.HOME / "config.json") if util.HOME != util.ROOT else str(util.ROOT / "config.local.json"),
            "memory": {"enabled": util.memory_on(cfg), "amr": str(util.mem_path(cfg, "amr")), "okf": str(util.mem_path(cfg, "okf"))},
            "in_checkout": util.HOME == util.ROOT}


def migrate(to: Path | None = None) -> dict:
    """Copy sessions, memory and config from the active data home (the code's folder, or the home it already points
    at) to a new data home, then point the code at it (`home` in config.local.json). Nothing is deleted: the old
    folders stay as they were, and the first config.local.json is kept as config.local.json.before-migrate, so
    undoing is restoring that file. Anything already in the destination is kept, never overwritten."""
    root = util.ROOT.resolve()
    env_name = next((name for name in ("QODO_AGENT_SESSION_REVIEW_HOME", "REVIEW_COCKPIT_HOME", "PR_COCKPIT_HOME")
                     if os.environ.get(name)), None)
    env = os.environ.get(env_name) if env_name else None
    env_home = Path(env).expanduser().resolve() if env else None
    dst = (to or env_home or util.DEFAULT_HOME).expanduser().resolve()   # the env var picks the home, so it is the default
    if dst == root:
        return {"error": f"{dst} is the code's own folder"}
    if env_home and dst != env_home:   # a pointer would be ignored while the env var is set
        return {"error": f"{env_name} is {env_home}, which wins over any pointer: unset it, or migrate --to {env_home}"}
    local, backup = root / "config.local.json", root / "config.local.json.before-migrate"
    raw = json.loads(local.read_text()) if local.is_file() else {}
    pointed = None if env_home == dst else raw.get("home")
    active = Path(pointed).expanduser().resolve() if pointed else root
    src = active if active not in (root, dst) else root   # a second move starts from where the data is now
    dst.mkdir(parents=True, exist_ok=True)
    copied, kept = [], []

    def copy(rel: str):
        s, t = src / rel, dst / rel
        if not s.exists():
            return
        if t.exists():
            kept.append(str(t))
            return
        t.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree(s, t, symlinks=True, ignore=shutil.ignore_patterns(".git")) if s.is_dir() else shutil.copy2(s, t))
        copied.append(rel)

    if (src / "sessions").is_dir():
        for s in sorted((src / "sessions").iterdir()):
            copy(f"sessions/{s.name}")
    if src == root:
        cfg = {k: v for k, v in raw.items() if k != "home"}
        cfg_from = "config.local.json"
    else:
        cfg = json.loads((src / "config.json").read_text()) if (src / "config.json").is_file() else {}
        cfg_from = f"{src}/config.json"
    shipped = (json.loads((root / "config.json").read_text()).get("memory") or {}) if (root / "config.json").is_file() else {}
    mem = {**shipped, **(cfg.get("memory") or {})}
    for kind in ("amr", "okf"):   # each relative memory folder on its own; absolute ones already live outside
        rel = Path(str(mem.get(kind, f"memory/{kind}"))).expanduser()
        if not rel.is_absolute():
            copy(rel.as_posix())
    if cfg:
        if (dst / "config.json").exists():
            kept.append(str(dst / "config.json"))
        else:
            (dst / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
            copied.append(f"{cfg_from} → config.json")
    if local.is_file() and "home" not in raw and not backup.exists():   # only the original, never a pointer
        shutil.copy2(local, backup)
    local.write_text(json.dumps({"home": str(dst)}, indent=2) + "\n")
    undo = f"restore {backup.name} as {local.name}" if backup.exists() else f"delete {local}"
    return {"home": str(dst), "from": str(src), "copied": copied, "kept": kept, "undo": f"{undo} (the old folders are untouched)"}

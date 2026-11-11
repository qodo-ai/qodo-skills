"""Placeholder adapter for calling Qodo directly (CLI or HTTP API).

Enable by adding "qodo_api" to config.adapters and setting config.qodo_api.command,
a shell command template that prints a JSON list of findings, e.g.
  "qodo review --pr {url} --format json"
Each item should already have (or be mapped to) the normalized finding keys.
"""
from __future__ import annotations

import json
import shlex
import subprocess


def collect(pr: dict, cfg: dict) -> list[dict]:
    q = cfg.get("qodo_api") or {}
    if not q.get("enabled") or not q.get("command"):
        return []
    cmd = q["command"].format(url=pr["url"], repo=pr["repo"], number=pr["number"])
    p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        return []
    try:
        items = json.loads(p.stdout)
    except json.JSONDecodeError:
        return []
    out = []
    for i, it in enumerate(items):
        out.append({
            "id": f"qa-{pr['number']}-{it.get('id', i)}", "pr": pr["key"], "source": "qodo-api",
            "category": it.get("category", "general"), "severity": it.get("severity", "medium"),
            "path": it.get("path"), "line": it.get("line"), "title": it.get("title", "Qodo finding"),
            "body": it.get("body", ""), "url": it.get("url"),
        })
    return out

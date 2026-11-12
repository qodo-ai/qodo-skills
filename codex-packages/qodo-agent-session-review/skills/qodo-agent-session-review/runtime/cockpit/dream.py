"""Consolidation pass ("Dreaming"): keep both memories small and honest.

AMR: merge duplicate bullets (same rule, or same text) summing evidence; drop rule
bullets not seen within rule_ttl_days.
OKF: report concepts past stale_after, validate conformance, rebuild index.md.
"""
from __future__ import annotations

import datetime as _dt

from .memory import AMR, OKF, PREF_FILES, parse_bullet
from .util import load_config, mem_path, memory_on, now_iso


def dream(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    if not memory_on(cfg):
        return {"skipped": "memory is off (config memory.enabled)"}
    amr, okf = AMR(mem_path(cfg, "amr")), OKF(mem_path(cfg, "okf"))
    amr.ensure(cfg.get("reviewer") or "reviewer"); okf.ensure()
    ttl = _dt.timedelta(days=cfg["distill"]["rule_ttl_days"])
    today = _dt.date.today()
    report = {"merged": 0, "expired": [], "stale": [], "invalid": []}

    for rel in PREF_FILES.values():
        p = amr.root / rel
        if not p.exists():
            continue
        header, merged = [], {}
        for line in p.read_text().splitlines():
            b = parse_bullet(line, rel) if line.startswith("- ") else None
            if not b:
                header.append(line); continue
            key = b.rule or b.text.lower()
            if key in merged:
                m = merged[key]
                m.meta["evidence"] = str(m.evidence + b.evidence)
                m.meta["seen"] = max(m.meta.get("seen", m.meta.get("added", "")), b.meta.get("seen", b.meta.get("added", "")))
                report["merged"] += 1
            else:
                merged[key] = b
        kept = []
        for b in merged.values():
            last = b.meta.get("seen") or b.meta.get("added")
            if b.rule and last:
                try:
                    if today - _dt.date.fromisoformat(last) > ttl:
                        report["expired"].append(b.text); continue
                except ValueError:
                    pass
            kept.append(b)
        p.write_text("\n".join(header + [b.render() for b in kept]).rstrip() + "\n")

    now = now_iso()
    for c in okf.concepts():
        d = c.as_dict(now)
        if d["stale"]:
            report["stale"].append(c.path)
    report["invalid"] = okf.validate()
    okf.write_index()
    return report

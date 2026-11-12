"""Implementation routes: the ways this package could have been built, and why this one.

The skill writes `routes` (skill/references/storytelling.md, "Other ways to build this") when the change is big enough
to question its approach: a new service or provider, several repos, a large production diff, or a plan that names
alternatives. Each route says where it came from: `documented` (a design note, ticket or thread says it, with a link) or
`inferred` (the review read it off the code at the base, and says what would have to be proven). The page never
declares a winner the evidence doesn't support.
"""
from __future__ import annotations

import re

SOURCES = ("documented", "inferred")
FIT = ("better", "similar", "worse", "unknown")


def _list(v, n: int = 6, cap: int = 200) -> list[str]:
    v = [v] if isinstance(v, str) else v if isinstance(v, list) else []
    return [str(x).strip()[:cap] for x in v if str(x).strip()][:n]


def normalize(raw, prs: set[str]) -> tuple[dict | None, list[str]]:
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["routes: an object {question, chosen, options, why} or {skip}"]
    if raw.get("skip"):
        return {"skip": str(raw["skip"]).strip()[:300]}, []
    warn, opts = [], []
    for i, o in enumerate(raw.get("options") or [], 1):
        if not isinstance(o, dict) or not str(o.get("name") or "").strip():
            warn.append(f"routes.options {i}: needs a name; left out")
            continue
        src = str(o.get("source") or "").lower()
        if src not in SOURCES:
            warn.append(f"routes.options {i}: source is documented or inferred; read as inferred")
            src = "inferred"
        ref = o.get("ref") if isinstance(o.get("ref"), dict) and str((o.get("ref") or {}).get("url") or "").startswith(("https://", "http://")) else None
        if src == "documented" and not ref:
            warn.append(f"routes.options {i} ({o['name']}): a documented route links where it's documented (ref.url)")
        prove = str(o.get("prove") or "").strip()
        if src == "inferred" and not prove:
            warn.append(f"routes.options {i} ({o['name']}): an inferred route says what would have to be proven (prove)")
        size = o.get("size") if isinstance(o.get("size"), dict) else {}
        opts.append({"id": str(o.get("id") or f"r{i}")[:24], "name": str(o["name"]).strip()[:80], "source": src,
                     "ref": {"url": ref["url"], "title": str(ref.get("title") or ref["url"])[:120]} if ref else None,
                     "idea": str(o.get("idea") or "").strip()[:400], "reuses": _list(o.get("reuses")), "builds": _list(o.get("builds")),
                     "touches": _list(o.get("touches"), 8, 60), "size": {"lines": size.get("lines") if isinstance(size.get("lines"), int) else None,
                                                                          "label": str(size.get("label") or "").strip()[:80]},
                     "covers": str(o.get("covers") or "").strip()[:300], "risks": _list(o.get("risks"), 4, 240), "prove": prove[:300],
                     "prs": [k for k in _list(o.get("prs"), 12, 80) if k in prs],
                     "fit": {k: (str(v).lower() if str(v).lower() in FIT else "unknown")
                             for k, v in (o.get("fit") or {}).items() if isinstance(k, str)} if isinstance(o.get("fit"), dict) else {}})
    if len(opts) < 2:
        warn.append("routes: needs at least two routes (the chosen one and one it was weighed against), or {skip: why}")
    ids = [o["id"] for o in opts]
    chosen = str(raw.get("chosen") or "")
    if chosen not in ids:
        warn.append(f"routes.chosen: names one of the routes ({', '.join(ids)})")
        chosen = ids[0] if ids else ""
    crit = _list(raw.get("criteria"), 6, 60)
    keep = opts[:4] if any(o["id"] == chosen for o in opts[:4]) else [o for o in opts if o["id"] == chosen] + opts[:3]   # the chosen one is never cut
    if len(opts) > 4:
        warn.append(f"routes: {len(opts)} routes; the page shows four, the chosen one among them")
    return {"question": str(raw.get("question") or "").strip()[:200], "chosen": chosen, "options": keep,
            "criteria": crit, "why": str(raw.get("why") or "").strip()[:600], "reconsider": str(raw.get("reconsider") or "").strip()[:400],
            "unargued": _list(raw.get("unargued"), 3, 300)}, warn


def sizes(p: dict) -> dict:
    """A PR's added lines by kind, with what came in from the base branch counted apart (it isn't this change)."""
    merged = {}
    for r in (p.get("attention") or {}).get("ranges", []):
        if re.match(r"(?i)\s*(merged (in )?from|from the base|base merge)", str(r.get("reason") or "")):   # the skill's triage marks them (storytelling.md 3c)
            merged[r["path"]] = merged.get(r["path"], 0) + (r.get("lines") or 0)
    out = {"production": 0, "test": 0, "docs": 0, "config": 0, "generated": 0, "from_base": 0}
    for f in p.get("files", []):
        add = f.get("additions") or 0
        base = min(add, merged.get(f["path"], 0))
        out["from_base"] += base
        role = f.get("role") or "source"
        key = "production" if role == "source" else role if role in out else "production"
        out[key] += add - base
    return out

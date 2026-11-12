"""The business criticality map: how much each changed path matters, and which paths Qodo must never approve.

Three sources, never mixed up:
- declared: the team's map, config `criticality.map`; each entry {repo, paths (globs), level, approve?, owner, reason,
  verify_after}. Only a declared entry (or CODEOWNERS, when the team opts in) can protect a path.
- codeowners: with `criticality.codeowners: "protect"`, a path a CODEOWNERS rule owns is protected (never
  auto-approved). A catch-all rule (`*`, `**`, `/`) protects nothing: it says who reviews, not what matters.
- discovered: the review's own suggestion (enrich `criticality`), with its reason. It is a suggestion until someone
  declares it, and an unconfirmed Low counts as undeclared, because a wrong Low hides damage.
Precedence per file: the most specific declared entry, then discovered; protection is the union of declared
`approve: never` and CODEOWNERS. Paths are globs from the start, so a whole repo is just `**`.
"""
from __future__ import annotations

import datetime as _dt
import re

LEVELS = ("low", "medium", "high")
CATCH_ALL = {"*", "**", "/", "/*", "/**", "**/*"}


def glob(pat: str, path: str) -> bool:
    """`*` stays inside one directory, `**` crosses them, a trailing / covers everything below it."""
    from .reviewers import _owns
    return _owns(pat.strip() or "**", path)   # CODEOWNERS rules: a bare folder covers what's below it, *.py any depth, /x anchors at the root


def specificity(pat: str) -> int:
    """How narrow a glob is: its literal characters. `**` (the whole repo) is the least specific."""
    p = pat.strip("/")
    return len(re.sub(r"[*?]", "", p)) * 4 + p.count("*") - 3 * p.count("**")   # foo/* is narrower than foo/**


def _date(s) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def normalize_map(raw, source: str = "declared") -> tuple[list[dict], list[str]]:
    """Map entries from config (declared) or from the review (discovered), checked. Discovered entries can't protect."""
    out, warn = [], []
    for i, e in enumerate(raw or [], 1):
        if not isinstance(e, dict):
            warn.append(f"criticality {i}: an object {{repo, paths, level, reason}}; left out")
            continue
        paths = e.get("paths") or ["**"]
        if not isinstance(paths, (str, list)):
            warn.append(f"criticality {i}: paths is a glob or a list of globs; left out"); continue
        paths = [paths] if isinstance(paths, str) else [p for p in paths if isinstance(p, str) and p.strip()]
        if not paths:
            warn.append(f"criticality {i}: no usable paths; left out"); continue
        level = str(e.get("level") or "").lower()
        if level not in LEVELS and not (source == "declared" and e.get("approve")):
            warn.append(f"criticality {i}: needs level ({'|'.join(LEVELS)}); left out")
            continue
        reason = str(e.get("reason") or e.get("why") or "").strip()
        if not reason:
            warn.append(f"criticality {i}: needs a reason, so the level is accountable")
        approve = str(e.get("approve") or "").lower()
        if approve and source != "declared":
            warn.append(f"criticality {i}: only the team's map can protect a path; `approve` dropped from a {source} entry")
            approve = ""
        out.append({"repo": str(e.get("repo") or "*"), "paths": paths, "level": level if level in LEVELS else None,
                    "approve": "never" if approve == "never" else None, "owner": str(e.get("owner") or "")[:80],
                    "reason": reason[:300], "verify_after": str(e.get("verify_after") or "")[:10] or None, "source": source,
                    **({"ev": [x for x in e["ev"] if isinstance(x, dict) and x.get("path")][:4]} if isinstance(e.get("ev"), list) else {})})
    return out, warn


def _repo_ok(entry_repo: str, repo: str) -> bool:
    return entry_repo in ("*", "") or entry_repo.lower() == repo.lower()


def _best(entries: list[dict], repo: str, path: str) -> tuple[dict | None, str | None]:
    hits = [(specificity(p), e, p) for e in entries if _repo_ok(e["repo"], repo) for p in e["paths"] if glob(p, path)]
    if not hits:
        return None, None
    s, e, p = max(hits, key=lambda h: (h[0], h[1]["repo"] != "*"))   # narrowest glob, a named repo over "*"
    return e, p


def resolve(data: dict, cfg: dict | None = None, today: _dt.date | None = None) -> dict:
    """Every changed file's criticality and protection, with where each came from; plus the map's entries."""
    cfg = cfg or {}
    today = today or _dt.date.today()
    ccfg = cfg.get("criticality") or {}
    declared, warn = normalize_map(ccfg.get("map"), "declared")
    discovered = data.get("criticality") or []
    protect_co = str(ccfg.get("codeowners") or "off").lower() == "protect"
    rv = data.get("reviewers") or {}
    owned = (rv.get("owned") or {}) if protect_co else {}
    owners_unchecked = protect_co and ("owned" not in rv or bool(rv.get("stale")) or rv.get("ownership_complete") is False)   # never looked up, or the files moved since
    files = []
    for p in data.get("prs", []):
        for f in p.get("files", []):
            path, repo = f["path"], p["repo"]
            d, dp = _best([e for e in declared if e["level"]], repo, path)
            g, gp = _best(discovered, repo, path)
            both = [path] + ([f["previous"]] if f.get("previous") else [])   # moving a file out of a protected folder still touches it
            lock = next(((e, x) for e in declared if e["approve"] == "never" and _repo_ok(e["repo"], repo)
                         for x in e["paths"] for q in both if glob(x, q)), None)
            co = next((pat for q in both for pat in owned.get(repo, {}).get(q, []) if pat.strip() not in CATCH_ALL), None) if owned else None
            if d:
                level, source, entry, pat = d["level"], "declared", d, dp
            elif g and g["level"] in ("medium", "high"):
                level, source, entry, pat = g["level"], "discovered", g, gp
            else:   # nothing declared, and an unconfirmed Low is no answer
                level, source, entry, pat = "undeclared", "none", None, None
            vd = _date(entry.get("verify_after")) if entry else None
            files.append({"pr": p["key"], "repo": repo, "path": path, "lines": (f.get("additions") or 0) + (f.get("deletions") or 0),
                          "role": f.get("role"), "level": level, "source": source, "pattern": pat,
                          "reason": (entry or {}).get("reason", ""), "owner": (entry or {}).get("owner", ""),
                          "stale": bool(vd and vd < today), "suggested": g["level"] if g and not d else None,
                          "suggested_why": g.get("reason", "") if g and not d else "",
                          "protected": bool(lock or co),
                          "protected_by": (f"declared: {lock[1]}" if lock else f"CODEOWNERS: {co}" if co else None)})
    protecting = bool(owned) or any(e["approve"] == "never" for e in declared)
    unseen = {p["key"]: p["files_missing"] for p in data.get("prs", []) if p.get("files_missing")} if protecting else {}
    return {"files": files, "declared": declared, "discovered": discovered, "codeowners": bool(owned) or protect_co, "unseen": unseen,
            "owners_unchecked": owners_unchecked,
            "has_map": bool(declared), "warnings": warn}


def rank(level: str) -> int:
    return LEVELS.index(level) if level in LEVELS else -1


def for_paths(crit: dict, prs: list[str], paths: list[str]) -> dict:
    """A Merge Risk scenario's criticality: the highest over the changed files its paths name, with the source."""
    hit = [f for f in crit["files"] if (not prs or f["pr"] in prs) and any(glob(p, f["path"]) or f["path"] == p for p in paths or [])]
    if not hit:
        return {"level": "undeclared", "source": "none"}
    top = max(hit, key=lambda f: (rank(f["level"]), f["source"] == "declared"))
    if top["level"] == "undeclared":
        sug = max((f["suggested"] for f in hit if f["suggested"]), key=rank, default=None)
        return {"level": "undeclared", "source": "none", **({"suggested": sug} if sug else {})}
    return {"level": top["level"], "source": top["source"], "stale": top["stale"], "reason": top["reason"], "pattern": top["pattern"]}


def gate(crit: dict) -> dict:
    """Protected paths in the package: any one of them, in any PR, and Qodo doesn't approve. It still reviews."""
    if crit.get("error"):   # a map that can't be read protects nothing we can check: fail closed
        return {"protected": [], "count": 0, "prs": [], "mixed": False, "error": crit["error"]}
    prot = [f for f in crit["files"] if f["protected"]]
    return {"protected": [{k: f[k] for k in ("pr", "path", "protected_by")} for f in prot[:40]], "count": len(prot),
            "prs": sorted({f["pr"] for f in prot}), "mixed": bool(prot) and len(prot) < len(crit["files"]),
            "unseen": crit.get("unseen") or {},   # changed files the collector never got: their paths weren't checked
            "owners_unchecked": bool(crit.get("owners_unchecked"))}

"""What a review style renders from: one compact view of a session.

The styles in app/styles/ (guided, behavior) read this instead of the full review-data.json: per PR its
story, walk, plan blocks with the code of every deep and read block, files with their tiers, findings
and checks; the session story, sources, stacks and media; and the behavior diff with its code resolved.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import re
from urllib.parse import quote
from pathlib import Path

from .behavior import check as check_behavior, window

MAX_BLOCK = 80   # code lines kept per block
MAX_TESTS = 40   # added test cases named per PR

_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$")
_TEST_DECL = (re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)"), re.compile(r"^\s*(?:it|test)(?:\.(?:only|concurrent|skip|todo|failing))*(?:\.each\s*(?:\(.*?\)|`[^`]*`))?\(\s*[\"'`]([^\"'`]+)"),
              re.compile(r"^\s*func\s+(Test\w+)"))


def _tests(p: dict) -> list[dict]:
    """The test cases a PR adds, from every collected test-file hunk (not only the code a review keeps)."""
    out, seen = [], set()
    for f in p.get("files", []):
        if f.get("role") != "test" and not _TEST_PATH.search(f["path"]):
            continue
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                if ln[0] != "+":
                    continue
                m = next((m for r in _TEST_DECL if (m := r.match(ln[3]))), None)   # [kind, old, new, text, spans?]
                if m and (f["path"], m.group(1)) not in seen:
                    seen.add((f["path"], m.group(1)))
                    out.append({"name": m.group(1), "path": f["path"], "line": ln[2]})
    return out


def _test_counts(tests: list[dict]) -> dict:
    """New test cases per file, all of them (the view sends only the first MAX_TESTS names)."""
    out: dict = {}
    for t in tests:
        out[t["path"]] = out.get(t["path"], 0) + 1
    return out


def _code(files: dict, path: str, side: str, lo: int, hi: int) -> dict | None:
    f = files.get(path)
    if not f:
        return None
    w = window(f, side, lo, hi)
    return {"lines": w[:MAX_BLOCK], "cut": max(0, len(w) - MAX_BLOCK)}


def _derived_impact(data: dict) -> list[dict]:
    from .impact import derived
    return derived(data)


def _danger(p: dict) -> dict:
    from .impact import domains, door_guess
    return {"door_guess": door_guess(p), "domains": domains(p)}


def _evidence(p: dict) -> dict:
    from .impact import evidence
    return evidence(p)


def _decisions(p: dict) -> list[dict]:
    from .decisions import normalize
    return normalize(p.get("decisions"), p, resolve=True)[0] if p.get("decisions") else []


def _read_summary(evidence):
    if not evidence:
        return evidence
    sections = {}
    for name, section in (evidence.get('sections') or {}).items():
        pages = section.get('pages') or []
        sections[name] = {k: v for k, v in section.items() if k not in ('pages', 'items')}
        sections[name].update(item_count=len(section.get('items') or []), page_count=len(pages),
                              observations=[{k: page.get(k) for k in ('revision', 'observed_at', 'consistency', 'notes', 'complete')} for page in pages])
    return {**{k: v for k, v in evidence.items() if k != 'sections'}, 'sections': sections}


def _pr_view(p: dict) -> dict:
    from .product import enabled, project_pr
    if enabled(p):
        p = project_pr(p)
    files = {f["path"]: f for f in p.get("files", [])}
    att = p.get("attention") or {}
    code, blocks = {}, []
    for b in att.get("blocks", []):
        blocks.append({k: b.get(k) for k in ("id", "path", "side", "from", "to", "lines", "tier", "why", "score", "layer", "reason")})
        if b.get("tier") in ("deep", "review"):
            c = _code(files, b["path"], b.get("side", "new"), b["from"], b["to"])
            if c:
                code[b["id"]] = c
    for bt in p.get("story") or []:   # code beats show their own range
        if bt.get("kind") == "code" and bt.get("path") in files and bt.get("from"):
            c = _code(files, bt["path"], bt.get("side", "new"), bt["from"], bt.get("to", bt["from"]))
            if c:
                code[f"beat:{bt.get('id')}"] = c
    tiers: dict[str, dict] = {}
    for r in att.get("ranges", []):
        t = tiers.setdefault(r["path"], {"deep": 0, "review": 0, "skim": 0, "skip": 0})
        t[r["tier"]] = t.get(r["tier"], 0) + r.get("lines", 0)
    keep = ("id", "source", "category", "severity", "status", "verdict", "path", "line", "end_line", "side", "title", "stance", "url", "scanner", "local", "status_why", "qodo_type", "review_source", "git_sha", "review_run_id", "created_at", "commit", "qodo_id", "source_location", "current_anchor")
    return {
        "key": p["key"], "repo": p["repo"], "number": p["number"], "title": p["title"], "url": p.get("url"),
        "author": p.get("author"), "base": p.get("base"), "head": p.get("head"), "head_sha": p.get("head_sha"), "base_sha": p.get("base_sha"),
        "add": p.get("additions", 0), "del": p.get("deletions", 0),
        **({"review_decision_complete": p.get("review_decision_complete")} if p.get("product") else {}), "approvals": p.get("approvals") or [], "changes_requested": p.get("changes_requested") or [],   # human reviews at collection time
        "unresolved_threads": p.get("unresolved_threads"), "unresolved_ids": p.get("unresolved_ids") or [],   # review conversations not resolved at collection time (None: not read)
        "summary": p.get("summary"), "risk": p.get("risk"), "story": p.get("story") or [], "layers": p.get("layers") or [],
        "findings": [{**{k: f.get(k) for k in keep}, "why": f.get("stance_why"), "body": (f.get("body") or "")[:900]}
                     for f in p.get("findings", [])],
        "attention": {**({"coverage": {"complete": bool((p.get("product_evidence") or {}).get("patches_complete")), "scope": "observed_subset" if not (p.get("product_evidence") or {}).get("patches_complete") else "complete"}} if p.get("product") else {}), "summary": att.get("summary"), "blocks": blocks, "must_read": att.get("must_read", []),
                      # skim and skip, per file and reason, for the plan bar's segments
                      "ranges": [{k: r.get(k) for k in ("path", "tier", "lines", "reason", "evidence")}
                                 for r in att.get("ranges", []) if r.get("tier") in ("skim", "skip")]},
        "files": [{"path": f["path"], "role": f.get("role"), "add": f.get("additions", 0), "del": f.get("deletions", 0),
                   "semantic": f.get("semantic"), "tiers": tiers.get(f["path"], {})} for f in p.get("files", [])],
        "code": code, "tests": _tests(p)[:MAX_TESTS], "test_counts": _test_counts(_tests(p)), "evidence": {**_evidence(p), "results": p.get("test_results"), "coverage": p.get("coverage")}, **_danger(p), "files_missing": p.get("files_missing", 0), "checks": p.get("checks", []), "scans": p.get("scans", []), "qodo_source": p.get("qodo_source"), "body": (p.get("body") or "")[:1500],
        "identity": p.get('identity'), "product": p.get('product'), "product_evidence": p.get('product_evidence'), "read_evidence": _read_summary(p.get('read_evidence')), "qodo_review": p.get('qodo_review'), "qodo_read_error": p.get('qodo_read_error'),
        "decisions": _decisions(p), "notes": p.get("notes"), "quality": p.get("quality"),
        # what Qodo says the PR does (the stories tab falls back to it)
        "qodo": {k: (p.get("qodo") or {}).get(k) for k in ("headline", "description", "url")} if p.get("qodo") else None,
    }


def _media(data: dict, sdir: Path, inline: bool, *, story_media: bool = False) -> list[dict]:
    """Screenshots and videos from media beats, in story order, with the paths they show."""
    out, seen = [], set()

    def add(b: dict, pr: dict | None):
        src = b.get("src") or ""
        if not src or src in seen or (b.get("type") == "video" and not story_media):
            return
        seen.add(src)
        paths = [r.get("path") for r in (b.get("refs") or []) if isinstance(r, dict) and r.get("path")]
        if b.get("path"):
            paths.insert(0, b["path"])
        url = src
        if ":" in src.split("/")[0] and not src.startswith(("https://", "http://")):   # no javascript: or data: links
            return
        if not src.startswith(("https://", "http://")):
            f = (sdir / "media" / src).resolve()
            root = (sdir / "media").resolve()
            if not f.is_file() or not f.is_relative_to(root):
                return
            url = (f"data:{mimetypes.guess_type(f.name)[0] or 'image/png'};base64," + base64.b64encode(f.read_bytes()).decode()
                   if inline else "/media/" + src + "?s=" + quote(sdir.name))   # the package, for a tab another tab switched away from
        out.append({"file": src, "title": b.get("title") or src, "caption": b.get("caption") or b.get("lede") or "",
                    "paths": paths, "src": url, "pr": (pr or {}).get("key")})

    from .story_media import references
    for beat, pr in references(data, pairs=story_media):
        add(beat, pr)
    return out


def package_name(sdir: Path) -> str:
    """The name you gave a work package in Manage work packages (package.json in its folder), else ""."""
    try:
        n = json.loads((sdir / "package.json").read_text()).get("name")
    except (OSError, ValueError, AttributeError):
        return ""
    return n.strip()[:80] if isinstance(n, str) else ""


def title_of(data: dict) -> str:
    st = data.get("story") or []
    if len(st) > 1 and st[0].get("kind") == "notice":
        return st[1].get("title") or "PR review"
    return (st[0].get("title") if st else None) or (data["prs"][0]["title"] if len(data.get("prs", [])) == 1 else "PR review")


def blurb_of(data: dict) -> str:
    prs = data.get("prs", [])
    repos = sorted({p["repo"] for p in prs})
    n = len(prs)
    lines = sum(p.get("additions", 0) + p.get("deletions", 0) for p in prs)
    where = repos[0] if len(repos) == 1 else f"{len(repos)} repos"
    return f"{n} PR{'s' if n != 1 else ''} in {where} · {lines:,} changed lines"


def _prefs(sdir: Path) -> dict:
    """The active preference rules, read now (not at collect time), so Make memories shows on the next open."""
    try:
        from .memory import AMR
        from .util import mem_path, memory_on, session_config
        cfg = session_config(sdir)
        if not memory_on(cfg):
            return {"enabled": False, "rules": []}
        rules = AMR(mem_path(cfg, "amr")).active_rules(cfg["distill"]["dismiss_threshold"])
        return {"enabled": True, "rules": [{k: v for k, v in r.items() if k != "file"} for r in rules]}
    except Exception as e:   # noqa: BLE001 - memory never breaks the page
        return {"enabled": False, "rules": [], "error": f"{type(e).__name__}: {e}"}


def view_data(sdir: Path, *, inline_media: bool = False, data: dict | None = None, story_media: bool = False) -> dict:
    data = data or json.loads((sdir / "review-data.json").read_text())
    from .product import enabled, project_data
    if enabled(data):
        data = project_data(data)
    ctx = data.get("context") or {}
    effective_impact = data.get("impact") or _derived_impact(data)
    out = {"case": data["session"], "session": data["session"], "title": package_name(sdir) or title_of(data), "blurb": blurb_of(data),
           "collection": data.get("collection"), "product": bool(data.get("product")), "demo": bool(data.get("demo")), "dummy": bool(data.get("dummy")), "story": data.get("story") or [], "sources": ctx.get("sources", []), "related": ctx.get("related", []),
           "impact": effective_impact, "impact_source": "review" if data.get("impact") else "diff",
           "deploy": data.get("deploy") or [], "door": data.get("door"), "notices": data.get("notices") or [],
           "reviewed_at": data.get("created"),   # when the PRs were collected: the freshness line in every style
           "stacks": ctx.get("stacks", []), "media": _media(data, sdir, inline_media, story_media=story_media),
           "prs": [_pr_view(p) for p in data.get("prs", [])], "behavior": None,
           # other work on the same code; the closest first (lines, function, then file)
           "other_work": [{k: h.get(k) for k in ("for", "source", "key", "number", "title", "url", "author", "state", "merged_at",
                                                  "path", "closeness", "ours", "ours_new", "theirs", "function", "session", "agent_source", "at")}
                          for h in ((data.get("overlaps") or {}).get("external") or [])]}
    if data.get('product'):
        from .distill import load_events
        out['events'] = [e for e in load_events(sdir) if e.get('type') in ('note', 'mark', 'finding_verdict', 'package_state') and e.get('session') in (None, data['session'])]
    crit = None
    try:   # the criticality map: the team's declared map, CODEOWNERS when opted in, and the review's suggestions
        from .criticality import gate, resolve
        from .util import session_config
        crit = resolve(data, session_config(sdir))
        out["criticality"] = {**{k: crit[k] for k in ("declared", "discovered", "codeowners", "has_map", "warnings")},
                              "files": (lambda fs: fs[:3000])(sorted(crit["files"], key=lambda f: not f["protected"])),   # the locked ones are never the ones cut
                              "more": max(0, len(crit["files"]) - 3000), "gate": gate(crit)}
    except Exception as e:   # noqa: BLE001 - the page still renders, and the gate fails closed
        crit = {"error": f"{type(e).__name__}: {e}", "files": []}
        out["criticality"] = {"error": crit["error"], "files": [], "gate": {"count": 0, "protected": [], "prs": [], "error": crit["error"]}}
    out["routes"] = data.get("routes")
    try:   # the contracts the package changes, resolved against the diff (cockpit.system)
        from .system import resolve as resolve_system
        out["system"] = resolve_system(data)
    except Exception as e:   # noqa: BLE001
        out["system"] = None
        out["system_error"] = f"{type(e).__name__}: {e}"
    from .routes import sizes
    for pv, p in zip(out["prs"], data.get("prs", [])):
        pv["size"] = sizes(p)
    try:   # the Merge Risk style's estimate; a review never fails on it
        from .risk import assess
        out["risk"] = assess({**data, "impact": effective_impact}, crit)
        from .risk import report
        out["risk"]["report"] = report({**data, "impact": effective_impact, "title": out["title"]}, out["risk"])
    except Exception as e:   # noqa: BLE001
        out["risk"] = {"error": f"{type(e).__name__}: {e}"}
    out["prefs"] = _prefs(sdir)   # what memory learned about how this reviewer reads; the page applies it, visibly
    out["reviewers"] = (data.get("reviewers") or {}).get("suggested") or []
    out["reviewers_stale"] = bool((data.get("reviewers") or {}).get("stale"))
    out["reviewers_failed"] = int((data.get("reviewers") or {}).get("failed_calls") or 0)
    from .rollback import sensitive, uncovered
    files = sensitive(data.get("prs", []))   # all of them for coverage; the page lists at most MAX_FILES
    from .rollback import MAX_FILES
    left = uncovered(data.get("rollback"), files)
    gap = {f["path"] for f in left}
    shown = sorted(files, key=lambda f: f["path"] not in gap)[:MAX_FILES]   # the uncovered ones first, so they're never the ones cut
    out["rollback"] = {"plan": data.get("rollback"), "sensitive": shown, "more": max(0, len(files) - MAX_FILES), "uncovered": left}
    high = ((out.get("risk") or {}).get("level")) == "high"
    if "report" in (out.get("risk") or {}) and (data.get("rollback") or files or high):   # a missing plan is said, not left out
        from .risk import rollback_report
        out["risk"]["report"] += rollback_report(data.get("rollback"), left, high)
    if data.get("behavior"):
        bh, errs, _ = check_behavior(data["behavior"], data, resolve=True)
        out["behavior"] = bh if not errs else {**bh, "errors": errs}
    return out

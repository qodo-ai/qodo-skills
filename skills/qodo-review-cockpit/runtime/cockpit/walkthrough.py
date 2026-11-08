"""Execution walkthrough and Finding review: two Work Package pages from files the skill writes into the session.

  <session>/builder.json   every changed file and the methods, classes or sections it touches, each with a one-line
                           purpose (Tree), plus flows from a page load, API call or webhook through the calls (Flow)
  <session>/triage/        each PR's Qodo findings triage page (triage-<n>.html, its spec triage-<n>.json) and the
                           raw findings it was built from (findings-<n>.json)

`cockpit walkthrough --session <id> --builder FILE --triage-dir DIR` checks them and copies them in; package.html
shows the pages only when they're there.
"""
from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path

from .util import ROOT

OPEN = {"pending", "partial_implementation", "not_implemented", "focus_areas_edited", None, ""}
KINDS = {"user", "api", "webhook", "cron", "cli", "event", "queue", "deploy"}
CONTEXT = 2   # unchanged lines kept around each change in a method's code
MAX_LINES = 90


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:120]


# ---------- builder.json: check it and attach each method's changed lines ----------

def owner(methods: list[dict], k: str, o, n, anchor) -> dict | None:
    def inn(lo_key, hi_key, x):
        hits = [m for m in methods if x and m.get(lo_key) and m[lo_key] <= x <= m[hi_key]]
        return min(hits, key=lambda m: m[hi_key] - m[lo_key]) if hits else None
    if k == "-":
        return inn("ostart", "oend", o) or (inn("start", "end", anchor) if not any(m.get("ostart") for m in methods) else None)
    return inn("start", "end", n)


def method_code(f: dict, methods: list[dict]) -> None:
    rows = {id(m): [] for m in methods}
    module = next((m for m in methods if m["kind"] == "module"), None)
    for h in f.get("hunks") or []:
        lines = h.get("lines") or []
        for i, ln in enumerate(lines):   # [sign, old, new, text] and, on some, intra-line spans
            k, o, n = ln[0], ln[1], ln[2]
            anchor = n or next((x[2] for x in lines[i:] if x[2]), None)
            m = owner(methods, k, o, n, anchor) or (module if k != " " else None)
            if m is not None:
                rows[id(m)].append((h["id"], i, ln[:4]))
    for m in methods:
        got = rows[id(m)]
        keep = set()
        for j, (_, _, ln) in enumerate(got):
            if ln[0] != " ":
                keep.update(range(max(0, j - CONTEXT), j + CONTEXT + 1))
        blocks, cur, last = [], [], None
        for j in sorted(x for x in keep if x < len(got)):
            hid, i, ln = got[j]
            if last is not None and (hid != last[0] or i != last[1] + 1):
                blocks.append(cur)
                cur = []
            cur.append(ln)
            last = (hid, i)
        if cur:
            blocks.append(cur)
        out, total = [], 0
        for b in blocks:
            room = MAX_LINES - total
            if room <= 0:
                out[-1]["cut"] = out[-1].get("cut", 0) + len(b)
                continue
            out.append({"lines": b[:room], **({"cut": len(b) - room} if len(b) > room else {})})
            total += min(len(b), room)
        m["code"] = out


def check_builder(b: dict, data: dict, warn: list[str]) -> dict:
    prs = {p["key"]: p for p in data["prs"]}
    files = {(p["key"], f["path"]): f for p in data["prs"] for f in p["files"]}
    seen, uids = set(), set()

    def uid(s: str) -> str:
        u, n = s, 2
        while u in uids:
            u, n = f"{s}-{n}", n + 1
        uids.add(u)
        return u

    no_fp, no_mp, long = [], [], []
    for f in b.get("files") or []:
        key = (f.get("pr"), f.get("path"))
        if key not in files:
            warn.append(f"builder file {key[0]} {key[1]} isn't in the session's diff (rerun touched_methods.py --merge)")
            continue
        seen.add(key)
        f["uid"] = uid("bwf-" + slug(f"{f['pr']}-{f['path']}"))
        f.setdefault("role", files[key].get("role", "source"))
        f.setdefault("add", files[key].get("additions", 0))
        f.setdefault("del", files[key].get("deletions", 0))
        if not (f.get("purpose") or "").strip():
            no_fp.append(f["path"])
        for m in f.get("methods") or []:
            m["uid"] = uid("bwm-" + slug(f"{f['pr']}-{f['path']}-{m['qual']}"))
            p = (m.get("purpose") or "").strip()
            if not p:
                no_mp.append(f"{f['path']} {m['qual']}")
            for t in (p, f.get("purpose") or ""):
                if len(t) > 240 or "\n" in t:   # the guide allows ~220 when a line has to name things
                    long.append(t[:60])
        method_code(files[key], f.get("methods") or [])
    for key in files:
        if key not in seen:
            warn.append(f"{key[0]} {key[1]} changed but isn't in builder.json (rerun touched_methods.py --merge)")
    if no_fp:
        warn.append(f"{len(no_fp)} files have no purpose, e.g. " + ", ".join(no_fp[:4]))
    if no_mp:
        warn.append(f"{len(no_mp)} methods have no purpose, e.g. " + "; ".join(no_mp[:4]))
    for t in sorted(set(long))[:6]:
        warn.append(f"a purpose is longer than one line (keep it under ~220 characters): “{t}…”")

    by_path: dict[str, list[dict]] = {}
    for f in b.get("files") or []:
        if "uid" in f:
            by_path.setdefault(f["path"], []).append(f)
    repo_of = {k: p["repo"] for k, p in prs.items()}
    head_of = {}
    for p in data["prs"]:
        head_of.setdefault(p["repo"], p["head_sha"])
    flow_ids = set()
    for fl in b.get("flows") or []:
        fl["id"] = fl.get("id") or slug(fl.get("title") or "flow")
        if fl["id"] in flow_ids:
            warn.append(f"two flows share the id {fl['id']}")
        flow_ids.add(fl["id"])
        tr, name = fl.get("trigger") or {}, fl.get("title") or fl["id"]
        if tr.get("kind") not in KINDS:
            warn.append(f"flow “{name}”: trigger.kind must be one of {', '.join(sorted(KINDS))}")
        if not tr.get("label") or not (fl.get("outcome") or {}).get("label"):
            warn.append(f"flow “{name}”: needs trigger.label and outcome.label")
        n, depth = 0, 0
        for s in fl.get("steps") or []:
            s["flow"] = fl["id"]
            if s.get("boundary"):
                continue
            n += 1
            s["n"] = n
            if not s.get("name"):
                warn.append(f"flow “{name}” step {n}: no name")
            if s.get("pr") and s["pr"] not in prs:
                warn.append(f"flow “{name}” step {n}: pr {s['pr']} isn't in this review")
            for r in s.get("state") or []:
                if r.get("where") not in STATE_WHERE or not r.get("target") or "value" not in r:
                    warn.append(f"flow “{name}” step {n}: a state row needs where ({', '.join(STATE_WHERE)}), target and value: {json.dumps(r)[:120]}")
            if (s.get("depth") or 0) > depth + 1:
                warn.append(f"flow “{name}” step {n}: depth jumps from {depth} to {s['depth']}; a call goes one level deeper at a time")
            depth = s.get("depth") or 0
            claimed = s.pop("in_diff", None)
            cands = [f for f in by_path.get(s.get("path") or "", []) if (not s.get("pr") or f["pr"] == s["pr"]) and (not s.get("repo") or repo_of[f["pr"]] == s["repo"])]
            hit = None
            for f in cands:
                nm = s.get("name") or ""
                hit = next(((f, m) for m in f["methods"] if m["qual"] == nm), None) or \
                      next(((f, m) for m in f["methods"] if m["qual"].endswith("." + nm) or nm.endswith("." + m["qual"]) or m["name"] == nm), None)
                if hit:
                    break
            s["file_changed"] = bool(cands)
            if hit:
                f, m = hit
                s.update(in_diff=True, ref=m["uid"], pr=f["pr"], repo=repo_of[f["pr"]], change=m.get("change"), line=s.get("line") or m.get("start"))
            else:
                s["in_diff"] = False
                if claimed:
                    warn.append(f"flow “{name}” step {n} ({s.get('name')}): marked in_diff but no touched method matches; it shows as existing code")
                if cands:
                    s.setdefault("pr", cands[0]["pr"])
            repo = s.get("repo") or (repo_of.get(s["pr"]) if s.get("pr") else None)
            if repo:
                s["repo"] = repo
            if not s.get("url") and repo and s.get("path"):
                ref = s.get("ref_sha") or (prs[s["pr"]]["head_sha"] if s.get("pr") in prs else head_of.get(repo, "HEAD"))
                s["url"] = f"https://github.com/{repo}/blob/{ref}/{s['path']}" + (f"#L{s['line']}" if s.get("line") else "")
        handoffs(fl, {m["uid"]: m for f in b.get("files") or [] if "uid" in f for m in f["methods"]}, warn)
        if n and not any(s.get("state") for s in fl.get("steps") or []):
            warn.append(f"flow “{name}” sets no state: add `state` rows where a step changes local state or the database")
        if not n:
            warn.append(f"flow “{name}” has no steps")
        elif not any(s.get("in_diff") for s in fl.get("steps") or []):
            warn.append(f"flow “{name}” runs through no changed method: is it part of this change?")
    if not b.get("flows"):
        warn.append("no flows: Flow mode will be empty")
    return b


STATE_WHERE = {"local": "Local state", "app": "App state", "url": "URL", "browser": "Browser storage", "request": "Request context", "cache": "Cache", "db": "Database"}
# each handoff reads as a verb: what the step before does to reach the next one
VIA = {"click": "User clicks", "api": "Calls API", "event": "Emits event", "navigate": "User navigates to", "call": "Calls function", "render": "Renders", "data": "Queries database", "cache": "Reads cache"}
LEADS = {"click", "api", "event", "navigate"}   # a boundary of these kinds is how the next step is reached; data and cache happen beside it
VIA_RX = [("api", r"\bhttps?\b|\bapi\b|\bgit (provider|host)\b|\bgithub\b|\bgitlab\b|\bbitbucket\b|\bendpoint\b|\bgraphql\b|\bfetch\b"),
          ("event", r"\bevents?\b|\bqueue\b|\bwebhooks?\b|\bpub/?sub\b|\bkafka\b|\bsqs\b|\bemits?\b"),
          ("navigate", r"\bnavigat|\brouter\b|\bredirect|\burl replace\b"),
          ("cache", r"\bcache\b|\bredis\b"),
          ("data", r"\bdb\b|\bdatabase\b|\bpostgres\b|\btables?\b|\bsql\b|\bfirestore\b|\bclickhouse\b|\bjsonb\b"),
          ("click", r"\bclicks?\b|\btoggles?\b|\bselects?\b")]
FROM_TRIGGER = {"user": ("click", "User clicks"), "api": ("api", "Calls API"), "webhook": ("event", "Receives webhook"), "event": ("event", "Emits event"),
                "queue": ("event", "Takes queue message"), "cron": ("event", "Runs on schedule"), "cli": ("call", "Runs command"), "deploy": ("event", "Deploys")}


def via_label(kind: str, text: str = "") -> str:
    t = text.lower()
    if kind == "api" and "response" in t:
        return "Returns response"
    if kind == "data":
        return "Writes database" if re.search(r"\bwrites?\b|\binsert|\bupdate|\bupsert", t) else "Reads database" if re.search(r"\breads?\b|\bselect\b|\bquer", t) else "Queries database"
    return VIA[kind]


def handoffs(fl: dict, methods: dict, warn: list[str]) -> None:
    """How each step is reached, for the thin row above it: the boundary that leads to it, else the trigger, else the call."""
    steps, pending, tk = fl.get("steps") or [], None, (fl.get("trigger") or {}).get("kind")
    for i, s in enumerate(steps):
        if s.get("boundary"):
            k = s.get("via") if s.get("via") in VIA else next((k for k, rx in VIA_RX if re.search(rx, s["boundary"], re.I)), "event")
            s.update(kind=k, label=via_label(k, s["boundary"]), merged=False)
            pending = s if k in LEADS else None
            continue
        m, nm = methods.get(s.get("ref") or ""), s.get("name") or ""
        s["okind"] = m["kind"] if m else ("method" if "." in nm else "hook" if re.match(r"use[A-Z0-9]", nm) else
                                          "component" if re.match(r"[A-Z]", nm) and re.search(r"\.[jt]sx$", s.get("path") or "") else "function")
        if s.get("via") in VIA:   # the writer said how it's reached
            k = s["via"]
            s["via"] = {"kind": k, "label": via_label(k, s.get("via_detail") or ""), "detail": s.get("via_detail") or ""}
        elif pending:   # the HTTP call, event or navigation just above is the handoff
            pending["merged"] = True
            s["via"] = {"kind": pending["kind"], "label": pending["label"], "detail": pending["boundary"]}
        elif s.get("n") == 1:
            k, lab = FROM_TRIGGER.get(tk, ("event", "Event"))
            if tk == "user" and re.search(r"\b(opens?|loads?|visits?|navigates?|goes to|lands on)\b", (fl.get("trigger") or {}).get("label") or "", re.I):
                k, lab = "navigate", "Loads page"
            s["via"] = {"kind": k, "label": lab, "detail": ""}
        else:
            d = s.get("depth") or 0
            caller = next((x for x in reversed(steps[:i]) if not x.get("boundary") and (x.get("depth") or 0) == d - 1), None) if d else None
            mk = s["okind"]
            k = "render" if mk == "component" else "call"
            lab = "Renders" if k == "render" else "Calls method" if mk in ("method", "class") or "." in (s.get("name") or "") else "Calls function"
            s["via"] = {"kind": k, "label": lab, "detail": f"{'rendered by' if k == 'render' else 'from'} `{caller['name']}`" if caller and caller.get("name") else ""}
        pending = None


# ---------- triage pages ----------

KEEP = ("id", "title", "description", "action_level", "attribution_status", "file_path", "start_line", "end_line", "finding_source", "category")   # what a card needs of each Qodo finding


def load_triage(tdir: Path, data: dict, warn: list[str]) -> list[dict]:
    out = []
    for p in data["prs"]:
        html, snap = tdir / f"triage-{p['number']}.html", tdir / f"findings-{p['number']}.json"
        if not html.is_file():   # nothing to triage: Qodo never reviewed it, or every finding is closed
            raw = json.loads(snap.read_text()) if snap.is_file() else None
            if raw is None:
                warn.append(f"no triage page for {p['key']} ({html.name}) and no {snap.name}")
                continue
            left = [x for x in raw.get("findings") or [] if x.get("attribution_status") in OPEN]
            if left:
                warn.append(f"{p['key']} has {len(left)} open findings but no {html.name}")
                continue
            rs = raw.get("review_session")
            out.append({"pr": p["key"], "html": "", "counts": {"open": 0, "reviewed": bool(rs), "closed": len(raw.get("findings") or [])},
                        **({"url": p.get("url") or "", "sha": str((rs or {}).get("commit_sha") or "")[:9], "review_url": "", "targets": [],   # every finding closed: listed under Show closed findings
                            "snapshot": {"review": rs, "findings": [{k: f.get(k) for k in KEEP} for f in raw.get("findings") or []]}} if rs and raw.get("findings") else {})})
            continue
        spec = json.loads((tdir / f"triage-{p['number']}.json").read_text()) if (tdir / f"triage-{p['number']}.json").is_file() else {}
        repo = (spec.get("pr") or {}).get("repo")
        if repo and repo != p["repo"]:
            warn.append(f"{html.name} is for {repo}, not {p['repo']}: skipped")
            continue
        raw = json.loads(snap.read_text()) if snap.is_file() else {}
        live = {x["id"]: x.get("attribution_status") for x in raw.get("findings") or []}
        mine = [x for x in spec.get("findings") or [] if live.get(x.get("id"), None) in OPEN or x.get("id") not in live]
        new = [i for i, st in live.items() if st in OPEN and i not in {x.get("id") for x in spec.get("findings") or []}]
        v = Counter(x.get("verdict") for x in mine)
        fix = [x for x in mine if x.get("verdict") == "fix"]
        counts = {"open": len(mine) + len(new), "fix": v["fix"], "skip": v["skip"], "call": v["call"], "new": len(new),
                  "add": sum((x.get("size") or {}).get("add", 0) for x in fix), "rem": sum((x.get("size") or {}).get("rem", 0) for x in fix),
                  "reviewed": bool(raw.get("review_session")) if snap.is_file() else True}
        page = html.read_text()
        out.append({"pr": p["key"], "counts": counts, **triage_page(page, spec, raw, html.name, warn)})
    return out


def triage_page(page: str, spec: dict, raw: dict | None = None, name: str = "", warn: list | None = None) -> dict:
    """What Finding review draws from a built triage page: the findings as its own script holds them, the code excerpts
    from its cards and the analysis as written (its markup kept). Qodo's statuses come from the current findings file
    when there is one, so the cards agree with the counts; the page's own snapshot only when there isn't."""
    import html as H
    def const(name):
        m = re.search(rf"^const {name} = (.*);$", page, re.M)
        try:
            return json.loads(m.group(1)) if m else None
        except ValueError:
            return None
    by = {str(f.get("id")): f for f in spec.get("findings") or []}
    cards = re.split(r'(?=<details class="card" id="f)', page)
    def code(num):
        card = next((c for c in cards if c.startswith(f'<details class="card" id="f{num}"')), "")
        out = []
        for fig in re.findall(r'<figure class="code">(.*?)</figure>', card, re.S):
            href = re.search(r'<a href="([^"]+)"', fig)
            path = re.search(r'<span class="path">(.*?)</span>', fig)
            rows = [{"n": int(n), "mark": mark.strip(), "text": H.unescape(tx).replace("\u200b", ""),
                     "note": H.unescape(re.sub(r"<[^>]+>", "", (re.search(r'<span class="bulb-note" hidden>(.*?)</span></button>', gut, re.S) or [None, ""])[1]))}
                    for mark, gut, n, tx in re.findall(r'<div class="ln ([^"]*)"><span class="gut">(.*?)</span><span class="no">(\d+)</span><span class="tx">(.*?)</span></div>', fig, re.S)]
            url = H.unescape(href.group(1)) if href else ""
            out.append({"url": url if url.startswith("https://") else "", "path": H.unescape(path.group(1)) if path else "", "lines": rows})   # a code link only over https
        return out
    found = const("TARGETS")
    if not isinstance(found, list):   # the page's script couldn't be read: say so, and build the cards from the spec instead
        if warn is not None:
            warn.append(f"{name}: couldn't read its findings; Finding review uses the triage spec, without code excerpts")
        sev = {"action_required": "High", "remediation_recommended": "Medium", "informational": "Low"}
        found = [{"num": str(i + 1), "id": f.get("id"), "title": f.get("title") or "", "sev": sev.get(f.get("action_level"), "Low"), "verdict": f.get("verdict") or "",
                  "rec": re.sub(r"<[^>]+>", "", f.get("recommendation") or ""), "add": (f.get("size") or {}).get("add", 0), "rem": (f.get("size") or {}).get("rem", 0),
                  "reason": f.get("dismiss_reason") or "intentional", "kind": f.get("kind") or "", "badges": [],
                  "locs": [f"{x.get('path')}, lines {x.get('start')}–{x.get('end')}" for x in f.get("excerpts") or [] if x.get("path")]} for i, f in enumerate(spec.get("findings") or [])]
    targets = [{**t, "impact_html": (by.get(str(t.get("id"))) or {}).get("impact") or "", "why_html": (by.get(str(t.get("id"))) or {}).get("why") or "",
                "note": ((by.get(str(t.get("id"))) or {}).get("size") or {}).get("note") or "", "code": code(t.get("num"))} for t in found]
    snap = raw if raw and raw.get("findings") is not None else (const("SNAPSHOT") or {})   # the current findings file wins over the page's snapshot
    return {"url": const("PR_URL") or (spec.get("pr") or {}).get("url") or "", "sha": const("SHA") or "", "review_url": (spec.get("pr") or {}).get("review_url") or "",
            "targets": targets, "snapshot": {"review": snap.get("review") or {}, "findings": [{k: f.get(k) for k in KEEP} for f in snap.get("findings") or []]}}



def check_files(sdir: Path, data: dict, builder: Path | None = None, triage_dir: Path | None = None) -> tuple[dict | None, list[dict], list[str]]:
    """The checked execution walkthrough and triage pages, from the given files or the session's own, with warnings."""
    warn: list[str] = []
    builder = builder or sdir / "builder.json"
    triage_dir = triage_dir or sdir / "triage"
    b = None
    if builder.is_file():
        raw = json.loads(builder.read_text())
        if not isinstance(raw, dict) or not isinstance(raw.get("files"), list) or not isinstance(raw.get("flows", []), list):
            warn.append(f"{builder.name} needs `files` (and optionally `flows`) as lists: skipped")
        else:
            b = check_builder(raw, data, warn)
    triage = load_triage(triage_dir, data, warn) if triage_dir.is_dir() else []
    return b, triage, warn


def page_data(sdir: Path, data: dict) -> dict | None:
    """What walkthrough.js reads, or None when the session has neither page."""
    b, triage, _ = check_files(sdir, data)
    if not b and not triage:
        return None
    return {"builder": b, "triage": triage}


def attach(sdir: Path, builder: Path | None, triage_dir: Path | None) -> None:
    """Copy the skill's files into the session, so serve and export show the two pages."""
    if builder:
        shutil.copyfile(builder, sdir / "builder.json")
    if triage_dir:
        dest = sdir / "triage"
        dest.mkdir(exist_ok=True)
        for p in triage_dir.glob("*"):
            if p.is_file() and re.fullmatch(r"(triage|findings)-\d+\.(html|json)", p.name):
                shutil.copyfile(p, dest / p.name)

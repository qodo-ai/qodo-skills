"""The system section: the contracts a work package changes, after Shlomo Dalezman's contract-first review (Oct 20).

The skill writes the contracts first (skill/references/contracts.md): every endpoint, event, table, type, flag and
budget the package changes, who defines it, who uses it (unchanged code too), before -> after, door and risk. This
module checks every code ref against the diff and derives the rest: who touches each contract, the reading tiers,
other work on the same code, the merge order the contracts imply, and how much of the change the contracts cite.

Input (enrich `system`):
  {summary, components: [{id, name, role, kind, repo?, prs?, group?, risk?, why?}],
   contracts: [{id, name, kind, change, from, to: [ids], summary, before?, after?, carries?, reaches?, undo?, why?,
                compat?, door?, risk?, prs: [keys], defined: [ref], used: [ref], tests: [ref], depends?: [ids],
                intent?: [{text, status, source}], decision?: {ask, options, lede?}, open?, mismatch?, seam?, findings?}],
   flows: [{id, title, question?, steps: [{text, contract? | component?}]}]}
  A ref is changed code {pr, path, from, to, side?, note?}, code a PR doesn't change {repo, path, from, to, ref?, note?},
  or something outside the code {outside: true, component?, note}.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import time
from urllib.parse import quote

KINDS = ("endpoint", "webhook", "event", "queue", "table", "schema", "type", "flag", "config", "cli", "file", "budget", "capability")
CHANGES = ("added", "changed", "removed", "missing", "unchanged")
COMPONENT_KINDS = ("service", "library", "store", "queue", "external", "infra", "ui")
RISKS = ("low", "medium", "high")
MAX_REF_LINES = 60     # code shown per ref
MAX_EXCERPT = 40       # lines kept from unchanged code


def _rank(r) -> int:
    return RISKS.index(r) if r in RISKS else -1


def _s(v, n: int = 600) -> str:
    return str(v or "").strip()[:n]


MAX_FETCHES = 40       # unchanged files read per enrich
FETCH_BUDGET = 90      # seconds for all of them
_files: dict = {}


def _excerpt(repo: str, path: str, ref: str, lo: int, hi: int, budget: dict) -> tuple[str, int] | None:
    """Lines lo..hi of a file at a ref, read-only through gh, each file read once; None when it can't be read."""
    from .product import enabled
    if enabled():
        from .adapters.managed import Client, ReadBudget, ReadError
        cache = budget.setdefault('_managed_excerpts', {})
        identities = budget.setdefault('_managed_identities', {})
        identity_key = identities.get(repo) or {}
        key = (identity_key.get('provider'), identity_key.get('provider_host'), identity_key.get('repository_url') or repo, path, ref)
        for start, end, content, evidence in cache.get(key, []):
            if start <= lo and hi <= end:
                lines = content.splitlines()[lo-start:hi-start+1]
                return '\n'.join(lines[:MAX_EXCERPT]), 0, {**evidence, 'selection_from':lo, 'selection_to':hi, 'cache_hit':True}
        left = budget['until'] - time.monotonic()
        if budget['n'] >= MAX_FETCHES or left <= 0:
            return None
        client = budget.get('_managed_client')
        if client is None:
            client = budget['_managed_client'] = Client(budget=ReadBudget(max_calls=MAX_FETCHES*2, seconds=left))
        budget['n'] += 1
        try:
            if repo not in identities:
                identities[repo] = client.identity(repo)
            identity = identities[repo]
            key = (identity.get('provider'), identity.get('provider_host'), identity.get('repository_url') or repo, path, ref)
            result = client.read('codebase', 'read-file', repo=identity.get('repository_url') or identity['repo'], path=path, ref=ref, start_line=max(1, lo), limit_lines=min(MAX_EXCERPT, hi-lo+1))
        except ReadError:
            return None
        evidence = {k: result.get(k) for k in ('resolved_ref', 'last_fetched_at', 'committed_at', 'commit_date', 'qar_operation_result_truncated', 'next_read_cursor', 'truncated', 'content_truncated_upstream', 'next_start_line', 'start_line', 'total_lines')}
        evidence.update(identity=identity, path=path, requested_ref=ref, selection_from=lo, selection_to=hi, source_url=result.get('url') or result.get('html_url'))
        immutable = bool(re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', ref or ''))
        if immutable and str(result.get('resolved_ref') or '').lower() != ref.lower():
            return None, None, {**evidence, 'status':'unavailable', 'complete':False, 'reason':'returned commit does not match requested immutable ref'}
        text = result.get('content')
        if not isinstance(text, str):
            return None, None, {**evidence, 'status':'unavailable', 'complete':False, 'reason':'source content unavailable'}
        count = len(text.splitlines())
        truncated = bool(result.get('truncated') or result.get('qar_operation_result_truncated') or result.get('next_read_cursor') or result.get('content_truncated_upstream') or result.get('next_start_line'))
        complete = immutable and not truncated and count >= hi-lo+1
        evidence.update(returned_lines=count, status='complete' if complete else 'partial' if truncated else 'unverified',
                        complete=True if complete else False if truncated else None)
        # A short or mutable/stale read cannot prove absence, a zero cut or a complete excerpt.
        if complete:
            cache.setdefault(key, []).append((max(1, lo), max(1, lo)+count-1, text, evidence))
        return text, 0 if complete else None, evidence
    key = (repo, path, ref)
    if key not in _files:
        left = budget["until"] - time.monotonic()
        if budget["n"] >= MAX_FETCHES or left <= 1:
            return None
        budget["n"] += 1
        text = None
        try:
            r = subprocess.run(["gh", "api", f"repos/{quote(repo, safe='/')}/contents/{quote(path)}?ref={quote(ref or 'HEAD', safe='')}"],
                               capture_output=True, text=True, timeout=min(20, left))
            doc = json.loads(r.stdout) if r.returncode == 0 else None
            text = base64.b64decode(doc["content"]).decode(errors="replace") if isinstance(doc, dict) and doc.get("content") else None
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
            text = None
        if text is None:   # a failed read is tried again next time, not remembered
            return None
        _files[key] = text
    text = _files[key]
    lines = text.splitlines()[max(0, lo - 1):hi]
    return "\n".join(lines[:MAX_EXCERPT]), max(0, len(lines) - MAX_EXCERPT)


def _ref(raw, prs: dict, where: str, warn: list, fetch: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        warn.append(f"{where}: a ref is an object"); return None
    if raw.get("outside"):
        return {"outside": True, "component": _s(raw.get("component"), 60) or None, "note": _s(raw.get("note"), 400)}
    path = _s(raw.get("path"), 300)
    lo = raw.get("from") if isinstance(raw.get("from"), int) else None
    hi = raw.get("to") if isinstance(raw.get("to"), int) else lo
    if not path:
        warn.append(f"{where}: a ref needs a path"); return None
    if lo is not None and hi is not None and hi < lo:
        lo, hi = hi, lo
    out = {"path": path, "from": lo, "to": hi, "side": "old" if raw.get("side") == "old" else "new", "note": _s(raw.get("note"), 400)}
    if raw.get("pr"):
        p = prs.get(raw["pr"])
        if not p:
            warn.append(f"{where}: unknown PR {raw['pr']}"); return None
        if path not in {f["path"] for f in p.get("files", [])}:
            warn.append(f"{where}: {path} isn't in {raw['pr']}'s diff; cite it as unchanged code ({{repo, path, from, to}})"); return None
        out["pr"] = raw["pr"]
        if lo is None:
            warn.append(f"{where}: {path} cites no lines (from/to); it shows as the file only and proves no change")
        return out
    repo = _s(raw.get("repo"), 120)
    if not repo:
        warn.append(f"{where}: {path} needs a pr (changed code) or a repo (unchanged code)"); return None
    from .product import enabled
    product = enabled()
    def matches_repo(p):
        identity = p.get('identity') or {}
        same_repo = p['repo'].lower() == repo.lower() if not product or identity.get('provider') == 'github' else p['repo'] == repo
        return same_repo and (not raw.get('provider_host') or identity.get('provider_host') == raw['provider_host'])
    matches = [p for p in prs.values() if matches_repo(p)]
    identities = {((p.get('identity') or {}).get('provider_host'), (p.get('identity') or {}).get('provider'), p['repo']) for p in matches}
    if product and len(identities) > 1:
        out.update(repo=repo, source_evidence={'status':'unavailable', 'complete':False, 'reason':'ambiguous provider repository'})
        warn.append(f'{where}: source repository identity is ambiguous; no source read')
        return out
    explicit = _s(raw.get('ref'), 80)
    immutable = bool(re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', explicit))
    if product and not immutable:
        candidates = set()
        for match in matches:
            if not explicit or explicit == 'HEAD' or explicit == match.get('base'):
                candidates.add(match.get('base_sha'))
            elif explicit == match.get('head'):
                candidates.add(match.get('head_sha'))
            else:
                candidates.add(None)
        if len(candidates) != 1 or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', value) for value in candidates):
            out.update(repo=repo, ref=explicit or 'HEAD', source_evidence={'status':'unavailable', 'complete':False, 'reason':'source revision is ambiguous; cite an explicit immutable SHA'})
            warn.append(f'{where}: no unique immutable source revision; no source read')
            return out
    pr = matches[0] if matches else {}
    base = pr.get('base')
    ref = _s(raw.get('ref'), 80) or base or 'HEAD'
    if product:
        if ref in ('HEAD', base):
            ref = pr.get('base_sha') or ref
        elif ref == pr.get('head'):
            ref = pr.get('head_sha') or ref
        if fetch is not None and pr.get('identity'):
            fetch.setdefault('_managed_identities', {})[repo] = pr['identity']
    out.update(repo=repo, ref=ref)
    if raw.get('excerpt') and not product:
        out['excerpt'] = str(raw['excerpt'])[:4000]
        out['excerpt_cut'] = int(raw.get('excerpt_cut') or 0)
    elif fetch is not None and lo:
        got = _excerpt(repo, path, out['ref'], lo, hi or lo, fetch)
        if got and product:
            text, cut, ev = got
            out.update(excerpt_cut=cut, source_evidence=ev)
            if text is not None:
                out['excerpt'] = text
            if ev.get('complete') is not True:
                warn.append(f'{where}: source excerpt {ev.get("status")}; freshness/range completeness is not proven')
        elif got:
            out['excerpt'], out['excerpt_cut'] = got
        else:
            if product:
                out['source_evidence'] = {'status':'unavailable', 'complete':False, 'requested_ref':ref}
            warn.append(f"{where}: couldn't read {repo}:{path} at {out['ref']} (the page shows the path only)")
    elif product and raw.get('excerpt'):
        out.update(excerpt=str(raw['excerpt'])[:4000], excerpt_cut=None,
                   source_evidence={'status':'unverified', 'complete':None, 'origin':'authored', 'reason':'source must be re-observed through managed reads'})
    return out


def normalize(raw, data: dict, fetch: bool = True) -> tuple[dict | None, list[str]]:
    from .product import scope
    with scope(data):
        return _normalize(raw, data, fetch)


def _normalize(raw, data: dict, fetch: bool = True) -> tuple[dict | None, list[str]]:
    """The skill's system section, checked: components, contracts with their refs, flows."""
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["system: an object {summary, components, contracts, flows}"]
    prs = {p["key"]: p for p in data.get("prs", [])}
    warn: list[str] = []
    budget = {"n": 0, "until": time.monotonic() + FETCH_BUDGET} if fetch else None   # one deadline for the whole section
    old = {(r.get("repo"), r.get("path"), r.get("from"), r.get("to")): r for c in ((data.get("system") or {}).get("contracts") or [])
           for k in ("defined", "used", "tests") for r in c.get(k) or [] if r.get("excerpt")}   # a re-run keeps what it already read
    comps = []
    for i, c in enumerate(raw.get("components") or [], 1):
        if not isinstance(c, dict) or not c.get("id") or not c.get("name"):
            warn.append(f"system.components {i}: needs id and name; left out"); continue
        kind = c.get("kind") if c.get("kind") in COMPONENT_KINDS else "service"
        if any(x["id"] == _s(c["id"], 60) for x in comps):
            warn.append(f"system.components {i}: id {c['id']} used twice; left out"); continue
        comps.append({"id": _s(c["id"], 60), "name": _s(c["name"], 80), "role": _s(c.get("role"), 300), "kind": kind,
                      **({"repo": _s(c["repo"], 120)} if c.get("repo") else {}), **({"group": _s(c["group"], 60)} if c.get("group") else {}),
                      "prs": [k for k in (c.get("prs") or []) if k in prs],
                      **({"risk": c["risk"]} if c.get("risk") in RISKS else {}), **({"why": _s(c["why"], 300)} if c.get("why") else {})})
    ids = {c["id"] for c in comps}
    cons, seen = [], set()
    for i, c in enumerate(raw.get("contracts") or [], 1):
        if not isinstance(c, dict) or not c.get("id") or not c.get("name"):
            warn.append(f"system.contracts {i}: needs id and name; left out"); continue
        cid = re.sub(r"\s+", "-", _s(c["id"], 60))   # ids join with spaces on the map: none inside one
        if cid in seen:
            warn.append(f"system.contracts {cid}: id used twice; left out"); continue
        seen.add(cid)
        where = f"system.{cid}"
        change = c.get("change") if c.get("change") in CHANGES else "changed"
        kind = c.get("kind") if c.get("kind") in KINDS else "type"
        if c.get("kind") not in KINDS:
            warn.append(f"{where}: kind is one of {', '.join(KINDS)}; read as type")
        frm = c.get("from") if c.get("from") in ids else None
        to = [t for t in (c.get("to") or []) if t in ids]
        if c.get("from") and not frm:
            warn.append(f"{where}: from names no component ({c.get('from')})")
        if len(to) < len(c.get("to") or []):
            warn.append(f"{where}: to names unknown components")
        def seed(x):
            from .product import enabled
            if enabled(data):
                return x  # re-observe managed refs on enrich; never seed a new base with old content
            o = old.get((x.get("repo"), x.get("path"), x.get("from"), x.get("to"))) if isinstance(x, dict) and not x.get("excerpt") else None
            return {**x, "excerpt": o["excerpt"], "excerpt_cut": o.get("excerpt_cut", 0)} if o else x
        refs = {k: [r for j, x in enumerate(c.get(k) or []) if (r := _ref(seed(x), prs, f"{where}.{k}[{j}]", warn, budget))] for k in ("defined", "used", "tests")}
        out = {"id": cid, "name": _s(c["name"], 200), "kind": kind, "change": change, "from": frm, "to": to,   # noqa: E501
               "summary": _s(c.get("summary"), 900), "prs": [k for k in (c.get("prs") or []) if k in prs], **refs,
               "findings": [str(x) for x in (c.get("findings") or [])][:12],
               "depends": [re.sub(r"\s+", "-", str(x)) for x in (c.get("depends") or [])][:12]}
        for k, n in (("before", 900), ("after", 1400), ("carries", 400), ("reaches", 300), ("undo", 400), ("why", 1200), ("open", 900), ("mismatch", 900)):
            if c.get(k):
                out[k] = _s(c[k], n)
        for k, allowed in (("compat", ("additive", "breaking", "internal")), ("door", ("one-way", "two-way")), ("risk", RISKS)):
            if c.get(k) in allowed:
                out[k] = c[k]
        if isinstance(c.get("intent"), list):
            out["intent"] = [{"text": _s(x.get("text"), 300), "status": x.get("status") if x.get("status") in ("done", "partial", "missing") else "partial",
                              "source": _s(x.get("source"), 200)} for x in c["intent"] if isinstance(x, dict) and x.get("text")][:6]
        if isinstance(c.get("decision"), dict) and c["decision"].get("ask") and c["decision"].get("options"):
            out["decision"] = {"ask": _s(c["decision"]["ask"], 300), "options": [_s(o, 200) for o in c["decision"]["options"]][:5],
                               **({"lede": _s(c["decision"]["lede"], 400)} if c["decision"].get("lede") else {})}
        if isinstance(c.get("collision"), dict) and c["collision"].get("summary"):   # other work the skill found by reading, not by overlap
            k = c["collision"]
            out["collision"] = {"with": _s(k.get("with"), 120), "url": _s(k.get("url"), 300), "title": _s(k.get("title"), 200), "summary": _s(k.get("summary"), 600)}
        if isinstance(c.get("seam"), list):
            out["seam"] = [k for k in c["seam"] if k in prs]
        if change not in ("missing", "unchanged") and not refs["defined"] and not refs["used"]:
            warn.append(f"{where}: cites no code; say where it is defined or used")
        if not out["prs"] and change not in ("missing", "unchanged"):
            warn.append(f"{where}: names no PR that changes it (prs)")
        cons.append(out)
    known = {c["id"] for c in cons}
    for c in cons:
        bad = [d for d in c["depends"] if d not in known]
        if bad:
            warn.append(f"system.{c['id']}.depends: unknown contracts {', '.join(bad)}")
        c["depends"] = [d for d in c["depends"] if d in known]
    flows = []
    for i, f in enumerate(raw.get("flows") or [], 1):
        if not isinstance(f, dict) or not f.get("steps"):
            continue
        steps = []
        for s in f["steps"]:
            if not isinstance(s, dict) or not s.get("text"):
                continue
            st = {"text": _s(s["text"], 500)}
            sc = re.sub(r"\s+", "-", str(s.get("contract") or ""))
            if sc in known:
                st["contract"] = sc
            elif s.get("contract"):
                warn.append(f"system.flows {i}: step names unknown contract {s['contract']}")
            if s.get("component") in ids:
                st["component"] = s["component"]
            steps.append(st)
        if not steps:
            warn.append(f"system.flows {i}: no valid steps; left out"); continue
        flows.append({"id": _s(f.get("id") or f"f{i}", 40), "title": _s(f.get("title"), 120), **({"question": _s(f["question"], 200)} if f.get("question") else {}), "steps": steps})
    return {"summary": _s(raw.get("summary"), 1500), "components": comps, "contracts": cons, "flows": flows,
            "superseded": [str(k) for k in raw.get("superseded") or []][:20]}, warn


def _changed_lines(f: dict, side: str) -> set[int]:
    idx = 2 if side != "old" else 1
    out = set()
    for h in f.get("hunks", []):
        for ln in h.get("lines", []):
            if ln[0] == ("+" if side != "old" else "-") and ln[idx]:
                out.add(ln[idx])
    return out


def resolve(data: dict) -> dict | None:
    """The page's system: refs resolved against the diff, and everything the engine derives from the contracts."""
    sysd = data.get("system")
    if not sysd:
        return None
    from .behavior import window
    prs = {p["key"]: p for p in data.get("prs", [])}
    files = {(k, f["path"]): f for k, p in prs.items() for f in p.get("files", [])}
    changed = {kp: {"new": _changed_lines(f, "new"), "old": _changed_lines(f, "old")} for kp, f in files.items()}
    cited: dict = {}
    findings = {f["id"]: f for p in data.get("prs", []) for f in p.get("findings", [])}
    import re
    gone = {f"{m.group(1)}#{m.group(2)}".lower() for x in ((data.get("context") or {}).get("sources") or [])
            if "supersed" in f"{x.get('title', '')} {x.get('summary', '')}".lower()
            for m in [re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", str(x.get("url") or ""))] if m}   # earlier versions of this same work
    gone |= {str(k).lower() for k in sysd.get("superseded") or []}
    others = [h for h in (data.get("overlaps") or {}).get("external") or [] if str(h.get("key") or "").lower() not in gone]
    warn: list[str] = []

    def res(r: dict) -> dict:
        r = dict(r)
        if r.get("pr"):
            kp = (r["pr"], r["path"]); f = files.get(kp)
            r["diff"] = bool(f)
            ch = changed.get(kp, {}).get(r["side"], set())
            lo, hi = r.get("from"), r.get("to")
            hit = sorted(x for x in ch if lo and lo <= x <= (hi or lo)) if lo else sorted(ch)
            r["changed"] = bool(hit)
            r["at"] = (hit[-1] if hit else hi) if r["side"] != "old" else None
            if f and lo:
                w = window(f, r["side"], lo, hi or lo)
                r["lines"], r["cut"] = w[:MAX_REF_LINES], max(0, len(w) - MAX_REF_LINES)
                cited.setdefault((*kp, r["side"]), set()).update(hit)   # per side: the total counts additions and deletions apart
            elif f:   # a ref without lines: the file, not a claim about any line in it
                r["lines"], r["cut"], r["changed"], r["at"] = [], 0, False, None
        else:
            r["diff"] = r["changed"] = False
            from .product import enabled
            if enabled(data) and r.get('excerpt') and not r.get('source_evidence'):
                r['source_evidence'] = {'status':'unverified', 'complete':None, 'origin':'legacy', 'reason':'saved excerpt has no recorded source provenance'}
                r['excerpt_cut'] = None
        return r

    comp_repo = {n["id"]: n.get("repo") for n in sysd["components"]}
    cons = []
    for c in sysd["contracts"]:
        c = {**c, **{k: [res(r) for r in c.get(k) or []] for k in ("defined", "used", "tests")}}
        refs = c["defined"] + c["used"] + c["tests"]
        c["touched_by"] = list(dict.fromkeys(c["prs"] + [r["pr"] for r in refs if r.get("diff")]))   # the owners first, then who meets it, in the order the refs cite them
        paths = {(r["pr"], r["path"]) for r in refs if r.get("diff")}
        hs, keys = [], {}
        for h in others:   # other PRs on the same code; this machine's other reviews and agent sessions are not other work
            if h.get("source") in ("session", "agent") or h.get("closeness") not in ("lines", "function"):
                continue
            mine = [r for r in refs if r.get("diff") and r.get("pr") == h.get("for") and r["path"] == h.get("path")]
            if mine:
                def overlaps(r):   # the overlap's lines on the ref's own side
                    lo, hi = (h.get("ours" if r["side"] == "old" else "ours_new") or [None, None])[:2]
                    return lo is not None and r.get("from") and r["from"] <= hi and lo <= (r.get("to") or r["from"])
                on = any(overlaps(r) for r in mine)
                strong = on and h.get("closeness") == "lines" and h.get("source") == "open_pr"   # open, on this contract's own lines: one of the two has to adapt
                if h.get("key") in keys:   # the same PR on another cited file: one entry, strong if any of its overlaps is
                    if strong and not keys[h["key"]]["strong"]:
                        keys[h["key"]].update({"strong": True, "path": h.get("path"), "closeness": "lines"})
                    continue
                keys[h.get("key")] = e = {k: h.get(k) for k in ("key", "title", "url", "source", "state", "closeness", "path", "author")} | {"strong": strong}
                hs.append(e)
        c["collisions"] = sorted(hs, key=lambda h: (not h["strong"], h["closeness"] != "lines"))[:6]
        c["findings"] = [x for x in c.get("findings", []) if x in findings][:12]   # the ones the skill tied to this contract
        if "seam" not in c:
            definers = {r["pr"] for r in c["defined"] if r.get("changed")}
            if len(definers) > 1:
                c["seam"] = sorted(definers)
        c["unproven"] = c["change"] in ("added", "changed", "removed") and not any(r.get("changed") for r in refs) and not any(r.get("outside") for r in refs)
        high, breaks, oneway, every = _rank(c.get("risk")) == 2, c.get("compat") == "breaking", c.get("door") == "one-way", c.get("reaches") == "all"
        repos_of = {(comp_repo.get(x) or "").lower() for x in [c["from"], *c["to"]] if comp_repo.get(x)}
        crosses = len(repos_of) > 1 or any(not comp_repo.get(x) for x in [c["from"], *c["to"]] if x)   # between repos, or to a part outside them
        first = (c["change"] == "missing" or c.get("mismatch") or any(h["strong"] for h in c["collisions"]) or c["unproven"]
                 or (high and (breaks or oneway)) or (every and (breaks or (c.get("compat") == "internal" and crosses))))
        then = high or breaks or oneway or every
        c["tier"] = 3 if c["change"] == "unchanged" else 0 if first else 1 if then else 2
        cons.append(c)
    idx = {c["id"]: i for i, c in enumerate(cons)}
    order = sorted(cons, key=lambda c: (c["tier"], idx[c["id"]]))   # within a tier, the order the skill wrote them
    comps = []
    for n in sysd["components"]:
        n = dict(n)
        at = [c for c in cons if c["from"] == n["id"] or n["id"] in c["to"]]
        if "risk" not in n and at:
            top = max(at, key=lambda c: (_rank(c.get("risk")), -idx[c["id"]]))
            if top.get("risk"):
                n["risk"], n["risk_from"] = top["risk"], top["id"]
        comps.append(n)
    by_pr = {k: [c["id"] for c in order if k in c["touched_by"]] for k in prs}
    tiers = {}
    for p in data.get("prs", []):
        for r in (p.get("attention") or {}).get("ranges", []):
            t = tiers.setdefault((p["key"], r["path"]), r["tier"])
            if ["deep", "review", "skim", "skip"].index(r["tier"]) < ["deep", "review", "skim", "skip"].index(t):
                tiers[(p["key"], r["path"])] = r["tier"]
    repo_of = {k: p["repo"].lower() for k, p in prs.items()}
    cited_paths = {(repo_of[r["pr"]], r["path"]) for c in cons for r in c["defined"] + c["used"] + c["tests"] if r.get("diff")}   # a stack repeats files: cited in one PR is cited
    rest = [{"pr": k, "path": f["path"], "role": f.get("role"), "lines": (f.get("additions") or 0) + (f.get("deletions") or 0),
             "add": f.get("additions") or 0, "del": f.get("deletions") or 0, "tier": tiers.get((k, f["path"]))}
            for (k, _), f in files.items() if (repo_of[k], f["path"]) not in cited_paths and tiers.get((k, f["path"]))]   # moved and formatting-only files need no contract
    TR = {"deep": 0, "review": 1, "skim": 2, "skip": 3, None: 4}
    rest.sort(key=lambda r: (TR.get(r["tier"], 4), -r["lines"]))
    # merge order: a PR waits on the PRs that own a contract it uses, or one its contracts rely on
    owner = {c["id"]: set(c["prs"]) for c in cons}
    after: dict = {k: {} for k in prs}
    for c in cons:
        for p in c["touched_by"]:
            ups = set(c["prs"]) - {p} if p not in c["prs"] else set()
            for d in c["depends"]:
                if p in c["prs"]:
                    ups |= owner.get(d, set()) - {p}
            for q in ups:
                after[p].setdefault(q, []).append(c["id"])
    for chain in ((data.get("context") or {}).get("stacks") or []):
        for lo, hi in zip(chain, chain[1:]):
            if lo in prs and hi in prs:
                after[hi].setdefault(lo, [])   # stacked on it: waits on it, whatever the contracts say
    reach = {p: set(after[p]) for p in prs}   # who each PR waits on, directly or through others
    for _ in prs:
        for p in prs:
            reach[p] |= {r for q in list(reach[p]) for r in reach[q]}
    cyc = {p for p in prs if p in reach[p]}   # PRs that wait on each other land together
    done, merge, left = set(), [], list(prs)
    while left:
        ready = [p for p in left if set(after[p]) - (cyc & reach[p] if p in cyc else set()) <= done] or [left[0]]
        for p in ready[:1] if ready[0] in cyc else ready:
            merge.append({"pr": p, "after": [q for q in prs if q in after[p]], "because": {q: sorted(set(v)) for q, v in after[p].items() if v},
                          **({"together": True} if p in cyc else {})})
            done.add(p); left.remove(p)
    total = sum(1 for f in files.values() for h in f.get("hunks", []) for ln in h.get("lines", []) if ln[0] in "+-")   # the diff's own lines
    ncited = sum(len(v) for v in cited.values())
    counts = {ch: sum(1 for c in cons if c["change"] == ch) for ch in CHANGES}
    counts.update({"breaking": sum(c.get("compat") == "breaking" for c in cons), "one_way": sum(c.get("door") == "one-way" for c in cons),
                   "reaches_all": sum(c.get("reaches") == "all" for c in cons), "mismatches": sum(bool(c.get("mismatch")) for c in cons),
                   "collisions": sum(any(h["strong"] for h in c["collisions"]) for c in cons), "nearby": sum(bool(c["collisions"]) for c in cons),
                   "seams": sum(bool(c.get("seam")) for c in cons), "decisions": sum(bool(c.get("decision")) for c in cons),
                   "unproven": sum(c["unproven"] for c in cons)})
    n = sum(c["change"] != "unchanged" for c in cons)
    for c in cons:
        if c["unproven"]:
            warn.append(f"system.{c['id']}: claims a change but cites no changed line")
    return {"summary": sysd.get("summary", ""), "components": comps, "contracts": cons, "flows": sysd.get("flows", []),
            "order": [c["id"] for c in order], "headline": f"Review {n} contract{'s' if n != 1 else ''}" + (f", not {total:,} changed lines" if total >= 400 else "")
            + (f" ({len(cons) - n} more unchanged, for context)" if len(cons) > n else ""),
            "by_pr": by_pr, "rest": rest[:400], "merge": merge, "coverage": {"changed_lines": total, "cited": ncited, "files_off_contract": len(rest)},
            "counts": counts, "warnings": warn}

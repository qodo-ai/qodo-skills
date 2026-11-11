"""Decisions: what each PR decides, set against the plan it was written from.

The skill writes them into enrich.json per PR (format in skill/references/decisions.md). A decision the code makes
cites the changed lines that make it (`ev`, checked like the behavior diff's); one the plan asked for and the code
doesn't make cites nothing and quotes the plan. The point is the decisions nobody planned: the reviewer accepts them,
asks why, or asks for a fix.
"""
from __future__ import annotations

from .behavior import MAX_EV, changed, window

STATUSES = ("unplanned", "changed", "missing", "planned")      # the order the page reads them in
SOURCES = ("notes", "track", "session", "ticket", "spec", "rules", "pr", "inferred")   # rules: the organization's requirements
KINDS = ("product", "technical")   # what a user sees and when, or how it is built
EFFECTS = ("cost", "volume", "trigger", "data", "security", "ux", "contract")   # silent: behavior that won't fail, only differ
# heads-ups raised while the code was written (Claude Code's "you should know" observer, a review skill, a person)
NOTICE_KINDS = ("pattern", "duplicate", "plan", "risk", "other")
RESPONSES = ("none", "learn_more", "knew", "dismissed")   # what the author clicked; none of them accepts the behavior
NOTICE_STATES = ("open", "accepted", "fixed", "stale")    # the skill's reassessment against the code as it is now


def _ev(f_of, key: str, evs, where: str, errs: list[str], resolve: bool) -> list[dict]:
    out = []
    for e in evs if isinstance(evs, list) else []:
        if not isinstance(e, dict):
            errs.append(f"{where}: each ev is {{path, side, from, to}}"); continue
        path, side = e.get("path"), e.get("side", "new")
        f = f_of.get(path)
        if side not in ("new", "old"):
            errs.append(f"{where}: ev side must be new or old, not {side!r}"); continue
        if not f:
            errs.append(f"{where}: ev path {path} is not changed in {key}"); continue
        try:
            lo, hi = int(e["from"]), int(e.get("to", e["from"]))
        except (KeyError, TypeError, ValueError):
            errs.append(f"{where}: ev needs integer from/to"); continue
        hit = sorted(n for n in changed(f, side) if lo <= n <= hi)
        if not hit:
            errs.append(f"{where}: ev {path}:{side} {lo}-{hi} touches no changed line"); continue
        r = {"path": path, "side": side, "from": lo, "to": hi, "at": hit[0]}   # at: the changed line an answer is pinned to
        if resolve:
            w = window(f, side, lo, hi)
            r.update(lines=w[:MAX_EV], cut=max(0, len(w) - MAX_EV))
        out.append(r)
    return out


def normalize(raw, pr: dict, *, resolve: bool = False) -> tuple[list[dict], list[str]]:
    """Check one PR's decisions. Returns (decisions, problems); a decision with a problem is dropped, so the page never
    shows a claim about code it can't point at."""
    key, errs, out = pr["key"], [], []
    f_of = {f["path"]: f for f in pr.get("files", [])}
    fids = {f["id"] for f in pr.get("findings", [])}
    if raw is not None and not isinstance(raw, list):
        return [], [f"{key} decisions: a list of {{text, status, plan, source, why, ev}}"]
    seen: set[str] = set()   # an id keys the reader's answer and its note: two decisions can't share one
    for i, d in enumerate(raw or []):
        where = f"{key} decisions[{i}]"
        if not isinstance(d, dict) or not str(d.get("text") or "").strip():
            errs.append(f"{where}: needs text (the decision, in one line)"); continue
        st = d.get("status")
        if st not in STATUSES:
            errs.append(f"{where}: status must be one of {', '.join(STATUSES)}"); continue
        mine: list[str] = []
        ev = _ev(f_of, key, d.get("ev"), where, mine, resolve)
        if st != "missing" and not ev and not mine:
            mine.append(f"{where}: a {st} decision cites the changed lines that make it (ev)")
        if st in ("changed", "missing", "planned") and not str(d.get("plan") or "").strip():
            mine.append(f"{where}: a {st} decision quotes what the plan said (plan)")
        if mine:
            errs += mine; continue
        src = d.get("source") if d.get("source") in SOURCES else "inferred"
        if d.get("source") not in SOURCES:
            errs.append(f"{where}: source {d.get('source')!r} is not one of {', '.join(SOURCES)}; kept as inferred")
        eff = [x for x in (d.get("effects") or []) if x in EFFECTS] if isinstance(d.get("effects"), list) else []
        did = str(d.get("id") or f"d{i + 1}")
        if did in seen:
            errs.append(f"{where}: id {did!r} is used by another decision on {key}"); continue
        seen.add(did)
        item = {"id": did, "text": str(d["text"]).strip()[:240], "status": st,
                "plan": str(d.get("plan") or "").strip()[:600], "source": src,
                "why": str(d.get("why") or "").strip()[:600], "effects": eff,
                "notice": str(d.get("notice") or "").strip()[:240], "ev": ev,
                # the existing behavior or convention this departs from ("unlike Gerrit, re-running the wizard fails")
                "pattern": str(d.get("pattern") or "").strip()[:300]}
        if d.get("kind") in KINDS:
            item["kind"] = d["kind"]
        refs = [{"title": str(r.get("title") or r["url"]).strip()[:120], "url": r["url"]} for r in d.get("refs") or []
                if isinstance(r, dict) and str(r.get("url") or "").startswith(("https://", "http://"))] if isinstance(d.get("refs"), list) else []
        if refs:
            item["refs"] = refs[:6]   # where the human instruction lives: the ticket, the PRD, the organization's rule
        if d.get("finding"):
            if d["finding"] in fids:
                item["finding"] = d["finding"]
            else:
                errs.append(f"{where}: finding {d['finding']} is not one of {key}'s findings")
        out.append(item)
    out.sort(key=lambda x: STATUSES.index(x["status"]))
    return out, errs


def normalize_notices(raw, prs: dict) -> tuple[list[dict], list[str]]:
    """Heads-ups from the coding session, kept with what the author answered and what holds now. An answer of
    "knew this already" or "dismiss" is not acceptance: a notice stays open until it is accepted, fixed, or no
    longer applies to the code."""
    if raw is not None and not isinstance(raw, list):
        return [], ["notices: a list of {text, kind, source, response, state, pr, decision, why}"]
    out, warn, seen = [], [], set()
    for i, n in enumerate(raw or []):
        where = f"notices[{i}]"
        if not isinstance(n, dict) or not str(n.get("text") or "").strip():
            warn.append(f"{where}: needs text (the heads-up as it was raised)"); continue
        nid = str(n.get("id") or f"n{i + 1}")
        if nid in seen:
            warn.append(f"{where}: id {nid!r} is used twice"); continue
        seen.add(nid)
        for k in ("pr", "kind", "response", "state", "decision"):
            if n.get(k) is not None and not isinstance(n.get(k), str):
                warn.append(f"{where}: {k} must be a string"); n = {**n, k: None}
        pr = n.get("pr") if n.get("pr") in prs else None
        if n.get("pr") and not pr:
            warn.append(f"{where}: unknown pr {n.get('pr')}")
        dec = str(n.get("decision") or "")
        if dec and pr and dec not in {d.get("id") for d in prs[pr].get("decisions") or []}:
            warn.append(f"{where}: decision {dec!r} is not one of {pr}'s"); dec = ""
        pick = lambda k, allowed, dflt: n.get(k) if n.get(k) in allowed else dflt
        for k, allowed in (("kind", NOTICE_KINDS), ("response", RESPONSES), ("state", NOTICE_STATES)):
            if n.get(k) is not None and n.get(k) not in allowed:
                warn.append(f"{where}: {k} must be one of {', '.join(allowed)}")
        out.append({"id": nid, "text": str(n["text"]).strip()[:400], "kind": pick("kind", NOTICE_KINDS, "other"),
                    "source": str(n.get("source") or "you-should-know").strip()[:60], "response": pick("response", RESPONSES, "none"),
                    "state": pick("state", NOTICE_STATES, "open"), "pr": pr, "decision": dec if pr else "",
                    "why": str(n.get("why") or "").strip()[:500], "related": str(n.get("related") or "").strip()[:200]})
    return out, warn

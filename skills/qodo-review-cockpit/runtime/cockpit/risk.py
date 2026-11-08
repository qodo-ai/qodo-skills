"""Merge Risk, as Explainable Risk (Hussam's proposal): three factors per failure scenario, combined by two versioned
decision tables, never averaged, with Unknown kept explicit. Each scenario is one of the review's parts (an impact
row); the skill writes its factors with evidence, and this module only applies the rules."""
from __future__ import annotations

RULES_VERSION = "er-v1"   # the tables below; a change to them is a new version
FACTORS = ("radius", "damage", "complexity")
NAMES = {"radius": "Blast radius", "damage": "Potential damage", "complexity": "Complexity"}
SCALES = {"radius": ("small", "medium", "large"), "damage": ("low", "medium", "high"), "complexity": ("low", "medium", "high")}
LEVELS = ("low", "medium", "high")
WORDS = {"small": "Small", "medium": "Medium", "large": "Large", "low": "Low", "high": "High", "unknown": "Unknown"}
CRITICALITY = ("high", "medium", "low", "undeclared")

# Step 1: blast radius x potential damage -> potential impact. Rows: radius; columns: damage.
T1 = {"small": ("low", "medium", "high"), "medium": ("low", "medium", "high"), "large": ("medium", "high", "high")}
# Step 2: potential impact x complexity -> Risk. Rows: impact; columns: complexity.
T2 = {"low": ("low", "medium", "medium"), "medium": ("medium", "medium", "high"), "high": ("high", "high", "high")}
EFFORT = {"low": "Focused check of the changed behavior", "medium": "Complete review, aimed by the factors",
          "high": "Thorough review of failure paths, consumers and safeguards", "unknown": "Investigate first, review conservatively"}
MEANING = {"low": "a failure stays small and easy to undo",
           "medium": "a failure is recoverable and reaches a limited part of the product",
           "high": "a failure could be serious (security, money, lost data) or spread through shared code",
           "unknown": "there isn't enough evidence yet to say how bad a failure could be"}
APPROVAL_LIMIT = "medium"   # the suggested starting limit for teams that opt in to auto-approval


def _rank(level: str) -> int:
    return LEVELS.index(level)


def combine(radius: str, damage: str, complexity: str) -> dict:
    """One scenario through the two tables, with the rule ids that decided."""
    impact = T1[radius][SCALES["damage"].index(damage)]
    risk = T2[impact][SCALES["complexity"].index(complexity)]
    return {"impact": impact, "risk": risk, "rules": [f"{RULES_VERSION}.T1.{radius}-{damage}", f"{RULES_VERSION}.T2.{impact}-{complexity}"]}


def scenario_risk(levels: dict) -> dict:
    """Known factors go straight through the tables; an Unknown factor is tried at every level, so the result is a
    range. A range that isn't one level is Unknown, never the low end."""
    options = {f: [levels[f]] if levels.get(f) in SCALES[f] else list(SCALES[f]) for f in FACTORS}
    outs = [combine(r, d, c) for r in options["radius"] for d in options["damage"] for c in options["complexity"]]
    lo, hi = min(outs, key=lambda o: _rank(o["risk"])), max(outs, key=lambda o: _rank(o["risk"]))
    if lo["risk"] == hi["risk"] and len(outs) == 1:
        return {"risk": lo["risk"], "impact": lo["impact"], "rules": lo["rules"], "range": None}
    if lo["risk"] == hi["risk"]:   # unknown factors that can't change the answer
        return {"risk": lo["risk"], "impact": None, "rules": [], "range": None, "settled_despite_unknown": True}
    return {"risk": "unknown", "impact": None, "rules": [], "range": [lo["risk"], hi["risk"]]}


def normalize_factors(raw, changed: set[str], repos: set[str] = frozenset()) -> tuple[dict | None, list[str]]:
    """The skill's factors for one scenario: {radius|damage|complexity: {level, why, ev?}, criticality?, contained?,
    flag?}. A factor without a level or a reason is Unknown; evidence must name a changed file."""
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["factors: an object {radius, damage, complexity}"]
    out, warn = {}, []
    for f in FACTORS:
        v = raw.get(f) if isinstance(raw.get(f), dict) else {}
        level = str(v.get("level") or "").lower()
        why = str(v.get("why") or "").strip()
        if level not in SCALES[f] or not why:
            if v:
                warn.append(f"factors.{f}: needs level ({'|'.join(SCALES[f])}) and why; read as Unknown")
            out[f] = {"level": "unknown", "why": why or "Not assessed."}
            continue
        from .story import plain_layer   # the why reads on the overview: references go in ev, not the prose
        warn += plain_layer(f"factors.{f}.why", why, repos)
        raw_ev = v.get("ev") if isinstance(v.get("ev"), list) else []
        ev = [e for e in raw_ev if isinstance(e, dict) and isinstance(e.get("path"), str) and e["path"].strip()]
        if len(ev) < len(raw_ev):
            warn.append(f"factors.{f}: {len(raw_ev) - len(ev)} evidence entr{'y' if len(raw_ev) - len(ev) == 1 else 'ies'} without a text path dropped")
        stray = [e["path"] for e in ev if e["path"] not in changed]
        if stray:
            warn.append(f"factors.{f}: evidence outside the changed files dropped ({', '.join(stray[:3])})")
        out[f] = {"level": level, "why": why[:400], "ev": [{"path": e["path"], **({"lines": str(e["lines"])} if e.get("lines") else {})}
                                                            for e in ev if e["path"] in changed][:6]}
    crit = str(raw.get("criticality") or "undeclared").lower()
    out["criticality"] = crit if crit in CRITICALITY else "undeclared"   # missing is not Low
    for k in ("contained", "flag", "recoverability"):
        if raw.get(k):
            out[k] = str(raw[k]).strip()[:240]
    return out, warn


def _criticality(fx: dict, row: dict, crit: dict | None) -> dict:
    """A scenario's importance: the team's map when it declares the paths; else the review's judgment, shown as a
    suggestion. An unconfirmed Low is undeclared: a wrong Low hides damage."""
    mapped = None
    if crit:
        from .criticality import for_paths
        strs = lambda v: [x for x in v if isinstance(x, str)] if isinstance(v, list) else []   # a malformed row never iterates a string
        paths = strs(row.get("paths")) or [e["path"] for f in FACTORS for e in ((fx.get(f) or {}).get("ev") or []) if isinstance(e, dict) and isinstance(e.get("path"), str)]
        mapped = for_paths(crit, strs(row.get("prs")), paths)   # the row's paths, else the files its factors cite
        if mapped["source"] == "declared":
            return mapped
    judged = fx.get("criticality", "undeclared")
    if judged in ("medium", "high"):
        return {"level": judged, "source": "review"}
    sug = judged if judged == "low" else (mapped or {}).get("suggested") or ((mapped or {}).get("level") if (mapped or {}).get("source") == "discovered" else None)
    return {"level": (mapped or {}).get("level") if (mapped or {}).get("source") == "discovered" else "undeclared",
            "source": "discovered" if (mapped or {}).get("source") == "discovered" else "none", **({"suggested": sug} if sug else {})}


def assess(data: dict, crit: dict | None = None) -> dict:
    """The work package's Merge Risk: each scenario through the tables, then the riskiest one. A scenario the
    skill hasn't assessed is Unknown on every factor. `crit`: the resolved criticality map (cockpit.criticality)."""
    from .criticality import gate
    rows = data.get("impact") or []
    scenarios = []
    for i, r in enumerate(rows):
        fx = r.get("factors") or {}
        levels = {f: (fx.get(f) or {}).get("level", "unknown") for f in FACTORS}
        res = scenario_risk(levels)
        cr = _criticality(fx, r, crit)
        scenarios.append({"i": i, "component": r.get("component", ""), "prs": r.get("prs") or [], "assessed": bool(fx),
                          "factors": {f: fx.get(f) or {"level": "unknown", "why": "Not assessed."} for f in FACTORS},
                          "criticality": cr["level"], "criticality_from": cr, "contained": fx.get("contained"), "flag": fx.get("flag"),
                          "recoverability": fx.get("recoverability") or r.get("undo") or "", **res})
    known = [s for s in scenarios if s["risk"] != "unknown"]
    # the riskiest scenario decides; among equals, the worst damage, then the widest reach, then the hardest change
    fr = lambda s, f: SCALES[f].index(s["factors"][f]["level"]) if s["factors"][f]["level"] in SCALES[f] else -1
    top = max(known, key=lambda s: (_rank(s["risk"]), fr(s, "damage"), fr(s, "radius"), fr(s, "complexity"))) if known else None
    could = max([_rank(s["range"][1]) for s in scenarios if s["range"]] or [-1])
    if not scenarios:
        level, rng = "unknown", None
    elif top and could <= _rank(top["risk"]):
        level, rng = top["risk"], None
    else:   # an unassessed or partly assessed scenario could be worse than the worst known one
        floor = max([_rank(s["risk"]) for s in known] + [_rank(s["range"][0]) for s in scenarios if s["range"]] or [0])   # no lower than any scenario can be
        level, rng = "unknown", [LEVELS[floor], LEVELS[max(could, _rank(top["risk"]) if top else 0)]]
    if level == "unknown" and scenarios:   # the scenario that could be worst decides an Unknown level, not the worst known one
        open_ = [s for s in scenarios if s["range"]]
        deciding = max(open_, key=lambda s: _rank(s["range"][1]))["i"] if open_ else scenarios[0]["i"]
    else:
        deciding = top["i"] if top else (scenarios[0]["i"] if scenarios else None)
    # the picture: each factor's highest known level across scenarios (the tables decide, not the shape)
    picture = {}
    for f in FACTORS:
        ks = [s["factors"][f]["level"] for s in scenarios if s["factors"][f]["level"] in SCALES[f]]
        picture[f] = max(ks, key=SCALES[f].index) if ks else "unknown"
    out = {"source": "review" if any(s["assessed"] for s in scenarios) else "none", "version": RULES_VERSION,
            "level": level, "range": rng, "deciding": deciding, "scenarios": scenarios, "picture": picture,
            "effort": EFFORT[level], "approval": approval(data, level, gate=gate(crit) if crit else None), "words": WORDS, "tables": {"T1": T1, "T2": T2},
            "meaning": MEANING[level], "meanings": MEANING}
    out["headline"] = headline(out)
    out["because"] = because(out)
    return out


def _sentences(text: str, limit: int = 240) -> str:
    """The first sentence or two of a reason, for a headline."""
    import re
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    out = ""
    for p in parts:
        if out and len(out) + len(p) > limit:
            break
        out = f"{out} {p}".strip()
    return out[:limit + 40]


def headline(risk: dict) -> str:
    """One plain sentence on what could go wrong, from the scenario that decided the level."""
    sc = {s["i"]: s for s in risk["scenarios"]}
    top = sc.get(risk["deciding"])
    if risk["level"] == "unknown" or not top:
        missing = sorted({NAMES[f].lower() for s in risk["scenarios"] for f in FACTORS if s["factors"][f]["level"] == "unknown"})
        return f"Not assessed enough to judge: {', '.join(missing) or 'the factors'} still unknown."
    why = _sentences(top["factors"]["damage"].get("why", "")) if top["factors"]["damage"]["level"] != "unknown" else ""
    return why or f"{top['component']} is the riskiest part."


REACH = {"small": "stay in one feature", "medium": "reach one subsystem", "large": "reach shared code"}
HARM = {"low": "minor and easy to undo", "medium": "recoverable", "high": "serious (security, money or data)"}


def because(risk: dict) -> str:
    """Why this package is at its level, in words, from the deciding scenario's path through the tables."""
    import re
    top = next((s for s in risk["scenarios"] if s["i"] == risk["deciding"]), None)
    if not top or risk["level"] == "unknown":
        return ""
    f = {k: top["factors"][k]["level"] for k in FACTORS}
    if "unknown" in f.values():
        return ""
    name = re.sub(r"\s*\([^)]*\)", "", top["component"]).strip()
    name = name[:1].lower() + name[1:] if name[:2] != name[:2].upper() else name
    harm, reach = HARM[f["damage"]], REACH[f["radius"]]
    joint = " but " if f["damage"] != "high" and f["radius"] == "large" else " and "
    out = f"{WORDS[risk['level']]} because a failure in the {name} would be {harm}{joint}would {reach}"
    if top.get("impact") and _rank(top["risk"]) > _rank(top["impact"]):   # complexity raised it in step 2
        out += ", and the change is hard to get right"
    return out + "."


def approval(data: dict, level: str, limit: str = APPROVAL_LIMIT, gate: dict | None = None) -> dict:
    """What auto-approval would do at this limit: protected paths, Risk, findings and completion as separate
    conditions. A protected path anywhere in the package means no approval, whatever else it changes."""
    fs = [f for p in data.get("prs", []) for f in p.get("findings", []) if (f.get("status") or "open") == "open"]
    high = [f for f in fs if f.get("severity") in ("high", "critical")]
    def unfinished(p):   # missing evidence never unlocks approval: no source, or a review that isn't complete on this head
        rv = p.get("qodo_review") or {}
        from .product import enabled
        if not enabled(data) and not enabled(p):
            if p.get('qodo_source') in (None, 'none'):
                return True
            return bool(rv) and (rv.get('status') != 'completed' or (p.get('head_sha') and rv.get('commit') != p.get('head_sha')))
        from .product import qodo_current
        return not qodo_current(p)
    unreviewed = [p["key"] for p in data.get("prs", []) if unfinished(p)]
    from .product import enabled
    if enabled(data) and not data.get("prs"):
        unreviewed = ["no observed PRs"]
    local_incomplete = [p['key'] for p in data.get('prs', []) if (enabled(data) or enabled(p)) and p.get('files_complete', ((p.get('read_evidence') or {}).get('sections', {}).get('files') or {}).get('complete')) is not True]
    reasons = []
    if local_incomplete:
        reasons.append('Changed-file completeness is unknown on ' + ', '.join(local_incomplete) + '; all protected paths cannot be verified.')
    prot = (gate or {}).get("count") or 0
    if (gate or {}).get("error"):
        reasons.append(f"The criticality map couldn't be read ({gate['error']}), so protected paths can't be checked; a person approves.")
    unseen = sum(((gate or {}).get("unseen") or {}).values())
    if (gate or {}).get("owners_unchecked"):
        reasons.append("CODEOWNERS protection is on, but ownership wasn't looked up for the current files (run `cockpit reviewers`); a person approves.")
    if unseen:
        reasons.append(f"{unseen} changed file{'s' if unseen != 1 else ''} weren't collected, so their paths couldn't be checked against the protected ones.")
    if prot:
        reasons.append(f"{prot} changed file{'s' if prot != 1 else ''} on protected paths ({', '.join(sorted({(f['protected_by'] or '').split(':')[0] for f in gate['protected']}))}), "
                       f"so a person approves, even if the other files pass{' (mixed PR)' if gate.get('mixed') else ''}. This is the cockpit's map: Qodo's own auto-approval doesn't read it yet.")
    if level == "unknown":
        reasons.append("Risk is Unknown, which never passes.")
    elif _rank(level) > _rank(limit):
        reasons.append(f"Risk is {WORDS[level]}, above the {WORDS[limit]} limit.")
    else:
        reasons.append(f"Risk is {WORDS[level]}, within the {WORDS[limit]} limit.")
    reasons.append(f"{len(high)} open high-severity finding{'s' if len(high) != 1 else ''}." if high else "No open high-severity findings.")
    reasons.append(f"No complete Qodo review of the current commit on {', '.join(unreviewed)}." if unreviewed else "Qodo reviewed every PR.")
    ok = level != "unknown" and _rank(level) <= _rank(limit) and not high and not unreviewed and not prot and not (gate or {}).get("error") and not unseen and not (gate or {}).get("owners_unchecked") and not local_incomplete
    heads = {p["key"]: (p.get("head_sha") or "")[:7] for p in data.get("prs", [])}
    return {"limit": limit, "result": "approve" if ok else "human review", "reasons": reasons, "blocked_by_path": bool(local_incomplete or prot or unseen or (gate or {}).get("error") or (gate or {}).get("owners_unchecked")),
            "heads": heads}   # what a result is for: a new commit voids it


def report(data: dict, risk: dict | None = None) -> str:
    """The work-package Merge Risk Report: what a coding agent needs to lower the risk across the PRs and repos."""
    risk = risk or assess(data)
    W = WORDS
    head = f"Merge Risk: {W[risk['level']]}" + (f" (could be {W[risk['range'][0]]}–{W[risk['range'][1]]})" if risk.get("range") else "")
    lines = [f"# Merge Risk Report: {data.get('title') or 'work package'}", "", head, risk.get("headline", ""), risk.get("because") or f"{W[risk['level']]} means {risk.get('meaning', '')}.", f"Review effort: {risk['effort']}.",
             f"Rules: {risk['version']} (two tables; findings never feed the factors).", ""]
    rows = data.get("impact") or []
    for s in sorted(risk["scenarios"], key=lambda s: -_rank(s["risk"]) if s["risk"] != "unknown" else -1.5):
        r = rows[s["i"]] if s["i"] < len(rows) else {}
        lines.append(f"## {s['component']} · {W[s['risk']]}" + (f" (range {W[s['range'][0]]}–{W[s['range'][1]]})" if s.get("range") else ""))
        if s["prs"]:
            lines.append(f"PRs: {', '.join(s['prs'])}")
        for f in FACTORS:
            v = s["factors"][f]
            lines.append(f"- {NAMES[f]}: {W.get(v['level'], v['level'])}. {v.get('why', '')}")
        if s.get("rules"):
            lines.append(f"- Decided by: {' → '.join(s['rules'])}")
        for k, label in (("fails", "If it fails"), ("notice", "We'd notice"), ("undo", "Undo")):
            if r.get(k):
                lines.append(f"- {label}: {r[k]}")
        if r.get("affects"):
            lines.append(f"- Reaches: {'; '.join(r['affects'][:8])}")
        for g in r.get("gaps") or []:
            lines.append(f"- To lower it: close the gap — {g}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rollback_report(plan: dict | None, left: list[dict], high: bool = False) -> str:
    """The rollback plan, for the coding agent: what to prepare before merging, and how to undo the package."""
    out = ["", "## Rollback plan"]
    if not plan:
        out.append("There's no rollback plan yet" + (": these changes outlive a revert of the code." if left else ", and Merge Risk is High."))
        plan = {}
    elif not plan.get("steps"):
        out.append("The plan has no rollback steps yet: it doesn't say how to undo the package.")
    for part, title in (("before", "Before merging"), ("steps", "To roll back, in order"), ("verify", "Then check")):
        if plan.get(part):
            out.append(f"{title}:")
            out += [f"{i}. {s['text']}" + (f" ({', '.join(s['prs'])})" if s.get("prs") else "")
                    + (f" [covers: {', '.join(s['covers'])}]" if s.get("covers") else "") for i, s in enumerate(plan[part], 1)]   # the claim coverage is checked against
    for o in plan.get("one_way") or []:
        out.append(f"- Can't be undone: {o['what']}" + (f". {o['why']}" if o.get("why") else ""))
    for f in left:
        out.append(f"- {'Not covered by the plan' if plan else 'Rollback-sensitive'}: {f['path']} ({f['label']})")
    return "\n".join(out) + "\n"

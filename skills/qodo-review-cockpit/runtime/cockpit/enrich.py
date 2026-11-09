"""Merge agent-written enrichment into a session's review-data.json.

Input JSON (all keys optional):
{
  "prs": {
    "owner/repo#12": {
      "summary": "markdown", "risk": "markdown",
      "diagrams": [{"id": "flow", "title": "Checkout flow", "mermaid": "sequenceDiagram ..."}],
      "findings": [{"category": "bug", "severity": "high", "path": "a.py", "line": 3, "title": "...", "body": "...",
                    "stance": "agree|partial|disagree", "why": "..."}],
      "story": [{"kind": "diagram", "title": "...", "lede": "...", "mermaid": "..."}]
    }
  },
  "story": [ ...beats for the whole session (how the PRs fit together)... ],
  "behavior": { ...the behavior diff for the `behavior` style (skill/references/behavior.md)... },
  "knowledge": [
    {"type": "Invariant", "title": "Prices are integers in cents", "body": "...",
     "paths": ["src/payments/**"], "pr": "owner/repo#12", "source": "https://github.com/..."}
  ]
}
Knowledge items become OKF concepts with status: draft, generated.by the agent, and are
listed as candidates in the app for the reviewer to confirm or reject.
"""
from __future__ import annotations

import json
from pathlib import Path

from .behavior import check as check_behavior
from .memory import OKF
from .attention import compute as attention
from .layers import normalize as normalize_layers
from .story import missing_flow, normalize
from .util import mem_path, memory_on, session_config, write_json


READ_TARGET = 0.3   # share of changed lines left on Read after the skill's triage, for PRs of 200+ lines
SKIM_TARGET = 0.3   # skim at most this share; the rest of what needs no reading is skip


def story_anchors(pr: dict, beats: list) -> list[dict]:
    """Changed spans of this PR that the story points at (code beats, refs with a line); they weigh toward deep read."""
    paths = {f["path"] for f in pr.get("files", [])}
    out: list[dict] = []

    def walk(x):
        if isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            if x.get("pr") in (None, pr["key"]) and x.get("path") in paths:
                lo = x.get("from") if isinstance(x.get("from"), int) else x.get("line")
                if isinstance(lo, int):
                    hi = x.get("to") if isinstance(x.get("to"), int) else lo
                    out.append({"path": x["path"], "side": x.get("side", "new"), "from": lo, "to": hi})
            for v in x.values():
                if isinstance(v, (list, dict)):
                    walk(v)

    walk(beats)
    return out


from .product import session_operation


@session_operation
def enrich(sdir: Path, payload: dict, agent: str = "claude/review-prs") -> dict:
    from .product import enabled
    if not enabled():
        return _enrich(sdir, payload, agent)
    from copy import deepcopy
    from .session_writer import session_writer
    from .util import _merge
    with session_writer(sdir):
        authored_file = sdir / 'enrich.json'
        previous = json.loads(authored_file.read_text()) if authored_file.is_file() else {}
        authored = _merge(previous, deepcopy(payload))
        # Normalizers can enrich their input; persist only the original authored values.
        result = _enrich(sdir, deepcopy(authored), agent)
        write_json(authored_file, authored)
        return result


def _enrich(sdir: Path, payload: dict, agent: str) -> dict:
    cfg = session_config(sdir)
    p = sdir / "review-data.json"
    data = json.loads(p.read_text())
    by_key = {pr["key"]: pr for pr in data["prs"]}
    changed = []
    for key, extra in (payload.get("prs") or {}).items():
        pr = by_key.get(key)
        if not pr:
            continue
        for k in ("summary", "risk"):
            if extra.get(k):
                pr[k] = extra[k]
        if extra.get("diagrams"):   # replaces earlier agent diagrams; Qodo's own diagram stays
            keep = [d for d in pr.get("diagrams", []) if d.get("source") == "qodo"]
            pr["diagrams"] = keep + extra["diagrams"]
        for fid, st in (extra.get("stances") or {}).items():   # agent's view on existing (Qodo) findings
            for f in pr.get("findings", []):
                if f["id"] == fid:
                    f["stance"], f["stance_why"] = st.get("stance"), st.get("why", "")
        if extra.get("findings") is not None:   # re-runs replace the agent's findings, never add twice
            from .agent_findings import assign
            from .distill import load_events
            reserved = [(e['target'].get('id') if isinstance(e.get('target'), dict) else e.get('target'))
                        for e in load_events(sdir) if isinstance(e, dict) and e.get('pr') in (None, key)]
            finding_ids = assign(pr, extra['findings'], (x for x in reserved if isinstance(x, str)))
            pr["findings"] = [f for f in pr.get("findings", []) if f.get("source") != "agent"]
        for i, f in enumerate(extra.get("findings") or []):
            pr.setdefault("findings", []).append({
                "id": finding_ids[i], "pr": key, "source": "agent",
                "category": f.get("category", "general"), "severity": f.get("severity", "medium"),
                "path": f.get("path"), "line": f.get("line"), "title": f.get("title", ""), "body": f.get("body", ""),
                "url": None, "stance": f.get("stance") if f.get("stance") in ("agree", "partial", "disagree") else None,
                "stance_why": str(f.get("why") or "")})
        changed.append(key)
    warnings = []
    for key, extra in (payload.get("prs") or {}).items():   # the guided walk through each PR's code
        if key in by_key and extra.get("layers") is not None:
            by_key[key]["layers"], by_key[key]["layer_coverage"], w = normalize_layers(extra["layers"], by_key[key])
            warnings += w
    for key, extra in (payload.get("prs") or {}).items():   # decisions against the plan; after findings, so their ids resolve
        if key in by_key and extra.get("decisions") is not None:
            from .decisions import normalize as normalize_decisions
            by_key[key]["decisions"], w = normalize_decisions(extra["decisions"], by_key[key])
            warnings += w
    quality_for = {}   # read after attention below, which decides what counts as weakened or untested
    for key, extra in (payload.get("prs") or {}).items():
        if key in by_key and extra.get("quality") is not None:
            quality_for[key] = extra["quality"]
    for key, extra in (payload.get("prs") or {}).items():   # after findings exist, so refs resolve
        if key in by_key and extra.get("story") is not None:
            by_key[key]["story"], w = normalize(extra["story"], where=key, prs=by_key, sdir=sdir)
            warnings += w
    if payload.get("story") is not None:
        data["story"], w = normalize(payload["story"], where="session", prs=by_key, sdir=sdir)
        w += missing_flow(data["story"])
        warnings += w
    # attention last: it uses the layer order, the findings (incl. the agent's), the story and the skill's overrides
    concept_dicts = [c.as_dict() for c in OKF(mem_path(cfg, "okf")).concepts()]
    rules = (data.get("prefs") or {}).get("rules") or []
    for pr in data["prs"]:
        extra = (payload.get("prs") or {}).get(pr["key"]) or {}
        pr["attention"], w = attention(pr, overrides=extra.get("attention"), concepts=concept_dicts, rules=rules,
                                       anchors=story_anchors(pr, (pr.get("story") or []) + (data.get("story") or [])),
                                       additive_tests=(cfg.get("attention") or {}).get("additive_tests", "skip"))
        warnings += w
        from .impact import normalize_quality, unexplained
        if pr["key"] in quality_for:
            pr["quality"], w = normalize_quality(quality_for[pr["key"]], pr)
            warnings += w
        else:   # no quality this run: keep what an earlier run saved, and still say what's unexplained
            warnings += unexplained(pr, pr.get("quality"))
        if pr.get("files_missing"):
            warnings.append(f"{pr['key']} collect: {pr['files_missing']} changed file(s) are not in the review (GitHub's file list "
                            f"and diff gave out); say so in the story and review those files on GitHub")
        sm = pr["attention"]["summary"]
        target = (cfg.get("attention") or {}).get("read_target", READ_TARGET)
        if sm["total"] >= 200 and sm["review"] > target * sm["total"]:   # the collector is cautious; the skill triages
            warnings.append(f"{pr['key']} attention: read is {round(100 * sm['review'] / sm['total'])}% of {sm['total']} changed lines "
                            f"(aim for <= {round(100 * target)}%); triage mechanical lines into skim or skip (storytelling.md §3c)")
        skim_target = (cfg.get("attention") or {}).get("skim_target", SKIM_TARGET)
        if sm["total"] >= 200 and sm["skim"] > skim_target * sm["total"]:   # skim is a glance; what nobody learns from is skip
            warnings.append(f"{pr['key']} attention: skim is {round(100 * sm['skim'] / sm['total'])}% of {sm['total']} changed lines "
                            f"(aim for <= {round(100 * skim_target)}%); move what the story or a Read block already says to skip (storytelling.md §3c)")
    if payload.get("impact") is not None:   # blast radius: what the change reaches, with its evidence and gaps
        from .impact import normalize as normalize_impact
        data["impact"], w = normalize_impact(payload["impact"], by_key)
        warnings += w
    if payload.get("deploy") is not None:   # merge danger for the whole set: each field on its own, so sending one keeps the other
        from .impact import normalize_deploy
        data["deploy"], w = normalize_deploy(payload["deploy"], by_key); warnings += w
    if payload.get("notices") is not None:   # heads-ups from the coding session; after decisions, so links resolve
        from .decisions import normalize_notices
        data["notices"], w = normalize_notices(payload["notices"], by_key); warnings += w
    if payload.get("system") is not None:   # the contracts first (skill/references/contracts.md); refs checked against the diff
        from .system import normalize as normalize_system, resolve as resolve_system
        data["system"], w = normalize_system(payload["system"], data); warnings += w
        if data["system"]:
            warnings += (resolve_system(data) or {}).get("warnings", [])
    if payload.get("routes") is not None:   # other ways to build this, and why this one (storytelling.md)
        from .routes import normalize as normalize_routes
        data["routes"], w = normalize_routes(payload["routes"], set(by_key)); warnings += w
    if payload.get("criticality") is not None:   # the review's suggested criticality: never declared, never protecting
        from .criticality import normalize_map
        data["criticality"], w = normalize_map(payload["criticality"], "discovered"); warnings += w
    if payload.get("rollback") is not None:   # how to undo the package; checked against the rollback-sensitive files below
        from .rollback import normalize as normalize_rollback
        data["rollback"], w = normalize_rollback(payload["rollback"], set(by_key)); warnings += w
    if payload.get("door") is not None:
        from .impact import normalize_door
        data["door"], w = normalize_door(payload["door"]); warnings += w
    if payload.get("behavior") is not None:   # after agent findings exist, so `finding` ids resolve
        bh, errs, warns = check_behavior(payload["behavior"], data)
        warnings += errs + warns
        if payload["behavior"]:
            cv = bh["coverage"]
            if cv["important_lines"] and cv["cited"] < 0.4 * cv["important_lines"]:
                warnings.append(f"behavior cites {cv['cited']} of {cv['important_lines']} read-tier changed lines; "
                                "describe the files it leaves out (skill/references/behavior.md)")
        if errs:   # a sketch with an unproven line is not shown; fix the ev and rerun enrich
            warnings.append("behavior not saved: fix the errors above and run enrich again")
        else:
            data["behavior"] = payload["behavior"] or None
    if payload.get("context"):   # the skill's summaries of the sources it read
        ctx = data.setdefault("context", {})
        known = {x.get("url"): x for x in ctx.get("sources", [])}
        for src in payload["context"].get("sources") or []:
            known[src.get("url") or src.get("title")] = {**known.get(src.get("url"), {}), **src}
        ctx["sources"] = list(known.values())
    okf = OKF(mem_path(cfg, "okf"))
    cands = []
    if payload.get("knowledge") and not memory_on(cfg):
        warnings.append("memory is off (config memory.enabled), so knowledge was not saved")
        payload = {**payload, "knowledge": []}
    if memory_on(cfg):
        okf.ensure()
    by_title = {c.meta.get("title", "").strip().lower(): c for c in okf.concepts()}
    have = {(c["path"], c.get('pr')) for c in data["okf"].get("candidates", [])}
    for k in payload.get("knowledge") or []:
        same = by_title.get(k["title"].strip().lower())
        if same:   # re-running enrich must not duplicate drafts
            if (same.path, k.get('pr')) not in have:
                cands.append({**same.as_dict(), "pr": k.get("pr")})
                have.add((same.path, k.get('pr')))
            continue
        c = okf.propose(type_=k.get("type", "Fact"), title=k["title"], body=k.get("body") or k["title"],
                        paths=k.get("paths") or [], by=agent,
                        sources=[{"resource": k.get("source") or f"session:{data['session']}"}],
                        description=k.get("description", ""), tags=k.get("tags"))
        cands.append({**c.as_dict(), "pr": k.get("pr")})
        by_title[k['title'].strip().lower()] = c
        have.add((c.path, k.get('pr')))
    if memory_on(cfg):
        okf.write_index()
    data["okf"]["candidates"] = data["okf"].get("candidates", []) + cands
    data["okf"]["concepts"] = [c.as_dict() for c in okf.concepts()]
    write_json(p, data)
    try:   # the plan must cover what's hard to take back; and a High package needs one
        from .rollback import check, sensitive
        from .risk import assess
        files = sensitive(data.get("prs", []))
        warnings += check(data.get("rollback"), files, assess(data).get("level") if data.get("impact") else None)
    except Exception as e:   # noqa: BLE001  never fail enrich on this check
        warnings.append(f"rollback check skipped: {type(e).__name__}: {e}")
    return {"prs_updated": changed, "candidates": [c["path"] for c in cands], "warnings": warnings}

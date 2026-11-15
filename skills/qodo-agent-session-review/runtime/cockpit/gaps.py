"""What the default Work Package layout still shows empty, so the skill fills every widget before handing over."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _beat(data: dict, kind: str) -> dict | None:
    return next((b for b in data.get("story") or [] if isinstance(b, dict) and b.get("kind") == kind), None)


def gaps(sdir: Path) -> list[dict]:
    """One row per empty widget: page, widget, what to write and the command that takes it.
    `optional` rows may stay empty only after the sources were searched and hold nothing for them."""
    data = json.loads((sdir / "review-data.json").read_text())
    prs = data.get("prs") or []
    brief, flow = _beat(data, "brief"), _beat(data, "flow") or {}
    out = []

    def need(page, widget, write, via="enrich", optional=False):
        out.append({"page": page, "widget": widget, "write": write, "via": via, "optional": optional})

    if not brief:
        need("Overview, Requirements", "Product summary", "story beat `brief` (Today, The change, Why paragraphs)")
    if not (brief or {}).get("assets"):
        need("Requirements", "Product assets", "brief.assets: the PRD, tickets, deck or prototype links found in the PR descriptions, linked tickets and specs", optional=True)
    if not flow.get("skip"):
        if not (flow.get("answers") or flow.get("hops")):
            need("Requirements", "Primary behaviors", "story beat `flow` with answers (1-3) and hops")
        if not flow.get("decisions"):
            need("Decisions", "Human decisions", "flow.decisions: the design choices, what each was chosen over and why")
        if not flow.get("contracts"):
            need("Contract changes", "Contract changes", "flow.contracts: each contract the change alters and who it reaches")
    for p in prs:
        key = p.get("key", "")
        if not p.get("decisions"):
            need("Decisions", f"Agent decisions ({key})", "prs[key].decisions against the plan, with changed-line evidence")
        if not p.get("layers"):
            need("Code map, Review walkthrough", f"Guided reading ({key})", "prs[key].layers over the changed ranges")
    if not data.get("system"):
        need("System", "System", "`system`: the contracts the package changes, with code on both sides")
    if not any((r or {}).get("factors") for r in data.get("impact") or []):
        need("Overview", "Qodo risk assessment", "`impact`: failure scenarios with blast radius, damage and complexity factors")
    builder = sdir / "builder.json"
    try:
        b = json.loads(builder.read_text()) if builder.is_file() else {}
    except ValueError:
        b = {}
    if not b.get("flows"):
        need("Execution paths", "Execution paths", "builder.json `flows`: each trigger traced through the changed code", via="walkthrough --builder")
    if not b.get("files"):
        need("Code changes", "Code changes", "builder.json `files`: every changed file with its methods", via="walkthrough --builder")
    have = {int(m.group(1)) for m in (re.fullmatch(r"triage-(\d+)\.json", f.name) for f in (sdir / "triage").glob("triage-*.json")) if m} if (sdir / "triage").is_dir() else set()
    for p in prs:
        if p.get("number") not in have:
            need("Findings", f"Findings review ({p.get('key', '')})", f"triage-{p.get('number')}.json, findings-{p.get('number')}.json and triage-{p.get('number')}.html", via="walkthrough --triage-dir")
    return out

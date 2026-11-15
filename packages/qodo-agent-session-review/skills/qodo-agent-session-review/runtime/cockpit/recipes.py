"""Your own review styles: a recipe says which of Focus's blocks to show, in which tabs (or on one page), how
dense, in which accent, and what opens first. Focus draws any recipe, so a style needs no code of its own.

Recipes live in the data home (`<home>/my-styles/<id>.json`), never in the code, so an update keeps them. A
request is what a reader typed in the page's "Describe it" box while the page was served: Claude Code turns it
into a recipe (`cockpit style add recipe.json --request <id>`), and the open page picks it up."""
from __future__ import annotations

import json
import os
import re

from .util import HOME, now_iso

DIR = HOME / "my-styles"
REQUESTS = DIR / "requests"

# Focus's blocks, the parts a recipe arranges. Kept in step with BLOCKS in app/styles/focus.html.
BLOCKS = {
    "brief": "The title and the brief: One line, Why, What, How",
    "flow": "How it works: plain answers, then one request followed hop by hop with what each hop carries",
    "plan": "The reading-plan bar, with Map · Route",
    "risk": "Merge Risk: one level from each failure scenario's blast radius, potential damage and complexity through two tables: what would go wrong, the deciding scenario, how it was decided, review effort and the auto-approval preview; then Quality and plan alignment",
    "impact": "One-way or two-way door, the deploy order, what the change reaches (blast radius), what could go wrong and how we'd notice, changes per domain, and the findings and tests behind it",
    "starts": "Start here: the one to three things to look at first",
    "scope": "Scope against the spec, in one line",
    "contracts": "Contracts between the PRs",
    "other": "Other work on the same code",
    "prs": "The pull requests and their merge order",
    "stories": "The journey and who it's for",
    "arch": "Architecture: the lenses and diagrams",
    "changes": "Changes: the behavior diff, file by file",
    "findings": "Quality: tests (weakened, untested, added), CI checks, and findings by severity",
    "walk": "The review walkthrough, unit by unit",
    "review": "Your review: decisions, verdict, notes to copy",
    "system": "The System tab: the Contract Map, every contract the package changes with its code on both sides",
}
LABELS = {"brief": "Brief", "flow": "How it works", "plan": "Reading plan", "risk": "Merge Risk", "impact": "Merge danger", "starts": "Start here", "scope": "Scope", "contracts": "Contracts",
          "other": "Other work", "prs": "Pull requests", "stories": "Stories", "arch": "Architecture", "changes": "Changes",
          "findings": "Quality", "walk": "Review walkthrough", "review": "Your review", "system": "System"}   # a tab with no name takes its first block's
# Work Package's own blocks (app/styles/package.html): a recipe may name them; Focus skips what it can't draw
PACKAGE_BLOCKS = {"verdict": "Verdict: the bottom line, whether the package is ready to merge, and what still blocks it",
                  "prstable": "Package table: a row per repo that opens to a row per PR, with merge, open findings, CI and lines",
                  "assets": "Product assets: links to the feature's PRD, tickets, overview deck and prototype",
                  "summary": "Product summary: the feature in one line",
                  "behaviors": "Behaviors: the primary behaviors, how the flow works and why it's being built, each to open",
                  "bhv": "Primary behaviors: plain answers to a newcomer's first questions about the change",
                  "bdif": "What's different: how this path differs from the usual one, aspect by aspect",
                  "bdec": "Key decisions: the design decisions behind the change, and what each was chosen over",
                  "bcon": "Contract changes: the contracts the change alters, and which callers each one reaches",
                  "bhop": "Hop by hop: one request followed across systems",
                  "bwhy": "Why it's being built: the problem the change solves, with its sources",
                  "rsum": "Risk assessment: Merge Risk's level, what would go wrong, and a chart of each factor's highest level",
                  "rtext": "Risk summary: what would go wrong, in a sentence, and why Merge Risk is at its level",
                  "rblast": "Blast radius: how far a fault can reach, scenario by scenario, with the evidence",
                  "rcplx": "Complexity: how hard each scenario is to get right, with the evidence",
                  "rdmg": "Damage: how bad a fault is where it lands, scenario by scenario, with the evidence",
                  "rdeep": "Go deeper: how to roll back, how Merge Risk was decided, review effort, auto-approval and who should review",
                  "decisions": "Agent decisions: what the code decided against the plan, unplanned first, each with its code and an answer",
                  "issues": "Quality and issue findings: what the reviewers, scanners and CI found, and how it was tested"}
PACKAGE_LABELS = {"verdict": "Verdict", "prstable": "Package table", "assets": "Product assets", "summary": "Product summary", "behaviors": "Behaviors", "bhv": "Primary behaviors", "bdif": "What's different", "bdec": "Key decisions", "bcon": "Contract changes", "bhop": "Hop by hop", "bwhy": "Why it's being built", "rsum": "Risk assessment", "rtext": "Risk summary", "rblast": "Blast radius", "rcplx": "Complexity", "rdmg": "Damage", "rdeep": "Go deeper", "decisions": "Agent decisions", "issues": "Quality & Issue findings"}   # a tab with no name, in Work Package
LAYOUTS = ("tabs", "page")
DENSITIES = ("calm", "compact")
ACCENTS = ("purple", "blue", "green", "amber", "rose")
BRIEF_VIEWS = ("line", "why", "what", "how")
MAX_TABS = 8


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")[:40] or "my-style"


def validate(recipe) -> tuple[dict, list[str]]:
    """The recipe as Focus will draw it, and what had to change. Raises ValueError when nothing usable is left."""
    if not isinstance(recipe, dict):
        raise ValueError("a recipe is a JSON object")
    notes: list[str] = []
    if not isinstance(recipe.get("tabs"), list):
        raise ValueError("tabs must be a list of {label, blocks}")
    name = str(recipe.get("name") or "").strip()[:40]
    if not name:
        raise ValueError("a recipe needs a name")
    layout = recipe.get("layout") if recipe.get("layout") in LAYOUTS else "tabs"
    tabs, seen = [], set()
    for t in (recipe.get("tabs") or [])[:MAX_TABS]:
        if not isinstance(t, dict):
            continue
        blocks = []
        for b in t.get("blocks") if isinstance(t.get("blocks"), list) else []:
            if not isinstance(b, str) or (b not in BLOCKS and b not in PACKAGE_BLOCKS):
                notes.append(f"unknown block {b!r} left out")
            elif b in seen:
                notes.append(f"block {b!r} shown once only")
            else:
                seen.add(b); blocks.append(b)
        if blocks:
            tabs.append({"label": str(t.get("label") or "").strip()[:24] or LABELS.get(blocks[0]) or PACKAGE_LABELS.get(blocks[0], blocks[0].title()), "blocks": blocks})
    if not tabs:
        raise ValueError("a recipe needs at least one tab with a known block (" + ", ".join(BLOCKS) + ")")
    if layout == "page":   # one page: every block in order, one tab
        tabs = [{"label": name, "blocks": [b for t in tabs for b in t["blocks"]]}]
    rid = slug(recipe.get("id") or name)
    out = {"id": {"focus": "focus-style", "merge-risk": "merge-risk-style"}.get(rid, rid), "name": name, "about": str(recipe.get("about") or "").strip()[:160],
           "layout": layout, "tabs": tabs,
           "density": recipe.get("density") if recipe.get("density") in DENSITIES else "calm",
           "accent": recipe.get("accent") if recipe.get("accent") in ACCENTS else "purple",
           "brief": recipe.get("brief") if recipe.get("brief") in BRIEF_VIEWS else "line"}
    for k in ("request",):
        if recipe.get(k):
            out[k] = str(recipe[k])[:40]
    return out, notes


def load_all() -> list[dict]:
    """Every saved recipe, valid ones only, by name."""
    out = []
    for p in sorted(DIR.glob("*.json")) if DIR.is_dir() else []:
        try:
            out.append(validate(json.loads(p.read_text()))[0])
        except (ValueError, TypeError, OSError):   # one bad file never takes the menu down
            continue
    return sorted(out, key=lambda r: r["name"].lower())


def save(recipe, request: str | None = None, replace: bool = False) -> tuple[dict, list[str]]:
    """Save a recipe. Without `replace`, a name another saved style already uses gets its own id (-2, -3),
    so answering a request never overwrites a style the reader made."""
    if not isinstance(recipe, dict):
        raise ValueError("send the recipe as a JSON object")
    clean, notes = validate({**recipe, **({"request": request} if request else {})})
    DIR.mkdir(parents=True, exist_ok=True)
    if not replace:
        base, n = clean["id"], 2
        while (DIR / f"{clean['id']}.json").is_file():
            clean["id"] = f"{base}-{n}"; n += 1
        if clean["id"] != base:
            notes.append(f"a style with id {base!r} exists; saved as {clean['id']!r} (use --replace to overwrite it)")
    (DIR / f"{clean['id']}.json").write_text(json.dumps({**clean, "saved_at": now_iso()}, indent=2) + "\n")
    if request:
        p = REQUESTS / f"{slug(request)}.json"
        if p.is_file():
            r = json.loads(p.read_text())
            p.write_text(json.dumps({**r, "status": "done", "recipe": clean["id"]}, indent=2) + "\n")
    return clean, notes


def add_request(text: str, base=None, session: str | None = None) -> dict:
    """What a reader asked for in the Describe box, kept for Claude Code to turn into a recipe."""
    text = str(text or "").strip()
    if not text:
        raise ValueError("describe the style you want")
    REQUESTS.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(m.group(1)) for p in REQUESTS.glob("r*.json") if (m := re.match(r"r(\d+)$", p.stem))] or [0])
    while True:   # two pages asking at once: the exclusive create gives each its own id
        try:
            os.close(os.open(REQUESTS / f"r{n}.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            n += 1
    req = {"id": f"r{n}", "text": text[:2000], "session": session, "at": now_iso(), "status": "open"}
    if isinstance(base, dict):
        try:
            req["base"] = validate(base)[0]
        except ValueError:
            pass
    (REQUESTS / f"{req['id']}.json").write_text(json.dumps(req, indent=2) + "\n")
    return req


def requests(open_only: bool = False) -> list[dict]:
    out = []
    for p in sorted(REQUESTS.glob("r*.json"), key=lambda p: int(p.stem[1:]) if p.stem[1:].isdigit() else 0) if REQUESTS.is_dir() else []:
        try:
            r = json.loads(p.read_text())
        except ValueError:
            continue
        if not open_only or r.get("status") == "open":
            out.append(r)
    return out

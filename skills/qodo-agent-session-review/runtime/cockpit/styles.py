"""Review styles: different ways to read the same session.

`cockpit` is the app in app/; the others are single pages in app/styles/ rendered from cockpit.view.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .util import ROOT
from .view import view_data

STYLES_DIR = ROOT / "app" / "styles"

STYLES: dict[str, dict] = {
    "cockpit": {"name": "Agent Session Review", "ready": True,
                "what": "The full app: story, reading plan, walk, findings, notes, publish and memory."},
    "focus": {"name": "Focus", "ready": True, "template": "focus.html",
              "what": "Calm and tabbed: the overview holds the brief (One line, Why, What, How; How carries how it works, step by step), the reading-plan bar, merge danger (door, deploy order, blast radius, domains, findings and tests) and three places to start; architecture, changes, findings, the review walkthrough and your review each get a tab."},
    "risk": {"name": "Briefing", "ready": True, "template": "focus.html",   # id kept: links and configs name "risk"
             "what": "The big picture first, one level at a time: the brief, with plain answers on how the change works, what differs from the usual path, the key decisions and what changed in the contracts; then Merge Risk, what would go wrong and why, from each failure scenario's blast radius, potential damage and complexity; then where to start. Keyboard keys in the corner, and / asks Qodo about the review, with answers that point back into it."},
    "package": {"name": "Work Package", "ready": True, "template": "package.html",   # Work Package layout
                "what": "Briefing's content in a Qodo-themed page: the Qodo header with the review's name and icon actions (refresh, styles, keys), the PRs and product assets first, then the brief, Merge Risk with a wide radar and one fold per factor, issues and CI, and the reading plan as a file tree; rich tooltips, keys in the header instead of a dock. When the review wrote its contracts (`system`), a System tab holds Shlomo Dalezman's Contract Map: the components with each contract on the arrow between them, then every contract with its code on both sides."},
    "verdict": {"name": "Verdict", "ready": True, "template": "verdict.html",
                "what": "The merge decision as four questions, each answered by a picture first: is this the right way to build it (the routes weighed, side by side, with what each reuses, builds and would have to prove), what it touches and how much that matters (a criticality map: declared, suggested or not declared, with protected paths), what could go wrong (Merge Risk on a reach-by-damage grid), and whether Qodo can approve it (the gate, bound to the commits it read)."},
    "guided": {"name": "Guided Review", "ready": True, "template": "guided.html",
               "what": "Brief → Read → Decide in one page: a short briefing, a reading plan with a time box, a decision queue and a review to copy."},
    "behavior": {"name": "Behavior Diff", "ready": True, "template": "behavior.html", "needs": "behavior",
                 "what": "Each file as + / − / ~ lines of behavior, each citing its code; read by file or by capability; one comment on many places."},
    "console": {"name": "Review Console", "ready": True, "template": "console.html",
                "what": "A dark console in three views: the overview maps the set and its merge lanes, the walkthrough takes each PR along a path of its layers with code to mark read, and your review gathers verdicts, decisions and notes."},
    "onepage": {"name": "One-Page Brief", "ready": True, "template": "onepage.html",
                "what": "Each PR on one calm page: the point, the summary in its own shapes, tables and code, the evidence (tests and checks), merge danger (one-way or two-way door, blast radius) and your outcome."},
    "decisions": {"name": "Decision Review", "ready": True, "template": "decisions.html", "needs": "decisions",
                  "what": "What the agent decided on its own: each decision in the diff against the plan (Qodo's review notes, the tickets), unplanned first, with its code; accept it, ask why or ask for a fix, then the rollout step by step with what to verify."},
    "living": {"name": "Living Review", "ready": False,
               "what": "Planned: the agent in the page (chat that re-lays out the canvas, requests to the session). Needs the claude.ai artifact runtime."},
    "briefing": {"name": "Briefing", "ready": False, "what": "Planned: a paced walkthrough, one idea per screen."},
    "literate": {"name": "Literate Review", "ready": False, "what": "Planned: the review as an article for someone who wasn't there."},
}
APP = "cockpit"      # the full app (app/index.html)
DEFAULT = "package"  # what a review opens on when neither --style nor config "style" says otherwise
# the product notice: a prominent toast over the content area (a desktop computer, the rule in bold, then what it means) until the reader acknowledges it
NOTICE_BAR = ('<style>.ck-notice{position:fixed;z-index:50;bottom:max(20px,env(safe-area-inset-bottom,0px));left:var(--nvw,0px);right:0;margin:0 auto;width:min(600px,calc(100vw - var(--nvw,0px) - 32px));'
              'display:flex;align-items:center;gap:14px;padding:14px 14px 14px 16px;border:1px solid var(--accent-line,var(--line-strong));border-radius:12px;'
              'background:color-mix(in srgb,var(--accent,#7968fa) 12%,var(--surface));box-shadow:0 18px 44px rgba(0,0,0,.4);color:var(--muted);'
              'font-size:13px;line-height:1.45;animation:ck-pop .25s ease-out}.ck-notice[hidden]{display:none}'
              '.ck-ni{flex:none;display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:var(--accent-soft,var(--sunk));color:var(--accent-text,var(--ink))}.ck-ni svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}'
              '.ck-nt{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}.ck-nt b{font-size:14px;font-weight:650;color:var(--ink)}'
              '.ck-notice button{flex:none;padding:7px 16px;border:0;border-radius:8px;background:var(--accent-fill,var(--ink));color:var(--accent-ink,var(--bg));font:inherit;font-weight:600;cursor:pointer}'
              '.ck-notice button:hover{filter:brightness(1.1)}@keyframes ck-pop{from{opacity:0;transform:translateY(12px)}}'
              'body.nv-none .ck-notice{left:0;width:min(600px,calc(100vw - 32px))}@media (max-width:900px){.ck-notice{left:0;width:calc(100vw - 32px)}}@media print{.ck-notice{display:none!important}}</style>'
              '<aside role="note" class="ck-notice" id="ck-notice" hidden><span class="ck-ni" aria-hidden="true"><svg viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8M12 17v4"/></svg></span>'
              '<span class="ck-nt"><b>{{TITLE}}</b><span>{{NOTICE}}</span></span><button type="button"'
              ' onclick="this.parentNode.hidden=true;try{localStorage.setItem(\'cockpit:notice-ack\',\'1\')}catch(e){}">Got it</button></aside>'
              '<script>{const n=document.getElementById("ck-notice");try{n.hidden=!!localStorage.getItem("cockpit:notice-ack")}catch(e){n.hidden=false}}</script>')


def names(ready_only: bool = True) -> list[str]:
    return [k for k, v in STYLES.items() if v["ready"] or not ready_only]


def require(style: str | None) -> str:
    style = (style or DEFAULT).lower()
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; choose one of: {', '.join(names())}")
    if not STYLES[style]["ready"]:
        raise ValueError(f"style {style!r} is planned, not built yet; ready: {', '.join(names())}")
    return style


def missing_content(style: str, data: dict) -> str | None:
    """What the skill still has to write for this style, if anything."""
    need = STYLES[style].get("needs")
    if need == "behavior" and not data.get("behavior"):
        return "This session has no behavior diff. Ask the skill for one (`/review-prs ... --style behavior`), or write `behavior` into enrich.json."
    if need == "decisions" and not any(p.get("decisions") for p in data.get("prs", [])):
        return "This session has no decisions yet. Ask the skill to write them (`/review-prs ... --style decisions`), or write `decisions` per PR into enrich.json."
    return None


def _json_tag(obj, **attrs) -> str:
    a = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    # inside <script>: escape every '<' so data can never close the tag or open a comment
    return f'<script type="application/json"{a}>' + json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c") + "</script>"


def evidence_limits(data: dict) -> dict:
    """What the managed reads couldn't confirm, per PR: sections not read in full, a changed-file list not confirmed complete,
    changed files missing from the review, patches not confirmed complete, overlap read warnings and a Qodo read error. `recorded` is false when the PR carries no completeness records at all (a package
    collected before product reads recorded them), so the page says that once instead of flagging every file."""
    prs = []
    for pr in data.get('prs', []):
        read = pr.get('read_evidence') or {}
        files = pr.get('files', [])
        def done(f):   # a returned patch counts only with complete, nonempty items, as local_patch_evidence() requires
            ev = f.get('patch_evidence') or {}
            return ev.get('complete') is True and bool(ev.get('items')) and all(x.get('patch_complete') is True for x in ev['items'])
        listed = pr.get('files_complete', ((read.get('sections') or {}).get('files') or {}).get('complete'))
        prs.append({'key': pr.get('key', ''), 'title': pr.get('title', ''), 'recorded': bool(read) or any(f.get('patch_evidence') for f in files),
                    'files_list_complete': listed is True, 'files_missing': max(0, int(pr.get('files_missing') or 0)),
                    'sections': [{'name': k, 'status': str(v.get('status') or ''), 'complete': v.get('complete') is True} for k, v in (read.get('sections') or {}).items()],
                    'files': len(files), 'files_open': [f.get('path', '') for f in files if f.get('patch_evidence') and not done(f)],
                    'files_unrecorded': sum(1 for f in files if not f.get('patch_evidence')),
                    'overlaps': [str(w) for w in pr.get('overlap_read_warnings') or []], 'qodo_error': str(pr.get('qodo_read_error') or '')})
    return {'prs': prs}


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def menu(sdir: Path, data: dict, mode: str, links: dict[str, str] | None = None) -> list[dict]:
    """The style switcher's entries: how to open each ready style from this page. Served, the server renders any
    style; a snapshot opens the styles exported next to it (`links`: style -> file). The rest carry the ask to copy
    for Claude: a style whose content the skill hasn't written, or one not exported with this page."""
    out = []
    for k, v in STYLES.items():
        if not v["ready"]:
            continue
        url = ("/index.html" if k == APP else f"/s/{k}") if mode == "serve" else (links or {}).get(k)
        e = {"id": k, "name": v["name"], "what": v["what"], "url": url}
        need = missing_content(k, data)
        if need:
            e["needs"] = "Not written yet."
            e["ask"] = f"/review-prs write the {v['name'].lower()} for review session {sdir.name}, then export it in the {v['name']} style"
        elif not url:
            e["ask"] = f"/review-prs export review session {sdir.name} in the {v['name']} style"
        out.append(e)
    return out


def _recipes() -> list[dict]:
    from .recipes import load_all
    try:
        return load_all()
    except Exception:   # your styles are extras: never the reason a review page fails
        return []


from .product import session_operation


@session_operation
def render(style: str, sdir: Path, *, mode: str = "snapshot", title: str | None = None, data: dict | None = None,
           links: dict[str, str] | None = None, access_link: bool = False) -> str:
    """The style as a page fragment (title, fonts, styles, markup, scripts; no html/head/body).
    mode: "serve" (notes go to the local server) or "snapshot" (they stay in the reader's browser).
    links: in a snapshot, the other styles exported next to it (style -> file name)."""
    style = require(style)
    if style == APP:
        raise ValueError("Agent Session Review style is the app itself; use export.build")
    data = data or json.loads((sdir / "review-data.json").read_text())
    view = view_data(sdir, inline_media=(mode != "serve"), data=data, story_media=(style == "onepage"))
    if mode != "serve":   # a shared page never carries or applies the exporter's personal preferences to its readers
        view["prefs"] = {"enabled": False, "rules": []}
    meta = STYLES[style]
    host = {"mode": mode, "style": style, "cockpit": "/index.html" if mode == "serve" else None,
            "styles": menu(sdir, data, mode, links),
            "missing": missing_content(style, data), "recipes": _recipes(),
            "session": sdir.name if mode == "serve" else None}
    if mode == "serve":   # your app settings, the same in every session; a snapshot keeps its reader's own
        from . import appstate
        host["app"] = {"keys": list(appstate.APP_KEYS), "state": appstate.load(), "path": str(appstate.path())}
    tpl = (STYLES_DIR / meta["template"]).read_text()
    if '{{PACKAGE_SCRIPT}}' in tpl:
        script = (STYLES_DIR / 'package.js').read_text()
        for mark, part in (('/*@READER@*/', 'reader.js'), ('/*@EVIDENCE@*/', 'evidence.js'), ('/*@WELCOME@*/', 'welcome.js')):   # parts in their own files keep package.js under the 512 KiB limit
            script = script.replace(mark, (STYLES_DIR / part).read_text(), 1)
        tpl = tpl.replace('{{PACKAGE_SCRIPT}}', (STYLES_DIR / 'product-state.js').read_text() + '\n' + script)
    kit = (STYLES_DIR / "kit.js").read_text()
    page_title = title or f"{view['title']} · {meta['name']}"
    from .product import enabled, NOTICE
    if enabled(data):
        host['product'] = True
        host['notice'] = NOTICE
        head, _, rest = NOTICE.partition('. ')   # the rule as its title, the rest below it
        tpl += NOTICE_BAR.replace('{{TITLE}}', head).replace('{{NOTICE}}', rest)
        host['limits'] = evidence_limits(data)   # shown in the refresh details, in full in a dialog
    if mode == "serve" and access_link:   # served to a browser that already holds access: Copy link asks the server for a one-time link (never in a snapshot, never a key in the page)
        host['access_link'] = True
    if enabled(data) and (data.get('collection') or {}).get('complete') is False:
        coll = data['collection']
        gap = f"Work package collection incomplete: {len(coll.get('collected_refs') or [])} of {len(coll.get('requested_refs') or [])} requested changes retained. Omitted: {', '.join(coll.get('omitted_refs') or []) or 'some source evidence'}."
        tpl = tpl.replace('</title>', '</title><div role="status" style="padding:12px;background:var(--surface);color:var(--ink);border:1px solid var(--line)">' + _esc(gap) + '</div>', 1)
    html = tpl.replace("{{TITLE}}", _esc(page_title), 1)
    extra = ""
    if "{{WALKTHROUGH}}" in html:   # Execution paths, Code changes and Finding review: always drawn, with data only when the session has their files
        from .walkthrough import page_data
        wt = page_data(sdir, data)
        html = html.replace("{{WALKTHROUGH}}", (STYLES_DIR / "walkthrough.js").read_text().replace("</script", "<\\/script"), 1)
        extra = f"<style>\n{(STYLES_DIR / 'walkthrough.css').read_text()}\n</style>\n" + (_json_tag(wt, id="wt-data") + "\n" if wt else "")
    html = html.replace("{{DATA}}", extra + _json_tag(host, id="cockpit-host") + "\n" + _json_tag(view, **{"class": "case-data", "data_case": view["case"]}))
    if "{{CONTRACT_MAP}}" in html:
        html = html.replace("{{CONTRACT_MAP}}", (STYLES_DIR / "contract-map.js").read_text().replace("</script", "<\\/script"))
    return html.replace("{{KIT}}", kit)


def favicon_link() -> str:
    """The Qodo icon for a browser tab, inline so a saved page keeps it too."""
    import base64
    svg = (ROOT / "app" / "favicon.svg").read_bytes()
    return f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{base64.b64encode(svg).decode()}">'


def as_document(fragment: str) -> str:
    """A full HTML document around a style fragment (for serve and plain export), with the Qodo tab icon in its head
    (a style's own icon link moves there too: browsers ignore one in the body)."""
    m = re.search(r"<title>.*?</title>", fragment, re.S)
    head_title = m.group(0) if m else "<title>PR review</title>"
    body = fragment[m.end():] if m else fragment
    body = re.sub(r'<link rel="icon"[^>]*>\s*', "", body, count=1)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{head_title}\n{favicon_link()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")

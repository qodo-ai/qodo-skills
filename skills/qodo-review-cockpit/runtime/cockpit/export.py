"""Export a session as one self-contained HTML file to share (no server needed).

The app, its styles and the session (story, findings, diffs, notes, memory snapshot) are inlined;
media files become data URIs. Only mermaid and fonts load from public CDNs. In the snapshot,
marks and notes work in the reader's browser but never reach GitHub or memory.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path

from .distill import load_events
from .memory import OKF
from .styles import _recipes
from .util import ROOT, mem_path, memory_on, now_iso, session_config, slug

APP = ROOT / "app"


def _safe_json(obj) -> str:
    # inside <script>: never let data close the tag or open a comment
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


from .product import session_operation


@session_operation
def build(sdir: Path, styles: list[dict] | None = None) -> str:
    """The full app as one file. styles: the other styles exported next to it, for its style links."""
    cfg = session_config(sdir)
    data = json.loads((sdir / "review-data.json").read_text())
    from .product import enabled, project_data
    if enabled(data):
        data = project_data(data)
    okf = OKF(mem_path(cfg, "okf"))
    # A shared file goes to other people: it carries this review's code knowledge (the facts its PRs' files match),
    # never the exporter's personal memory (preferences, the review log) or other reviews' facts.
    files = [f.get("path") for p in data.get("prs", []) for f in p.get("files") or [] if f.get("path")]
    mine = {c for p in data.get("prs", []) for c in p.get("concepts") or []} | {c.path for c in okf.match(files)}   # also what was drafted since collect
    concepts = [c.as_dict() for c in okf.concepts() if c.path in mine]
    data = {**data, "prefs": {"rules": [], "bullets": []}, "okf": {**(data.get("okf") or {}), "concepts": [c for c in (data.get("okf") or {}).get("concepts") or [] if c.get("path") in mine]}}
    memory = {"enabled": memory_on(cfg), "rules": [], "bullets": [], "concepts": concepts}   # on, so the Knowledge tab shows this review's facts; the personal parts stay empty
    media = {}
    root = (sdir / 'media').resolve()
    from .story_media import references
    for beat, _ in references(data):
        src = beat.get('src')
        if not isinstance(src, str) or not src or src in media or src.startswith(('http://', 'https://')):
            continue
        p = (root / src).resolve()
        if not p.is_file() or not p.is_relative_to(root):
            continue
        mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        media[src] = f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()
    private = {"ask", "fold", "view", "dwell", "lens", "beat_seen", "pref_toggle", "attention_opened", "verdict",
               "finding_verdict", "read_check", "okf_verdict"}   # how you read, what you asked and decided: yours; readers get the notes and marks
    payload = {"data": data, "memory": memory, "events": [e for e in load_events(sdir) if e.get("type") not in private], "media": media, "exported_at": now_iso(),
               "styles": [s for s in styles or [] if s.get("url") and s["id"] != "cockpit"],
               "recipes": [{"id": r["id"], "name": r["name"], "about": r.get("about", "")} for r in _recipes()]}
    title = data["story"][1]["title"] if len(data.get("story") or []) > 1 and data["story"][0].get("kind") == "notice" \
        else (data.get("story") or [{}])[0].get("title") or "PR review"
    html = (APP / "index.html").read_text()
    html = html.replace('<link rel="stylesheet" href="app.css">', "<style>\n" + (APP / "app.css").read_text() + "\n</style>")
    html = html.replace('<script src="app.js" defer></script>',
                        "<script>window.__COCKPIT__ = " + _safe_json(payload) + ";</script>\n"
                        "<script defer>\n" + (APP / "app.js").read_text().replace("</script", "<\\/script") + "\n</script>")
    html = re.sub(r"<title>.*?</title>", f"<title>{_esc(title)} · PR review</title>", html, count=1)
    html = html.replace('<meta name="viewport"', f'<meta name="description" content="{_esc(_describe(data))}">\n<meta name="viewport"', 1)
    return html


def _describe(data: dict) -> str:
    prs = data.get("prs") or []
    return f"Review of {len(prs)} PR{'s' if len(prs) != 1 else ''}: " + ", ".join(p["key"] for p in prs[:6]) + ("..." if len(prs) > 6 else "")


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def as_fragment(html: str, title: str | None = None) -> str:
    """For hosts that wrap pages in their own skeleton (Claude Artifacts): drop doctype, html, head,
    body and the charset/viewport metas; keep title, fonts, styles, markup and scripts."""
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
    head = re.sub(r'\s*<meta (charset|name="viewport")[^>]*>', "", head)
    if title:
        head = re.sub(r"<title>.*?</title>", f"<title>{_esc(title)}</title>", head, count=1)
    return head.strip() + "\n" + body.strip() + "\n"


def export(sdir: Path, out: Path | None = None, *, fragment: bool = False, title: str | None = None,
           style: str | None = None, with_styles: bool = False, written: list | None = None) -> Path:
    """One self-contained page. with_styles also writes every other ready style next to it (full documents, so a host
    can serve them as extra files), and the style switcher on each page opens the others."""
    from .styles import APP, as_document, menu, names, render, require, missing_content
    style = require(style or session_config(sdir).get("style"))
    data = json.loads((sdir / "review-data.json").read_text())
    name = slug("-".join(str(p["number"]) for p in data["prs"][:4]) + "-review" + ("" if style == APP else f"-{style}"))
    out = out or sdir / "share" / f"{name}{'-artifact' if fragment else ''}.html"
    stem = slug("-".join(str(p["number"]) for p in data["prs"][:4]) + "-review")
    # An artifact host serves the fragment at its own address, under no file name, so the other style pages can't
    # link back to it: they link to a full copy of this style, written next to them, instead.
    home = f"{stem}-{style}.html" if fragment and with_styles else out.name
    if home == out.name and fragment and with_styles:   # --out took that name: the full copy needs another one
        home = f"{stem}-{style}-page.html"
    links = {style: home}
    if with_styles:   # styles whose content is written; the switcher gives the ask for the rest
        links.update({s: f"{stem}-{s}.html" for s in names() if s != style and not missing_content(s, data)})
        for s, file in list(links.items()):   # --out took another style's name: that style's page moves aside, not over the output
            if s != style and file == out.name:
                links[s] = f"{stem}-{s}-page.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    def page(s: str, as_fragment_page: bool) -> str:
        if s == APP:
            html = build(sdir, menu(sdir, data, "snapshot", links))   # links back to the styles exported with it
            if title:
                html = re.sub(r"<title>.*?</title>", f"<title>{_esc(title)}</title>", html, count=1)
            return as_fragment(html, title) if as_fragment_page else html
        html = render(s, sdir, mode="snapshot", title=title, data=data, links=links)   # already a fragment
        return html if as_fragment_page else as_document(html)

    targets = [(s, out.parent / file, False) for s, file in links.items() if not (s == style and file == out.name)]
    targets.insert(0, (style, out, fragment))
    for s, dest, as_frag in targets:
        dest.write_text(page(s, as_frag))
        if written is not None and dest != out:
            written.append(dest)
    return out

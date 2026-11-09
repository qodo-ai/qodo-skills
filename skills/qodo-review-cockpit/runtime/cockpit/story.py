"""The review story: an ordered list of beats per PR (and one for the whole session).

A beat is one thing to look at plus one sentence on what to see in it. The skill chooses the
beat kinds per PR (skill/references/storytelling.md); this module only checks the shape and
that every reference points at something real, and returns warnings the skill should fix.

Beat: {id, kind, title, lede, body?, refs?, weight?: lead|normal|aside, width?: full|half, ...kind fields}
refs: [{path, line?, end_line?, label?} | {finding: id} | {concept: okf path} | {pr: key}]
"""
from __future__ import annotations

import re
from pathlib import Path

KINDS = {
    "diagram":      "mermaid (any type) + optional highlight: [node ids]",
    "before_after": "before/after: {label, mermaid | code | media | text} each",
    "shape":        "form: pseudocode|calltree|components|files|types|flow, text (lines; with diff: true each "
                    "line starts with '+', '-' or ' '), notes: [{line (1-based in text), text}]",
    "code":         "path, from, to (new-file lines), notes: [{line, text}]; excerpt is cut from the diff",
    "media":        "src (file in the session's media/ dir or http URL), type: image|video, caption",
    "findings":     "ids: [finding ids] that belong together",
    "question":     "ask: the decision the reviewer must make; options?: [str]",
    "stat":         "items: [{label, value, tone?: good|bad|neutral}] (2-4 numbers)",
    "callout":      "tone: risk|invariant|note, text",
    "table":        "columns: [str], rows: [[str]] (<= 8 rows)",
    "views":        "views: [{id, label, question, lede, mermaid | shape: {form, text, diff?}}] (2-4 lenses on one system)",
    # mostly for the session story, where the PRs are connected:
    "flow":         "answers: [{q, a}] (1-3: the questions a newcomer asks, answered in plain words, short: <= 50 words each), hops: [{from, to, call, "
                    "carries, keyed?, returns?, defined?, consumed?, fails?, prs?: [keys]}] (3-14, in order: the one thing that "
                    "moves through the change - a request, record, event, job, deploy or user action - followed end to end, "
                    "each hop saying what it carries), follow?: the toggle's label; differs?: {usual, this, rows: [{aspect, usual, "
                    "this}]} (when the change adds a variant of an existing path), decisions?: [{decision, instead, why}] "
                    "(2-4), contracts?: [{contract, change, affects: all|new|<who>, prs?}] (what changed, and who it reaches); "
                    "or skip: why this change needs none",
    "journey":      "steps: [{actor?, text, prs: [keys], status: new|changed|unchanged|gap}]",
    "brief":        "paragraphs: [{label, text} | str] (2-4, <= 60 words each), contributions: [{pr, adds}], "
                    "assets?: [{kind: prd|tickets|deck|prototype, title, url: https://...}] (the feature's product "
                    "links, shown in the Product assets widget); shown as a collapsed list",
    "notice":       "items: [{title, text, tone: risk|decision|gap|good, beat?: id, pr?: key of the chapter "
                    "holding that beat}] (1-3, ranked)",
    "scope":        "items: [{text, source?, by: {pr key: done|partial|missing}}], prs?: [keys], item_label?",
    "stories":      "items: [{id?, for: user|developer|operator, as, want, so_that, prs: [keys], status: delivered|partial|"
                    "missing|changed, source: {kind: qodo|ticket|spec|pr|inferred, title, url?}, checks?: [{text, status: "
                    "done|partial|missing}]}] (3-8; who the change is for, in their words)",
}
STORY_FOR = ("user", "developer", "operator")
STORY_STATUS = ("delivered", "partial", "missing", "changed")
STORY_SOURCES = ("qodo", "ticket", "spec", "pr", "inferred")
PR_KEY = re.compile(r"^[\w.-]+/[\w.-]+#\d+$")
WEIGHTS = ("lead", "normal", "aside")
LEDE_WORDS, BODY_WORDS, TITLE_WORDS = 30, 90, 8
PARAGRAPH_WORDS, LENS_LEDE_WORDS, ANSWER_WORDS = 60, 30, 50   # answers sit in folds now: short, but room for a full thought
SHAPE_FORMS = ("pseudocode", "calltree", "components", "files", "types", "flow")
SHAPE_LINES, CODE_LINES = 20, 20
MEDIA_EXT = {".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".webp": "image",
             ".svg": "image", ".mp4": "video", ".webm": "video", ".mov": "video"}


# The top layer reads as a story: no PR numbers, repo names, file paths or line numbers. Those go one layer down
# (prs, refs, ev, the hops, the PR list), where a reviewer who wants them drills in.
_REF_PATTERNS = (re.compile(r"(?<![\w&])(?:[\w.-]+/[\w.-]+)?#\d{2,}\b"),                       # #5343, owner/repo#12
                 re.compile(r"\b[\w.-]+/[\w./-]*[\w-]\.(?:py|ts|tsx|js|jsx|go|java|kt|rb|rs|cs|toml|ya?ml|json|sql|sh)\b"),
                 re.compile(r"\b[\w-]+\.(?:py|ts|tsx|js|jsx|go|java|kt|rb|rs|cs)(?::\d+(?:-\d+)?)?\b"),
                 re.compile(r"\blines? \d+(?:[-–]\d+)?\b", re.I),
                 re.compile(r"\b[A-Z][A-Z0-9]{1,6}-\d+\b"))                                       # ticket keys: PLA-74


PRODUCTS_JS = {"node.js", "vue.js", "next.js", "nuxt.js", "express.js", "react.js", "three.js", "d3.js", "chart.js", "ember.js", "deno.js"}
NOT_TICKETS = {"UTF", "SHA", "ISO", "RFC", "TLS", "SSL", "AES", "RSA", "HTTP", "IPV", "PEP", "ES", "GPT", "MD", "OS", "WCAG"}


def refs_in(text: str | None, repos: set[str] = frozenset()) -> list[str]:
    """References that belong a layer down: PR numbers, file paths, line numbers, ticket keys, repo names."""
    t = text or ""
    found = []
    for p in _REF_PATTERNS:
        for m in p.finditer(t):
            g = m.group(0)
            if re.fullmatch(r"[A-Z][A-Z0-9]{1,6}-\d+", g) and g.split("-")[0] in NOT_TICKETS:
                continue   # UTF-8, SHA-256: standards, not tickets
            if g.lower() in PRODUCTS_JS:
                continue   # Node.js, Vue.js: products, not files (Auth.js stays a file)
            found.append(g)
    # repo names only when they can't be ordinary words: a slug (owner/repo) or a hyphenated name like shared-gateway
    found += [r for r in repos if r and ("/" in r or "-" in r or "_" in r) and re.search(rf"(?<![\w/-]){re.escape(r)}(?![\w-])", t)]
    return list(dict.fromkeys(found))


def plain_layer(where: str, text: str | None, repos: set[str]) -> list[str]:
    hits = refs_in(text, repos)
    return [f"{where} mixes in references ({', '.join(hits[:4])}): keep this layer plain and put them in prs, refs or ev, "
            "one layer down (storytelling.md §4, one level per section)"] if hits else []


def _words(s: str | None) -> int:
    return len(re.findall(r"\S+", s or ""))


def normalize(beats: list[dict], *, where: str, prs: dict[str, dict], sdir: Path) -> tuple[list[dict], list[str]]:
    """Return (clean beats, warnings). Unknown kinds are dropped; soft limits only warn."""
    out, warn = [], []
    repos = {k.split("#")[0] for k in prs} | {k.split("#")[0].split("/")[-1] for k in prs}
    files = {k: {f["path"]: f for f in pr.get("files", [])} for k, pr in prs.items()}
    finding_ids = {f["id"] for pr in prs.values() for f in pr.get("findings", [])}
    for i, b in enumerate(beats or []):
        b = dict(b)
        b.setdefault("id", f"b{i + 1}")
        tag = f"{where} beat {b['id']}"
        if b.get("kind") not in KINDS:
            warn.append(f"{tag}: unknown kind {b.get('kind')!r}, dropped (kinds: {', '.join(KINDS)})")
            continue
        if b.get("weight", "normal") not in WEIGHTS:
            warn.append(f"{tag}: weight must be one of {WEIGHTS}")
            b["weight"] = "normal"
        if b.get("width", "full") not in ("full", "half"):
            warn.append(f"{tag}: width must be full or half")
            b["width"] = "full"
        if b.get("width") == "half" and b["kind"] in ("brief", "views", "journey", "scope", "stories"):
            warn.append(f"{tag}: {b['kind']} beats need the full width")
            b["width"] = "full"
        if not b.get("lede"):
            warn.append(f"{tag}: missing lede (the one sentence that says what to see)")
        for key, lim in (("title", TITLE_WORDS), ("lede", LEDE_WORDS), ("body", BODY_WORDS)):
            if _words(b.get(key)) > lim:
                warn.append(f"{tag}: {key} has {_words(b.get(key))} words (aim for <= {lim})")
        pr_keys = [where] if where in prs else list(prs)
        for r in b.get("refs") or []:
            if "path" in r and not any(r["path"] in files[k] for k in pr_keys):
                warn.append(f"{tag}: ref path {r['path']} is not in the changed files")
            if "finding" in r and r["finding"] not in finding_ids:
                warn.append(f"{tag}: ref finding {r['finding']} not found")
        k = b["kind"]
        if k == "diagram" and not b.get("mermaid"):
            warn.append(f"{tag}: diagram needs mermaid")
        if k == "code":
            if not any(b.get("path") in files[p] for p in pr_keys):
                warn.append(f"{tag}: code path {b.get('path')} is not in the changed files")
            if not (isinstance(b.get("from"), int) and isinstance(b.get("to"), int) and b["to"] >= b["from"]):
                warn.append(f"{tag}: code needs integer from <= to (new-file lines)")
            else:
                from .behavior import window
                candidates = [f for p in pr_keys if b.get('pr') in (None, p)
                              for f in prs[p].get('files', []) if f.get('path') == b.get('path')]
                if candidates and not any(window(f, b.get('side', 'new'), b['from'], b['to']) for f in candidates):
                    warn.append(f"{tag}: no observed code in this range; the excerpt is unavailable")
        if k == "shape":
            lines = (b.get("text") or "").rstrip("\n").split("\n")
            if not b.get("text"):
                warn.append(f"{tag}: shape needs text")
            if b.get("form") not in SHAPE_FORMS:
                warn.append(f"{tag}: shape form should be one of {SHAPE_FORMS}")
            if len(lines) > SHAPE_LINES:
                warn.append(f"{tag}: shape has {len(lines)} lines (aim for <= {SHAPE_LINES}; keep only what the lede is about)")
            if b.get("diff") and any(l and l[0] not in "+- " for l in lines):
                warn.append(f"{tag}: with diff: true every line starts with '+', '-' or ' '")
            for n in b.get("notes") or []:
                if not (isinstance(n.get("line"), int) and 1 <= n["line"] <= len(lines)):
                    warn.append(f"{tag}: note line {n.get('line')} is outside the shape (1..{len(lines)})")
        if k == "code" and isinstance(b.get("from"), int) and isinstance(b.get("to"), int) and b["to"] - b["from"] + 1 > CODE_LINES:
            warn.append(f"{tag}: code excerpt has {b['to'] - b['from'] + 1} lines; show the shape instead "
                        f"(kind: shape) and keep code for the lines that matter")
        if k == "findings":
            missing = [x for x in b.get("ids") or [] if x not in finding_ids]
            if missing:
                warn.append(f"{tag}: unknown finding ids {missing}")
        diagrams = [("", b.get("mermaid"))] + [(f" lens {v.get('id', j + 1)}", v.get("mermaid")) for j, v in enumerate(b.get("views") or [])] \
            + [(f" {side}", (b.get(side) or {}).get("mermaid")) for side in ("before", "after") if isinstance(b.get(side), dict)]
        for where_, src in diagrams:
            warn += [f"{tag}{where_}: {x}" for x in mermaid_traps(src)]
        if k == "notice":
            items = b.get("items") or []
            if not 1 <= len(items) <= 3:
                warn.append(f"{tag}: notice holds 1-3 items, ranked by consequence")
            ids = {x.get("id") for x in beats or []}
            for j, it in enumerate(items):
                if it.get("tone", "risk") not in ("risk", "decision", "gap", "good"):
                    warn.append(f"{tag}: item {j + 1} tone must be risk|decision|gap|good")
                if _words(it.get("title")) > TITLE_WORDS or _words(it.get("text")) > LEDE_WORDS:
                    warn.append(f"{tag}: item {j + 1} is too long (title <= {TITLE_WORDS}, text <= {LEDE_WORDS} words)")
                if it.get("pr"):   # the explaining beat lives in that PR's chapter
                    if it["pr"] not in prs:
                        warn.append(f"{tag}: item {j + 1} pr {it['pr']!r} is not in this session")
                    elif it.get("beat") and it["beat"] not in {x.get("id") for x in prs[it["pr"]].get("story") or []}:
                        warn.append(f"{tag}: item {j + 1} points at unknown beat {it['beat']!r} in {it['pr']}")
                elif it.get("beat") and it["beat"] not in ids:
                    warn.append(f"{tag}: item {j + 1} points at unknown beat {it['beat']!r}")
        if k == "brief":
            paras = b.get("paragraphs") or []
            if not 1 <= len(paras) <= 4:
                warn.append(f"{tag}: brief needs 1-4 paragraphs")
            for j, para in enumerate(paras):
                para = para.get("text", "") if isinstance(para, dict) else para
                if _words(para) > PARAGRAPH_WORDS:
                    warn.append(f"{tag}: paragraph {j + 1} has {_words(para)} words (aim for <= {PARAGRAPH_WORDS})")
            labels = {str(p.get("label", "")).strip().lower() for p in paras if isinstance(p, dict)}
            missing = [x for x in ("Why", "What", "How") if x.lower() not in labels]
            if missing:   # the overview swaps the one-liner for each of these
                warn.append(f"{tag}: label the brief's paragraphs Why, What and How (missing: {', '.join(missing)})")
            for j, a in enumerate(b.get("assets") or []):
                if not isinstance(a, dict) or a.get("kind") not in ("prd", "tickets", "deck", "prototype"):
                    warn.append(f"{tag}: asset {j + 1} needs kind prd, tickets, deck or prototype")
                elif not str(a.get("url") or "").startswith("https://"):
                    warn.append(f"{tag}: asset {j + 1} ({a['kind']}) needs an https:// url")
            for c in b.get("contributions") or []:
                if c.get("pr") not in prs and not PR_KEY.match(c.get("pr") or ""):
                    warn.append(f"{tag}: contribution pr {c.get('pr')!r} is not owner/repo#123")
        if k == "views":
            vs = b.get("views") or []
            if not 2 <= len(vs) <= 4:
                warn.append(f"{tag}: views needs 2-4 lenses (one lens is a diagram beat)")
            for j, v in enumerate(vs):
                v.setdefault("id", f"v{j + 1}")
                if not v.get("label") or not v.get("question"):
                    warn.append(f"{tag}: lens {v['id']} needs a label and the question it answers")
                if not (v.get("mermaid") or (v.get("shape") or {}).get("text")):
                    warn.append(f"{tag}: lens {v['id']} needs mermaid or shape.text")
                if _words(v.get("lede")) > LENS_LEDE_WORDS:
                    warn.append(f"{tag}: lens {v['id']} lede has {_words(v.get('lede'))} words (aim for <= {LENS_LEDE_WORDS})")
        if k == "notice":
            for j, it in enumerate(b.get("items") or []):
                warn += plain_layer(f"{tag} item {j + 1}", f"{it.get('title', '')} {it.get('text', '')}", repos)
        if k == "brief":
            warn += plain_layer(f"{tag} lede", b.get("lede"), repos)
            for j, para in enumerate(b.get("paragraphs") or []):
                warn += plain_layer(f"{tag} paragraph {j + 1}", para if isinstance(para, str) else para.get("text"), repos)
        if k == "flow" and b.get("skip"):   # the skill decided nothing moves through this change
            b = {"id": b["id"], "kind": "flow", "skip": str(b["skip"])[:240], "weight": "normal", "width": "full"}
            warn = [w for w in warn if not w.startswith(f"{tag}: missing lede")]
        elif k == "flow":
            warn += plain_layer(f"{tag} lede", b.get("lede"), repos)
            for j, a in enumerate(b.get("answers") or []):
                warn += plain_layer(f"{tag} answer {j + 1}", f"{a.get('q') or ''} {a.get('a') or ''}", repos)
            hops, answers = b.get("hops") or [], b.get("answers") or []
            if not 3 <= len(hops) <= 14:
                warn.append(f"{tag}: flow needs 3-14 hops (the one thing that moves, end to end), or skip with why")
            for j, h in enumerate(hops):
                if not (h.get("from") and h.get("to") and h.get("carries")):
                    warn.append(f"{tag}: hop {j + 1} needs from, to and carries (what crosses the arrow, by field)")
                bad = [x for x in h.get("prs") or [] if x not in prs and not PR_KEY.match(x)]
                if bad:
                    warn.append(f"{tag}: hop {j + 1} has bad PR keys {bad} (use owner/repo#123)")
            dif = b.get("differs") or {}
            if dif:
                rows = dif.get("rows") or []
                if not (dif.get("usual") and dif.get("this")) or not 2 <= len(rows) <= 8:
                    warn.append(f"{tag}: differs needs usual, this and 2-8 rows of {{aspect, usual, this}}")
                for j, r in enumerate(rows):
                    if not (r.get("aspect") and r.get("usual") and r.get("this")):
                        warn.append(f"{tag}: differs row {j + 1} needs aspect, usual and this")
                    warn += plain_layer(f"{tag} differs row {j + 1}", f"{r.get('usual', '')} {r.get('this', '')}", repos)
            decs = b.get("decisions") or []
            if decs and not 2 <= len(decs) <= 4:
                warn.append(f"{tag}: 2-4 key decisions (the ones a newcomer would question)")
            for j, x in enumerate(decs):
                if not (x.get("decision") and x.get("why")):
                    warn.append(f"{tag}: decision {j + 1} needs decision and why (and instead: the road not taken)")
                warn += plain_layer(f"{tag} decision {j + 1}", f"{x.get('decision', '')} {x.get('instead', '')} {x.get('why', '')}", repos)
            for j, c in enumerate(b.get("contracts") or []):
                if not (c.get("contract") and c.get("change") and c.get("affects")):
                    warn.append(f"{tag}: contract {j + 1} needs contract, change and affects (all, new, or who)")
                bad = [x for x in c.get("prs") or [] if x not in prs and not PR_KEY.match(x)]
                if bad:
                    warn.append(f"{tag}: contract {j + 1} has bad PR keys {bad} (use owner/repo#123)")
            if len(answers) > 3:
                warn.append(f"{tag}: at most 3 answers (the first questions a newcomer asks)")
            for j, a in enumerate(answers):
                if not (a.get("q") and a.get("a")):
                    warn.append(f"{tag}: answer {j + 1} needs q and a")
                elif _words(a["a"]) > ANSWER_WORDS:
                    warn.append(f"{tag}: answer {j + 1} has {_words(a['a'])} words (aim for <= {ANSWER_WORDS}; the hops hold the detail)")
        if k in ("journey", "scope"):
            rows = b.get("steps" if k == "journey" else "items") or []
            if not rows:
                warn.append(f"{tag}: {k} needs {'steps' if k == 'journey' else 'items'}")
            for r in rows:
                keys = r.get("prs", []) if k == "journey" else list((r.get("by") or {}))
                # PRs outside the session (other repos of the same feature) are fine as owner/repo#123
                bad = [x for x in keys if x not in prs and not PR_KEY.match(x)]
                if bad:
                    warn.append(f"{tag}: bad PR keys {bad} (use owner/repo#123)")
                if k == "journey" and r.get("status", "changed") not in ("new", "changed", "unchanged", "gap"):
                    warn.append(f"{tag}: journey status must be new|changed|unchanged|gap")
        if k == "stories":
            items = b.get("items") or []
            if not 1 <= len(items) <= 8:
                warn.append(f"{tag}: stories holds 1-8 items (the ones a reviewer must keep in mind)")
            for j, it in enumerate(items):
                it.setdefault("id", f"s{j + 1}")
                t = f"{tag} story {it['id']}"
                if it.get("for", "user") not in STORY_FOR:
                    warn.append(f"{t}: for must be {'|'.join(STORY_FOR)}")
                if not (it.get("as") and it.get("want")):
                    warn.append(f"{t}: needs as and want (\"As a <as>, I want <want>, so that <so_that>\")")
                if it.get("status", "delivered") not in STORY_STATUS:
                    warn.append(f"{t}: status must be {'|'.join(STORY_STATUS)}")
                bad = [x for x in it.get("prs") or [] if x not in prs and not PR_KEY.match(x)]
                if bad:
                    warn.append(f"{t}: bad PR keys {bad} (use owner/repo#123)")
                src = it.get("source") or {}
                if src.get("kind") not in STORY_SOURCES:
                    warn.append(f"{t}: source.kind must be {'|'.join(STORY_SOURCES)} (say where the story comes from)")
                for c in it.get("checks") or []:
                    if c.get("status", "done") not in ("done", "partial", "missing"):
                        warn.append(f"{t}: check status must be done|partial|missing")
        if k == "media":
            warn += _check_media(b, tag, sdir)
        if k == "before_after":
            for side in ("before", "after"):
                s = b.get(side) or {}
                if not any(s.get(x) for x in ("mermaid", "code", "media", "text")):
                    warn.append(f"{tag}: {side} needs mermaid, code, media or text")
                if s.get("media"):
                    warn += _check_media({"src": s["media"]}, f"{tag} {side}", sdir)
        out.append(b)
    told = [b for b in out if b["kind"] != "stories"]   # the stories list is reference, not part of the told story
    if len(told) > 8:
        warn.append(f"{where}: {len(told)} beats; a story over 8 beats stops being a story")
    if out and not any(b.get("weight") == "lead" for b in out):
        out[0]["weight"] = "lead"
    return out, warn


def missing_flow(beats: list[dict]) -> list[str]:
    """Every review decides how it works for a newcomer: a flow beat, or one that says why it needs none."""
    if not any(b.get("kind") == "flow" for b in beats or []):   # an empty story hasn't decided either
        return ["session story: no flow beat. Decide how this change works for a newcomer: follow the one thing that "
                "moves through it (storytelling.md §2 1a), or write {\"kind\": \"flow\", \"skip\": \"why it needs none\"}"]
    return []


def mermaid_traps(src) -> list[str]:
    """A ';' inside an unquoted label ends Mermaid's statement there. Between statements it's fine, and so is an
    entity code like #59; or a quoted label."""
    out = []
    if not isinstance(src, str):
        return out
    for n, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("%%"):
            continue
        bare = re.sub(r"#\w+;", "", re.sub(r'"[^"]*"', '""', line))
        labels = re.findall(r"\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|\|([^|]*)\|", bare)
        message = re.search(r"(?:-{1,2}>>?|-{1,2}x|-{1,2}\)|--?>)[^:]*:(.*)$", bare)   # a sequence diagram's message text
        if any(";" in "".join(g) for g in labels) or (message and ";" in message.group(1)):
            out.append(f"mermaid line {n} has ';' inside a label, which ends the statement there: use ',' or quote the label")
    return out


def _check_media(b: dict, tag: str, sdir: Path) -> list[str]:
    src = b.get("src") or ""
    if src.startswith(("http://", "https://")):
        return []
    root = (sdir / "media").resolve()
    p = (root / src).resolve()
    if p == root or not p.is_relative_to(root):   # same rule as the server's media route
        return [f"{tag}: media src must stay inside the session's media/ directory"]
    if not p.exists():
        return [f"{tag}: media file media/{src} does not exist"]
    if p.suffix.lower() not in MEDIA_EXT:
        return [f"{tag}: unsupported media type {p.suffix}"]
    b.setdefault("type", MEDIA_EXT[p.suffix.lower()])
    return []

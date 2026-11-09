"""Turn recorded review events into memory.

Deterministic first pass. The skill may refine wording afterwards (SKILL.md step 6),
but rules and evidence counts come from here so they stay auditable.
"""
from __future__ import annotations

import json
import threading
from collections import Counter, defaultdict
from pathlib import Path

from .memory import AMR, OKF, Bullet
from .util import mem_path, memory_on, session_config, today

BLOCKING = {"blocking", "bug", "security"}
_RUN = threading.Lock()   # one Make memories at a time in this process (the server is threaded)


def path_glob(path: str | None) -> str:
    if not path:
        return "**"
    parts = path.split("/")
    if any(p.startswith("test") or p in ("__tests__", "spec") for p in parts[:-1]) or parts[-1].startswith("test_"):
        return "**/test*/**" if len(parts) > 1 else "test_*"
    return "/".join(parts[:-1][:2]) + "/**" if len(parts) > 1 else "*"


def beat_form(target: dict) -> str | None:
    """Sub-form of a story beat, e.g. the mermaid type of a diagram ('sequenceDiagram')."""
    f = target.get("form")
    return f if f and all(c.isalnum() or c in "-_" for c in f) else None


FOLDS = {"rbk": "How to roll back", "rdec": "How it was decided", "reff": "Review effort", "rappr": "Auto-approval",
         "rrev": "Who should review", "fdif": "What's different", "fdec": "Key decisions", "fcon": "Contract changes",
         "flow": "How it works, step by step", "fwhy": "Why it's built"}


def e_label(fid: str) -> str:
    return FOLDS.get(fid, fid)


def slug_kind(kind) -> str:
    k = "-".join(str(kind or "").lower().split())
    return k if k and all(c.isalnum() or c == "-" for c in k) else ""


def load_events(sdir: Path) -> list[dict]:
    p = sdir / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def latest_state(events: list[dict]) -> list[dict]:
    """Collapse toggles: the last mark/verdict per (type, target, emoji) wins; `undo` removes."""
    keep: dict[tuple, dict] = {}
    seq = []
    for e in events:
        t = e.get("type")
        tgt = json.dumps([e.get('pr'), e.get("target")], sort_keys=True)
        if t == "mark":
            k = ("mark", tgt, e.get("emoji"))
            if e.get("undo"):
                keep.pop(k, None)
            else:
                keep[k] = e
        elif t == "finding_verdict":
            if e.get("verdict") in ("accept", "dismiss"):
                keep[("verdict", tgt)] = e
            else:
                keep.pop(("verdict", tgt), None)
        elif t == "note" and e.get("undo"):
            keep.pop(("note", e.get("note_id")), None)
        elif t == "note":
            keep[("note", e.get("note_id") or e.get("github_id") or len(seq))] = e
        else:
            seq.append(e)
    return list(keep.values()) + seq


def distill(sdir: Path, cfg: dict | None = None) -> dict:
    """Make memories from one session. One run at a time per memory folder (a click and a `cockpit finish` can
    overlap), since each run reads the credit ledger, writes evidence, then writes the ledger."""
    cfg = cfg or session_config(sdir)
    if not memory_on(cfg):
        raise RuntimeError("Memory is off (config memory.enabled), so there is nothing to make memories into.")
    root = mem_path(cfg, "amr")
    root.mkdir(parents=True, exist_ok=True)
    with open(_lock_path(root), "a+") as lock:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)   # released when the file closes
        except ImportError:   # no fcntl (Windows): the server's lock below still serializes its own requests
            pass
        with _RUN:
            return _distill(sdir, cfg)


def _lock_path(root: Path) -> Path:
    """Where a memory folder's run lock lives: outside it (memory's auto-commit never stages it), in a folder only
    this user can write, so another user on the machine can't create the lock first and block Make memories."""
    import getpass, hashlib, os, tempfile
    who = str(os.getuid()) if hasattr(os, "getuid") else getpass.getuser()
    d = Path(tempfile.gettempdir()) / f"review-cockpit-{who}"
    d.mkdir(mode=0o700, exist_ok=True)
    st = d.stat()
    if hasattr(os, "getuid") and (st.st_uid != os.getuid() or st.st_mode & 0o077):
        raise RuntimeError(f"{d} isn't private to you (someone else made it, or others can write in it); remove it and try again")
    return d / f"memory-{hashlib.sha1(str(root.resolve()).encode()).hexdigest()[:12]}.lock"


def _distill(sdir: Path, cfg: dict) -> dict:
    data = json.loads((sdir / "review-data.json").read_text())
    session = data["session"]
    src = f"session:{session}"
    events = latest_state(load_events(sdir))
    if not memory_on(cfg):
        raise RuntimeError("Memory is off (config memory.enabled), so there is nothing to make memories into.")
    amr, okf = AMR(mem_path(cfg, "amr")), OKF(mem_path(cfg, "okf"))
    amr.ensure(cfg.get("reviewer") or data.get("reviewer") or "reviewer"); okf.ensure()
    emoji = cfg["emoji"]
    entries = [(pr['key'], f) for pr in data['prs'] for f in pr.get('findings', [])]
    counts = Counter(f['id'] for _, f in entries)
    findings = {(key, f['id']): f for key, f in entries}
    unambiguous = {f['id']: f for _, f in entries if counts[f['id']] == 1}
    def event_finding(event, fid=None):
        if not fid and event.get('type') != 'finding_verdict' and (event.get('target') or {}).get('kind') != 'finding':
            return None
        fid = fid or (event.get('target') or {}).get('id')
        return findings.get((event.get('pr'), fid)) if event.get('pr') else unambiguous.get(fid)
    results = {"amr": [], "okf": [], "review_log": None}
    ledger_path = amr.root / ".credited.json"   # what each session already counted, so Make memories can run again safely
    try:
        ledger = json.loads(ledger_path.read_text())
    except (OSError, ValueError):
        ledger = {}
    credited = ledger.get(session) if isinstance(ledger.get(session), dict) else {}

    drafted = lambda type_, title: any(c.meta.get("type") == type_ and (c.meta.get("title") or "") == title for c in okf.concepts())
    pending: dict[str, list] = {}   # key -> [text, file, rule, evidence this review]: one credit per key, written at the end

    def add(text, file, rule=None, evidence=1):
        key = rule or text.lower()
        if key in pending:
            pending[key][3] += evidence
        else:
            pending[key] = [text, file, rule, evidence]

    def flush():
        for key, (text, file, rule, total) in pending.items():
            new = total - int(credited.get(key, 0))   # only what this review adds since its last Make memories
            if new <= 0:
                continue
            credited[key] = total
            meta = {"source": src, "added": today(), "rule": rule, "evidence": str(new)}
            results["amr"].append({"text": text, "rule": rule, "evidence": new,
                                   "result": amr.upsert(Bullet(text, meta, f"preferences/{file}.md"))})

    # 1) Qodo finding verdicts
    dismiss, accept = Counter(), Counter()
    for e in events:
        if e.get("type") != "finding_verdict":
            continue
        f = event_finding(e)
        if not f or e.get("verdict") not in ("accept", "dismiss"):
            continue
        key = (f["category"], path_glob(f.get("path")))
        (dismiss if e.get("verdict") == "dismiss" else accept)[key] += 1
    for (cat, glob), n in dismiss.items():
        add(f"Dismisses Qodo {cat} findings in `{glob}`", "findings", f"collapse category={cat} path={glob}", n)
    for (cat, _glob), n in accept.items():
        add(f"Acts on Qodo {cat} findings", "findings", f"prioritize category={cat}", n)

    # 2) Emoji marks on findings and panels
    for e in events:
        if e.get("type") != "mark":
            continue
        meaning = (emoji.get(e.get("emoji")) or {}).get("meaning")
        tgt = e.get("target") or {}
        if tgt.get("kind") == "finding" and event_finding(e):
            cat = event_finding(e)["category"]
            if meaning in BLOCKING:
                add(f"Treats {cat} findings as blocking", "findings", f"prioritize category={cat}")
            elif meaning == "nit":
                add(f"Considers {cat} findings nits", "findings", f"collapse category={cat}")
            elif meaning == "not_useful":
                add(f"Finds Qodo {cat} findings unhelpful", "findings", f"collapse category={cat}")
        elif tgt.get("kind") == "beat" and tgt.get("beat_kind"):
            form = beat_form(tgt)
            what = f"{form} {tgt['beat_kind']}" if form else tgt["beat_kind"]
            rule_tail = f"kind={tgt['beat_kind']}" + (f" form={form}" if form else "")
            if meaning in ("useful", "praise"):
                add(f"Finds {what} beats useful in the review story", "story", f"prefer-beat {rule_tail}")
            elif meaning == "not_useful":
                add(f"Finds {what} beats unhelpful in the review story", "story", f"avoid-beat {rule_tail}")
        elif tgt.get("kind") == "panel":
            if meaning in ("useful", "praise"):
                add(f"Finds the {tgt['id']} panel useful", "layout", f"boost panel={tgt['id']}")
            elif meaning == "not_useful":
                add(f"Finds the {tgt['id']} panel unhelpful", "layout", f"demote panel={tgt['id']}")

    # 2a) A typed note on a finding (the style pages mark that way): 🧹 is a nit, 🐛 🚫 🔒 treat it as blocking
    nits, blockers = Counter(), Counter()
    for e in events:
        f = event_finding(e, e.get('finding_id')) if e.get("type") == "note" else None
        meaning = (emoji.get(e.get("emoji")) or {}).get("meaning") if f else None
        if meaning == "nit":
            nits[f["category"]] += 1
        elif meaning in BLOCKING:
            blockers[f["category"]] += 1
    for cat, n in nits.items():
        add(f"Considers {cat} findings nits", "findings", f"collapse category={cat}", n)
    for cat, n in blockers.items():
        add(f"Treats {cat} findings as blocking", "findings", f"prioritize category={cat}", n)

    # 2b) Folds the reviewer opens though they start closed (or closes though they start open): the layout to start with
    opens, closes = Counter(), Counter()
    for e in events:
        fid = e.get("id") if e.get("type") == "fold" else None
        if fid not in FOLDS:   # only the page-wide folds; a finding's or a review's own question folds don't generalize
            continue
        if e.get("open") and not e.get("default_open"):
            opens[fid] += 1
        elif not e.get("open") and e.get("default_open"):
            closes[fid] += 1
    for fid, n in opens.items():
        add(f"Opens the {e_label(fid)} fold", "layout", f"open-fold id={fid}", n)
    for fid, n in closes.items():
        add(f"Closes the {e_label(fid)} fold", "layout", f"close-fold id={fid}", n)

    # 2c) What the reviewer asks Qodo about: the subject's kind, so the next brief can answer it up front
    asked = Counter(slug_kind((e.get("about") or {}).get("kind")) for e in events if e.get("type") == "ask")
    for kind, n in asked.items():
        if kind:
            add(f"Asks Qodo about {kind.replace('-', ' ')} items", "story", f"ask-about kind={kind}", n)

    # 2d) A decision the reviewer accepts is knowledge about the code: a draft for the next PR on those paths
    for e in events:
        if e.get("type") == "note" and e.get("decision") == "accept" and e.get("decision_text"):
            title = e["decision_text"][:70]
            if drafted("Decision", title):
                continue
            paths = [p for p in (e.get("decision_paths") or [e.get("path")]) if isinstance(p, str) and p][:20]
            c = okf.propose(type_="Decision", title=title, body=e["decision_text"], paths=paths,
                            by="cockpit/distill", sources=[{"resource": e.get("pr") or src}])
            results["okf"].append(c.path)

    # 3) What gets opened first, where time goes
    first_panel: dict[str, str] = {}
    dwell = Counter()
    for e in events:
        if e.get("type") == "view" and e.get("pr") and e.get("panel") and e.get("pr") not in first_panel:
            first_panel[e["pr"]] = e["panel"]
        if e.get("type") == "dwell" and e.get("panel"):
            dwell[e["panel"]] += int(e.get("ms", 0))
    for panel, n in Counter(first_panel.values()).items():
        add(f"Opens the {panel} panel first", "layout", f"open-first panel={panel}", n)
    if dwell:
        top, ms = dwell.most_common(1)[0]
        if ms > 60_000:
            add(f"Spends most review time in the {top} panel", "layout")

    # 3a) Which lens of a multi-view beat the reviewer opens (architecture, data flow, ...)
    lenses = Counter((e.get("lens") or "").strip().lower() for e in events if e.get("type") == "lens" and e.get("lens"))
    for lens, n in lenses.items():
        if all(c.isalnum() or c in " -_/" for c in lens):
            add(f"Opens the {lens} view of a change", "story", f"prefer-lens name={lens.replace(' ', '-')}", n)

    # 3c) What the reviewer opens although it was marked skim or skip: promote that reason next time
    opened = Counter((e.get("target") or {}).get("reason") for e in events if e.get("type") == "attention_opened")
    for reason, n in opened.items():
        if reason and all(c.isalnum() or c in " ,-_/" for c in reason):
            add(f"Opens {reason} code even when it is marked for skimming", "story",
                f"attention reason={reason.replace(' ', '-')} tier=review", n)

    # 3b) How much of each story gets read: beats seen vs beats offered
    seen = defaultdict(set)
    for e in events:
        if e.get("type") == "beat_seen" and e.get("pr"):
            seen[e["pr"]].add((e.get("target") or {}).get("id"))
    lengths = [(len(seen[p["key"]]), len(p.get("story") or [])) for p in data["prs"] if p.get("story")]
    if lengths and sum(t for _, t in lengths) >= 4:
        ratio = sum(s for s, _ in lengths) / sum(t for _, t in lengths)
        if ratio < 0.5:
            add("Reads only the opening of long review stories; keep stories short", "story", "story-length max=3")

    # 4) Notes: remember: -> AMR, fact: -> OKF draft, everything -> review log
    log_lines = defaultdict(list)
    for e in events:
        if e.get("type") == "note":
            text = (e.get("text") or "").strip()
            low = text.lower()
            if low.startswith("remember:"):
                add(text.split(":", 1)[1].strip(), "general")
            elif low.startswith("fact:") and not drafted("Fact", text.split(":", 1)[1].strip()[:70]):
                fact = text.split(":", 1)[1].strip()   # (a fact already drafted, by an earlier Make memories, isn't drafted twice)
                paths = [e["path"]] if e.get("path") else []
                c = okf.propose(type_="Fact", title=fact[:70], body=fact, paths=paths,
                                by=f"cockpit/distill", sources=[{"resource": e.get("url") or src}])
                results["okf"].append(c.path)
            where = (e.get("target") or {}).get("id", "")
            em = e.get("emoji") or ""
            origin = e.get("source", "app")
            posted = " (posted)" if e.get("posted") else ""
            log_lines[e.get("pr", "general")].append(
                f"- {em + ' ' if em else ''}{text.splitlines()[0][:200] if text else '(empty)'} "
                f"[source: {e.get('url') or src}; target: {where}; via: {origin}{posted}]")
        elif e.get("type") == "mark":
            m = (emoji.get(e.get("emoji")) or {}).get("label", e.get("emoji"))
            tgt = e.get("target") or {}
            what = event_finding(e)["title"] if tgt.get("kind") == "finding" and event_finding(e) else f"`{tgt.get('id')}`"
            log_lines[e.get("pr", "general")].append(
                f"- {e.get('emoji')} {m} on {tgt.get('kind')}: {what} [source: {src}; via: {e.get('source', 'app')}]")
        elif e.get("type") == "finding_verdict":
            f = event_finding(e) or {}
            log_lines[e.get("pr", "general")].append(
                f"- {e.get('verdict')} Qodo {f.get('category', '?')} finding: {f.get('title', e['target']['id'])} [source: {src}]")
        elif e.get("type") == "ask":
            q = (e.get("q") or "").strip().splitlines()[0][:200] if e.get("q") else ""
            about = (e.get("about") or {}).get("title")
            if q:
                log_lines["general"].append(f"- asked Qodo: {q}{f' (about {about})' if about else ''} [source: {src}]")
        elif e.get("type") == "verdict" and e.get("pr"):
            log_lines[e["pr"]].append(f"- verdict: {e.get('verdict') or 'cleared'} [source: {src}]")
        elif e.get("type") == "okf_verdict":
            log_lines[e.get("pr", "general")].append(
                f"- {e.get('verdict')} knowledge [[../okf/{e['target']['id'][:-3]}]] [source: {src}]")

    if log_lines:
        rel = f"reviews/{today()}-{session}.md"
        out = [f"# Review session {session}", f"- Reviewed {', '.join(p['key'] for p in data['prs'])} [source: {src}; added: {today()}]", ""]
        for pr, lines in log_lines.items():
            out += [f"## {pr}", *lines, ""]
        p = amr.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(out).rstrip() + "\n")
        _link_review(amr.root, rel)
        results["review_log"] = rel
    flush()
    okf.write_index()
    ledger[session] = credited
    ledger_path.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    return results


def _link_review(root: Path, rel: str):
    idx = root / "reviews.md"
    lines = idx.read_text().splitlines() if idx.exists() else ["# Review sessions"]
    link = f"- [[{rel[:-3]}]] [added: {today()}]"
    if not any(rel[:-3] in l for l in lines):
        lines.insert(1, link)
        idx.write_text("\n".join(lines) + "\n")

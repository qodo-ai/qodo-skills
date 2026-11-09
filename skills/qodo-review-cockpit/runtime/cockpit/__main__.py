"""CLI: python3 -m cockpit <command>

review   collect PRs (or --demo) and start the app
serve    start the app for an existing session
enrich   merge Claude-written summaries/diagrams/knowledge candidates into a session
note     add a note from a coding agent or terminal (appears live in the app)
mark     add an emoji mark from a coding agent or terminal
finish   distill a session into memory (same as the app's Finish button)
plan     print the review plan (must read / skim / skip with reasons); --json for other tools
refresh  re-collect a session's PRs (new commits, comments), keep notes, re-apply its enrich.json
export   write one self-contained HTML file of a session to share (no server needed)
styles   list the review styles (--style for review, serve and export)
dream    consolidate memory
validate check OKF conformance
"""
from __future__ import annotations

from pathlib import Path

import argparse
import json
import os
import secrets
import sys

from .styles import STYLES, names as style_names
from .util import SESSIONS, load_config, mem_path, memory_on, write_json

STYLE_HELP = "how the review reads: " + ", ".join(style_names()) + " (default: config 'style', else package)"


def _session_dir(name: str | None):
    if not name or name == "latest":
        p = SESSIONS / "latest"
        if not p.exists():
            sys.exit("No session yet. Run `python3 -m cockpit review ...` first.")
        name = p.read_text().strip()
    d = SESSIONS / name
    if not (d / "review-data.json").exists():
        sys.exit(f"Session {name} not found.")
    return d


def _warn_missing(sdir, style):
    from .styles import missing_content, require
    from .util import session_config
    msg = missing_content(require(style or session_config(sdir).get("style")), json.loads((sdir / "review-data.json").read_text()))
    if msg:
        print("note:", msg, file=sys.stderr)


def _target(spec: str, path: str | None, line: int | None) -> dict:
    if path and line:
        return {"kind": "line", "id": f"{path}:{line}", "label": f"{path}:{line}"}
    kind, _, ident = spec.partition(":")
    return {"kind": kind or "pr", "id": ident or spec}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cockpit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--product', action='store_true', help='managed Qodo reads; local review and export only')
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review"); r.add_argument("refs", nargs="*"); r.add_argument("--repo")
    r.add_argument("--demo", action="store_true"); r.add_argument("--port", type=int)
    r.add_argument("--no-open", action="store_true"); r.add_argument("--collect-only", action="store_true")
    r.add_argument("--style", choices=style_names(), help=STYLE_HELP)

    s = sub.add_parser("serve"); s.add_argument("--session"); s.add_argument("--port", type=int); s.add_argument("--no-open", action="store_true")
    s.add_argument("--style", choices=style_names(), help=STYLE_HELP)

    e = sub.add_parser("enrich"); e.add_argument("file"); e.add_argument("--session")

    for name in ("note", "mark"):
        n = sub.add_parser(name)
        n.add_argument("--session"); n.add_argument("--pr", required=True, help="owner/repo#123")
        n.add_argument("--target", default="pr", help="kind:id, e.g. finding:q-..., file:src/a.py, panel:diagram")
        n.add_argument("--path"); n.add_argument("--line", type=int)
        if name == "note":
            n.add_argument("--emoji"); n.add_argument("--post", action="store_true", help="queue for GitHub review")
            n.add_argument("text")
        else:
            n.add_argument("emoji"); n.add_argument("--undo", action="store_true")

    f = sub.add_parser("finish"); f.add_argument("--session")
    rf = sub.add_parser("refresh"); rf.add_argument("--session")
    rv = sub.add_parser("reviewers", help="suggest who should review: people who know the changed code, from read-only signals")
    rv.add_argument("--session"); rv.add_argument("--json", action="store_true")
    rr = sub.add_parser("risk-report", help="the work package's Merge Risk Report, for the coding agent: each scenario, its factors and what lowers it")
    rr.add_argument("--session"); rr.add_argument("--json", action="store_true")
    pl = sub.add_parser("plan"); pl.add_argument("--session"); pl.add_argument("--json", action="store_true")
    pl.add_argument("--pr", help="only this PR (number or owner/repo#n)")
    pl.add_argument("--code", action="store_true", help="print the changed lines of each block (for triage)")
    x = sub.add_parser("export"); x.add_argument("--session"); x.add_argument("--out")
    x.add_argument("--title", help="page name, e.g. 'Repo Access Filtering Review'")
    x.add_argument("--fragment", action="store_true", help="no html/head/body skeleton (for Claude Artifacts)")
    x.add_argument("--style", choices=style_names(), help=STYLE_HELP)
    x.add_argument("--with-styles", action="store_true", help="also write every other ready style next to it, linked from the style switcher")
    wk = sub.add_parser("walkthrough", help="the Work Package's Execution walkthrough and Finding review pages: check builder.json and triage pages, copy them into the session")
    wk.add_argument("--session"); wk.add_argument("--builder", help="builder.json (files, parts and flows)")
    wk.add_argument("--triage-dir", help="a folder of triage-<n>.html, triage-<n>.json and findings-<n>.json")
    wk.add_argument("--check", action="store_true", help="only report what's wrong; copy nothing")
    lc = sub.add_parser("local", help="local findings: what the author's `qodo review` found before the PR")
    lsub = lc.add_subparsers(dest="local_cmd", required=True)
    la = lsub.add_parser("add", help="keep a `qodo review --json` result for its PR (`-` reads stdin)")
    la.add_argument("file"); la.add_argument("--pr", help="owner/repo#123 (default: the PR of this repo's branch)")
    la.add_argument("--dir", help="the author's checkout, for its repo, branch and commit (default: here, unless here is the cockpit)")
    la.add_argument("--repo"); la.add_argument("--branch"); la.add_argument("--commit")
    lsub.add_parser("list", help="the local reviews kept, newest last")
    sub.add_parser("dream"); sub.add_parser("validate"); sub.add_parser("styles"); sub.add_parser("memory")
    sub.add_parser("home", help="where your reviews, memory and config live")
    st = sub.add_parser("style", help="your own review styles: recipes Focus draws, and the requests readers typed")
    ssub = st.add_subparsers(dest="scmd", required=True)
    ssub.add_parser("list", help="saved recipes")
    sr = ssub.add_parser("requests", help="what readers asked for in Describe it"); sr.add_argument("--all", action="store_true")
    sa = ssub.add_parser("add", help="check and save a recipe (JSON file, `-` reads stdin)")
    sa.add_argument("file"); sa.add_argument("--request", help="the request this recipe answers (closes it)")
    sa.add_argument("--replace", action="store_true", help="overwrite a saved style with the same id (default: save as a new one)")
    ssub.add_parser("blocks", help="the blocks a recipe can arrange")
    mg = sub.add_parser("migrate", help="copy this checkout's sessions, memory and config to a data home")
    mg.add_argument("--to", help="the data home (default ~/.qodo/review-cockpit)")
    a = ap.parse_args(argv)
    # This maintained distribution is the local-only product, including direct module invocations.
    if a.product or (Path(__file__).resolve().parents[2] / 'SKILL.md').is_file():
        from .product import activate
        activate()

    if a.cmd == "review":
        from .collect import collect, collect_demo
        from .server import serve
        if a.demo:
            session, sdir = collect_demo()
        elif a.refs:
            session, sdir = collect(a.refs, a.repo)
        else:
            sys.exit("Give PR refs or --demo.")
        print(f"Collected session {session} -> {sdir / 'review-data.json'}")
        if not a.collect_only:
            serve(sdir, a.port, not a.no_open, a.style)
    elif a.cmd == "serve":
        from .server import serve
        sdir = _session_dir(a.session)
        _warn_missing(sdir, a.style)
        serve(sdir, a.port, not a.no_open, a.style)
    elif a.cmd == "style":
        from . import recipes as R
        if a.scmd == "list":
            for r in R.load_all():
                print(f"{r['id']:24} {r['layout']:5} {' | '.join(t['label'] + ': ' + ','.join(t['blocks']) for t in r['tabs'])}")
        elif a.scmd == "requests":
            print(json.dumps(R.requests(open_only=not a.all), indent=2, ensure_ascii=False))
        elif a.scmd == "blocks":
            print(json.dumps({"blocks": R.BLOCKS, "layout": R.LAYOUTS, "density": R.DENSITIES, "accent": R.ACCENTS, "brief": R.BRIEF_VIEWS}, indent=2))
        else:
            from pathlib import Path as _P
            raw = sys.stdin.read() if a.file == "-" else _P(a.file).read_text()
            try:
                clean, notes = R.save(json.loads(raw), a.request, replace=a.replace)
            except ValueError as e:
                sys.exit(f"style: {e}")
            print(json.dumps({"saved": clean, "notes": notes}, indent=2))
    elif a.cmd == "styles":
        for k, v in STYLES.items():
            print(f"{k:9} {'ready  ' if v['ready'] else 'planned'}  {v['what']}")
    elif a.cmd == "enrich":
        from .enrich import enrich
        from .util import HOME
        f = Path(a.file)
        if not f.exists() and (HOME / f).exists():   # sessions/<id>/enrich.json, written in the data home
            f = HOME / f
        print(json.dumps(enrich(_session_dir(a.session), json.load(open(f))), indent=2))
    elif a.cmd == "reviewers":
        from .reviewers import suggest
        sd = _session_dir(a.session); p = sd / "review-data.json"
        res = suggest(json.loads(p.read_text()), load_config())   # slow: many lookups
        data = json.loads(p.read_text()); data["reviewers"] = res; write_json(p, data)   # re-read, so a save made meanwhile isn't undone
        if a.json:
            print(json.dumps(res, indent=2))
        else:
            for r in res["suggested"]:
                print(f"{r['login']}{' (weak)' if r['weak'] else ''}: {'; '.join(r['evidence'])}")
            print(f"({res['calls']} GitHub calls; left out: {', '.join(res['excluded'])})")
    elif a.cmd == "risk-report":
        from .view import view_data   # the page's rows, derived from the diff when the review wrote none
        r = view_data(_session_dir(a.session))["risk"]
        print(json.dumps(r, indent=2) if a.json else r["report"])
    elif a.cmd == "plan":
        from .attention import plan
        data = json.loads((_session_dir(a.session) / "review-data.json").read_text())
        prs = [p for p in data["prs"] if not a.pr or a.pr in (p["key"], str(p["number"]))]
        plans = [plan(p) for p in prs]
        files = {(p["key"], f["path"]): f for p in prs for f in p.get("files", [])}
        if a.json:
            print(json.dumps(plans, indent=2, ensure_ascii=False))
        else:
            for p in plans:
                s = p["summary"]
                print(f"{p['pr']}: deep-read {s.get('deep', 0)}, read {s.get('review', 0)} of {s.get('total', 0)} changed lines")
                for m in p["must_read"]:
                    deep = m["tier"] == "deep"
                    why = ", ".join(m["why_deep"]) if deep else m["reason"]
                    side = f" ({m['side']})" if m["side"] == "old" else ""
                    print(f"  {'deep' if deep else 'read':5} {m['path']}:{m['from']}-{m['to']}{side}  {m['lines']} lines  {why}" + (f"  [{m['layer']}]" if m["layer"] else ""))
                    if a.code:
                        f = files.get((p["pr"], m["path"])) or {}
                        mark, col = ("+", 2) if m["side"] == "new" else ("-", 1)
                        for h in f.get("hunks", []):
                            for l in h["lines"]:
                                if l[0] == mark and m["from"] <= l[col] <= m["to"]:
                                    print(f"      {l[col]:5} {l[0]} {l[3]}")
                for g in p["safe_to_skip"]:
                    print(f"  {g['tier']:5} {g['lines']:5} lines  {g['reason']}  ({g['evidence']})")
    elif a.cmd == "refresh":
        from .collect import refresh
        print(json.dumps(refresh(_session_dir(a.session)), indent=2))
    elif a.cmd == "export":
        from .export import export
        sdir = _session_dir(a.session)
        _warn_missing(sdir, a.style)
        more = []
        out = export(sdir, Path(a.out) if a.out else None, fragment=a.fragment, title=a.title, style=a.style,
                     with_styles=a.with_styles, written=more)
        print(f"Shared snapshot: {out} ({out.stat().st_size // 1024} KB)")
        for f in more:
            print(f"  with: {f} ({f.stat().st_size // 1024} KB)")
    elif a.cmd == "walkthrough":
        from .walkthrough import attach, check_files
        sdir = _session_dir(a.session)
        data = json.loads((sdir / "review-data.json").read_text())
        bf, td = Path(a.builder) if a.builder else None, Path(a.triage_dir) if a.triage_dir else None
        builder, triage, warn = check_files(sdir, data, bf, td)
        for w in warn:
            print("warning: " + w)
        if builder:
            print(f"builder: {len(builder['files'])} files, {sum(len(f['methods']) for f in builder['files'])} parts, {len(builder.get('flows') or [])} flows")
        if triage:
            print("triage: " + ", ".join(f"{t['pr']} ({t['counts']['open']} open)" for t in triage))
        if not a.check and (bf or td):
            attach(sdir, bf, td)
            print(f"Copied into {sdir.name}: the Work Package shows Execution walkthrough and Finding review on the next load")
    elif a.cmd in ("note", "mark"):
        from .server import append_events
        sdir = _session_dir(a.session)
        data = json.loads((sdir / "review-data.json").read_text())
        ev = {"type": a.cmd, "pr": a.pr, "target": _target(a.target, a.path, a.line), "path": a.path, "line": a.line}
        if a.cmd == "note":
            ev.update({"text": a.text, "emoji": a.emoji, "post": a.post, "note_id": "n-" + secrets.token_hex(4)})
        else:
            ev.update({"emoji": a.emoji, "undo": a.undo})
        append_events(sdir, [ev], data["session"], source="agent")
        print(f"Recorded {a.cmd} on {a.pr} ({ev['target']['kind']}:{ev['target']['id']})")
    elif a.cmd == "finish":
        from .distill import distill
        from .memory import git_commit
        from .util import session_config
        sdir = _session_dir(a.session)
        cfg = session_config(sdir)
        if not memory_on(cfg):
            sys.exit("Memory is off (config memory.enabled); nothing to finish.")
        print(json.dumps(distill(sdir, cfg), indent=2, ensure_ascii=False))
        if cfg["memory"].get("auto_commit"):
            print(git_commit([mem_path(cfg, "amr"), mem_path(cfg, "okf")], f"memory: review session {sdir.name}"))
    elif a.cmd == "local":
        from .adapters import qodo_local
        if a.local_cmd == "add":
            try:
                result = json.load(sys.stdin if a.file == "-" else open(a.file))
                rec = qodo_local.add(result, pr=a.pr, repo=a.repo, branch=a.branch, commit=a.commit, cwd=a.dir or os.getcwd())
            except (OSError, ValueError) as e:
                sys.exit(f"local add: {e}")
            if "qodo_local" not in (load_config().get("adapters") or []):
                print("note: your config's `adapters` leaves out qodo_local, so reviews won't show these; add it", file=sys.stderr)
            n = qodo_local.count(rec["result"])
            print(f"Kept local review {rec['local_review_id']} ({n} finding{'s' * (n != 1)}) for "
                  f"{rec['pr'] or rec['repo'] + ' ' + rec['branch']}; `refresh` shows it in an open session")
        else:
            for r in qodo_local.records():
                print(f"{r.get('added_at')}  {r.get('local_review_id')}  {r.get('pr') or (r.get('repo') or '?') + ' ' + (r.get('branch') or '?')}"
                      f"  {qodo_local.count(r['result'])} findings")
    elif a.cmd == "dream":
        from .dream import dream
        print(json.dumps(dream(), indent=2, ensure_ascii=False))
    elif a.cmd == "memory":   # where memory lives, or that it's off (the skill reads this first)
        cfg = load_config()
        print(json.dumps({"enabled": memory_on(cfg), "amr": str(mem_path(cfg, "amr")), "okf": str(mem_path(cfg, "okf")),
                          "threshold": cfg["distill"]["dismiss_threshold"]}, indent=2))
    elif a.cmd == "home":
        from .home import describe
        print(json.dumps(describe(), indent=2))
    elif a.cmd == "migrate":
        from .home import migrate
        out = migrate(Path(a.to) if a.to else None)
        print(json.dumps(out, indent=2))
        sys.exit(1 if out.get("error") else 0)
    elif a.cmd == "validate":
        from .memory import OKF
        probs = OKF(mem_path(load_config(), "okf")).validate()
        print("\n".join(probs) if probs else "OKF bundle conforms.")
        sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()

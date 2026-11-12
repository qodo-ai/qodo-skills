"""Other work on the same code: who else changes the lines this review's PRs change, and how close (the same lines,
the same function, or only the file). Sources, settings and closeness are described in the README ("Other work on
the same code"). A source that fails adds a warning; it never stops the review.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode

from .util import SESSIONS, gh, gh_json

NOISE = re.compile(r"(^|/)(CHANGELOG[^/]*|[^/]*\.lock|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|go\.sum|uv\.lock|poetry\.lock)$", re.I)
RANK = {"lines": 0, "function": 1, "file": 2}
SOURCE_RANK = {"merged": 0, "open_pr": 1, "agent": 2, "session": 3}   # live sources before snapshots
# Lines that say nothing about behavior: imports, re-exports, blank lines, closing brackets. Two changes that only
# touch these at the same place (the import block at the top of a file) are not a collision.
TRIVIAL = re.compile(r"^\s*(?:$|#|//|from\s+\S+\s+import\b|import\s|export\s+\*|export\s*\{|[\]\)\}],?;?$|[\w.]+,$|\"?\w+\"?,$|__all__\b|(?:const|let|var)\s+\w+\s*=\s*require\()")
DEFAULTS = {"enabled": True, "tolerance": 5, "max_diffs": 15, "max_paths": 25, "agent_max_age_days": 14,
            "sources": {"open_prs": True, "merged": True, "sessions": True, "agent_sessions": False},
            "agent_sources": ["checkpoints", "tracks"]}

_PRS_QUERY = """query($o:String!,$r:String!,$after:String){repository(owner:$o,name:$r){pullRequests(states:OPEN,first:50,after:$after,
orderBy:{field:UPDATED_AT,direction:DESC}){pageInfo{hasNextPage endCursor}nodes{number title url isDraft updatedAt headRefName baseRefName
author{login} files(first:100){totalCount nodes{path}}}}}}"""


def conf(cfg: dict) -> dict:
    o = {**DEFAULTS, **(cfg.get("overlaps") or {})}
    o["sources"] = {**DEFAULTS["sources"], **((cfg.get("overlaps") or {}).get("sources") or {})}
    return o



def func_of(header: str) -> str:
    """The enclosing function git puts after the second @@ ("def foo(", "class Bar"), normalized."""
    m = re.match(r"^@@[^@]*@@\s*(.*)$", header or "")
    return re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""


def spans(hunks: list[dict]) -> list[dict]:
    """Per hunk, where its changed lines sit in the base file (`old`), in the new file (`new`), and its function."""
    out = []
    for h in hunks:
        olds, news, last_old, texts = [], [], None, []
        for kind, o, n, *rest in h.get("lines") or []:
            if kind == " ":
                last_old = o
            elif kind == "-":
                olds.append(o); last_old = o; texts.append(rest[0] if rest else "")
            elif kind == "+":
                news.append(n); texts.append(rest[0] if rest else "")
                olds.append(last_old if last_old is not None else _hunk_old_start(h))   # an insertion sits after the line before it
        olds = [x for x in olds if x]   # 0: a new file has no place in the base
        if olds or news:
            out.append({"old": [min(olds), max(olds)] if olds else None, "new": [min(news), max(news)] if news else None,
                        "func": func_of(h.get("header", "")), "trivial": all(TRIVIAL.match(t or "") for t in texts)})
    return out


def _hunk_old_start(h: dict) -> int:
    m = re.match(r"^@@ -(\d+)", h.get("header", ""))
    return int(m.group(1)) if m else 1


def closeness(ours: list[dict], theirs: list[dict], tol: int, same_base: bool = True) -> tuple[str, dict | None, dict | None]:
    """(lines|function|file, our span, their span) for the closest pair of hunks. Line numbers only mean the same
    place on the same base branch; across bases the closest is the function."""
    best = ("file", None, None)
    for a in ours:
        for b in theirs:
            if a.get("trivial") and b.get("trivial"):   # both only touch imports or brackets
                continue
            if same_base and a["old"] and b["old"] and a["old"][0] - tol <= b["old"][1] and b["old"][0] - tol <= a["old"][1]:
                return "lines", a, b
            if best[0] == "file" and a["func"] and a["func"] == b["func"]:
                best = ("function", a, b)
    return best


def _patch_hunks(path: str, patch: str) -> list[dict]:
    from .collect import parse_diff   # late: collect imports this module
    return parse_diff(f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n{patch}").get(path, [])


def _ours(pr: dict, cap: int) -> dict[str, list[dict]]:
    """This PR's changed files worth comparing: not generated, lock or changelog files."""
    out = {}
    for f in pr.get("files") or []:
        if f.get("role") == "generated" or NOISE.search(f["path"]):
            continue
        sp = spans(f.get("hunks") or [])
        if sp:
            out[f["path"]] = sp
    return dict(list(out.items())[:cap])


def _hit(pr: dict, source: str, other: dict, path: str, ours_sp: list[dict], theirs_sp: list[dict], tol: int) -> dict:
    same_base = not other.get("base") or not pr.get("base") or other["base"] == pr["base"]
    close, a, b = closeness(ours_sp, theirs_sp, tol, same_base)
    return {"for": pr["key"], "source": source, **other, "path": path, "closeness": close,
            "ours": (a or {}).get("old"), "ours_new": (a or {}).get("new"), "theirs": (b or {}).get("old"),
            "function": (a or {}).get("func") if close == "function" else ((a or {}).get("func") or None)}



def open_prs(prs: list[dict], o: dict, warn: list[str]) -> list[dict]:
    from .collect import parse_diff
    out, mine = [], {p["key"] for p in prs}
    for repo in sorted({p["repo"] for p in prs}):
        owner, name = repo.split("/", 1)
        nodes, after = [], None
        try:
            for _ in range(10):   # 500 open PRs
                args = ["api", "graphql", "-f", f"query={_PRS_QUERY}", "-f", f"o={owner}", "-f", f"r={name}"] + (["-f", f"after={after}"] if after else [])
                page = ((json.loads(gh(args)).get("data") or {}).get("repository") or {}).get("pullRequests") or {}
                nodes += page.get("nodes") or []
                if not (page.get("pageInfo") or {}).get("hasNextPage"):
                    break
                after = page["pageInfo"]["endCursor"]
        except (RuntimeError, ValueError) as e:
            warn.append(f"overlaps: open PRs of {repo} unreadable ({str(e)[:120]})"); continue
        o.setdefault("_open", {})[repo] = {f"{repo}#{n['number']}" for n in nodes}   # live: lets sessions drop merged PRs
        ours = {p["key"]: _ours(p, o["max_paths"]) for p in prs if p["repo"] == repo}
        shared = []
        for n in nodes:
            key = f"{repo}#{n['number']}"
            if key in mine:
                continue
            fs = n.get("files") or {}
            paths = {x["path"] for x in fs.get("nodes") or []}
            if (fs.get("totalCount") or 0) > len(paths):   # more than one page of files: read them all
                try:
                    paths |= set(gh(["api", f"repos/{repo}/pulls/{n['number']}/files?per_page=100", "--paginate", "--jq", ".[].filename"]).splitlines())   # one path per line; paths may hold spaces
                except RuntimeError as e:
                    warn.append(f"overlaps: files of {key} beyond the first {len(paths)} unreadable ({str(e)[:80]})")
            hits = [(pk, path) for pk, files in ours.items() for path in files if path in paths]
            if hits:
                shared.append((n, hits))
        for n, hits in shared[:o["max_diffs"]]:   # newest first, as the query orders them
            try:
                theirs = parse_diff(gh(["pr", "diff", str(n["number"]), "--repo", repo]))
            except RuntimeError as e:
                warn.append(f"overlaps: diff of {repo}#{n['number']} unreadable ({str(e)[:80]})"); continue
            other = {"repo": repo, "number": n["number"], "key": f"{repo}#{n['number']}", "title": n.get("title"), "url": n.get("url"),
                     "author": (n.get("author") or {}).get("login"), "state": "draft" if n.get("isDraft") else "open", "updated_at": n.get("updatedAt"),
                     "head": n.get("headRefName"), "base": n.get("baseRefName")}
            for pk, path in hits:
                pr = next(p for p in prs if p["key"] == pk)
                out.append(_hit(pr, "open_pr", other, path, ours[pk][path], spans(theirs.get(path) or []), o["tolerance"]))
        for n, _ in shared[o["max_diffs"]:]:
            warn.append(f"overlaps: {repo}#{n['number']} shares files but wasn't compared (max_diffs {o['max_diffs']})")
    return out


def merged(prs: list[dict], o: dict, warn: list[str]) -> list[dict]:
    out, pr_of = [], {}
    for pr in prs:
        if str(pr.get("state") or "").upper() == "MERGED" or not pr.get("head_sha") or not pr.get("base"):
            continue
        repo = pr["repo"]
        try:
            cmp = gh_json(["api", f"repos/{repo}/compare/{pr['base']}...{pr['head_sha']}", "--jq", "{sha: .merge_base_commit.sha, at: .merge_base_commit.commit.committer.date}"]) or {}
        except RuntimeError as e:
            warn.append(f"overlaps: merge-base of {pr['key']} unknown ({str(e)[:80]})"); continue
        if not cmp.get("at"):
            continue
        added = _added_since(repo, cmp["sha"], pr["base"], warn)   # ancestry, not dates: what the base gained since
        since = _days_before(cmp["at"], 30) if added is not None else cmp["at"]   # commit dates can predate the merge-base
        for path, ours_sp in _ours(pr, o["max_paths"]).items():
            try:
                q = urlencode({"sha": pr["base"], "path": path, "since": since, "per_page": 100})   # a path may hold & or #
                commits = gh_json(["api", f"repos/{repo}/commits?{q}", "--paginate"]) or []
            except RuntimeError:
                continue
            for c in commits:
                if c.get("sha") == cmp.get("sha") or (added is not None and c.get("sha") not in added):
                    continue
                if c["sha"] not in pr_of:
                    try:
                        pulls = gh_json(["api", f"repos/{repo}/commits/{c['sha']}/pulls"]) or []
                        detail = gh_json(["api", f"repos/{repo}/commits/{c['sha']}"]) or {}
                    except RuntimeError:
                        pulls, detail = [], {}
                    # a commit also "belongs" to open PRs whose branch holds it: take only the PR that merged it here
                    landed = [x for x in pulls if x.get("merged_at") and ((x.get("base") or {}).get("ref") in (None, pr["base"]))]
                    pr_of[c["sha"]] = (landed[0] if landed else {}, {f["filename"]: f.get("patch") or "" for f in detail.get("files") or []})
                pull, patches = pr_of[c["sha"]]
                if pull.get("number") and f"{repo}#{pull['number']}" in {p["key"] for p in prs}:
                    continue
                other = {"repo": repo, "number": pull.get("number"), "key": f"{repo}#{pull['number']}" if pull.get("number") else None,
                         "title": pull.get("title") or (c.get("commit") or {}).get("message", "").split("\n")[0][:120],
                         "url": pull.get("html_url") or c.get("html_url"), "author": (pull.get("user") or {}).get("login"),
                         "state": "merged", "merged_at": pull.get("merged_at") or ((c.get("commit") or {}).get("committer") or {}).get("date"),
                         "commit": c["sha"][:12]}
                out.append(_hit(pr, "merged", other, path, ours_sp, spans(_patch_hunks(path, patches.get(path, ""))), o["tolerance"]))
    return out


def _added_since(repo: str, merge_base: str, base: str, warn: list[str]) -> set[str] | None:
    """The commits the base branch gained after the merge-base, or None when GitHub can't list them all."""
    try:
        out = gh(["api", f"repos/{repo}/compare/{merge_base}...{base}?per_page=100", "--paginate", "--jq", ".commits[].sha"]).split()
        total = gh_json(["api", f"repos/{repo}/compare/{merge_base}...{base}?per_page=1", "--jq", ".total_commits"])
    except RuntimeError as e:
        warn.append(f"overlaps: commits on {base} since the merge-base unreadable ({str(e)[:80]}); using dates")
        return None
    if isinstance(total, int) and total > len(out):
        warn.append(f"overlaps: {base} gained {total} commits since the merge-base; GitHub listed {len(out)}, using dates for the rest")
        return None
    return set(out)


def _days_before(iso: str, days: int) -> str:
    import datetime as _dt
    t = _dt.datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S") - _dt.timedelta(days=days)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_open(repo: str, number, o: dict) -> bool:
    """Whether a PR is open now, asked once per PR. Unknown is not open: a snapshot can't prove it."""
    cache = o.setdefault("_state", {})
    k = f"{repo}#{number}"
    if k not in cache:
        try:
            cache[k] = gh(["pr", "view", str(number), "--repo", repo, "--json", "state", "--jq", ".state"]).strip().upper() == "OPEN"
        except RuntimeError:
            cache[k] = False
    return cache[k]


def sessions(prs: list[dict], o: dict, warn: list[str], session: str | None) -> list[dict]:
    out, mine, latest = [], {p["key"] for p in prs}, {}
    for f in sorted(SESSIONS.glob("*/review-data.json"), key=lambda p: p.stat().st_mtime) if SESSIONS.is_dir() else []:
        if f.parent.name == session:
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for p in d.get("prs") or []:
            if p.get("key") not in mine and str(p.get("state") or "").upper() not in ("MERGED", "CLOSED"):
                latest[p["key"]] = (f.parent.name, p)   # the newest session that holds the PR wins
    for pr in prs:
        ours = _ours(pr, o["max_paths"])
        for sid, p in latest.values():
            if p.get("repo") != pr["repo"]:
                continue
            live = (o.get("_open") or {}).get(p["repo"])
            if live is not None and p["key"] not in live:   # merged or closed since that session: no longer other work
                continue
            if live is None and not _is_open(p["repo"], p.get("number"), o):   # no live list: ask, and drop unknowns
                continue
            for f in p.get("files") or []:
                if f["path"] in ours:
                    other = {"repo": p["repo"], "number": p.get("number"), "key": p["key"], "title": p.get("title"), "url": p.get("url"),
                             "author": p.get("author"), "state": "under review", "session": sid, "base": p.get("base")}
                    out.append(_hit(pr, "session", other, f["path"], ours[f["path"]], spans(f.get("hunks") or []), o["tolerance"]))
    return out



def _checkpoints(prs: list[dict], o: dict, warn: list[str]) -> list[dict]:
    """Diffs `qodo review` keeps on this machine (~/.qodo/review-checkpoints): an agent's reviewed change, by base sha."""
    from .collect import parse_diff
    root, out, belongs = Path.home() / ".qodo" / "review-checkpoints", [], {}
    cutoff = (time.time() - o["agent_max_age_days"] * 86400) * 1000
    for f in sorted(root.glob("*/*/*.json")) if root.is_dir() else []:
        try:
            cp = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not cp.get("diff") or (cp.get("submittedAt") or 0) < cutoff:
            continue
        theirs = parse_diff(cp["diff"])
        for pr in prs:
            ours = _ours(pr, o["max_paths"])
            shared = [p for p in theirs if p in ours]
            if not shared or _same_work(pr, theirs):
                continue
            k = (pr["repo"], cp.get("baseSha"))
            if k not in belongs:   # the checkpoint's repo is hashed; its base commit tells
                try:
                    gh(["api", f"repos/{pr['repo']}/commits/{cp.get('baseSha')}", "--jq", ".sha"]); belongs[k] = True
                except RuntimeError:
                    belongs[k] = False
            if not belongs[k]:
                continue
            other = {"repo": pr["repo"], "number": None, "key": None, "title": "a local qodo review (not a PR yet)",
                     "state": "agent session", "agent_source": "checkpoints", "base_sha": cp.get("baseSha"),
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(cp["submittedAt"] / 1000))}
            out += [_hit(pr, "agent", other, p, ours[p], spans(theirs[p]), o["tolerance"]) for p in shared]
    return out


def _same_work(pr: dict, theirs: dict) -> bool:
    """A checkpoint of this very PR's work, before it was a PR: most of its added lines are the PR's."""
    added = lambda files: {(p, l[3].strip()) for p, hs in files.items() for h in hs for l in h.get("lines") or [] if l[0] == "+" and l[3].strip()}
    a, b = added(theirs), added({f["path"]: f.get("hunks") or [] for f in pr.get("files") or []})
    return bool(a) and len(a & b) / len(a) >= 0.6


TRACKS_PAGES = 200    # find-tracks pages a record at a time
TRACKS_BUDGET = 60    # seconds for the whole lookup: other work is optional and never holds a review up for long


def _tracks(prs: list[dict], o: dict, warn: list[str]) -> list[dict]:
    """Development tracks other coding sessions keep on the same repo, read with the toolbox's notes tools: a track
    whose notes name one of this PR's changed files is work on the same code. The tool takes the registry's id for a
    repo (`resolve-repository`), not owner/repo, and returns a page at a time; a page can be empty and still carry a
    cursor (records you can't read are skipped), so the cursor is followed to the end."""
    import time
    from .notes import _cmd, _read, repo_ref
    cmd = _cmd({})
    if not cmd:
        return []
    out, cache, end = [], {}, time.monotonic() + TRACKS_BUDGET
    own = {p["key"]: ((p.get("notes") or {}).get("track") or {}).get("id") for p in prs}   # a PR's own track is its plan, not other work
    # a changed path as a whole mention: not inside docs/src/foo.py or foo.py.bak
    mention = lambda path, text: re.search(r"(?<![\w./-])" + re.escape(path) + r"(?![\w/-]|\.\w)", text) is not None
    for repo in sorted({p["repo"] for p in prs}):
        ref, err = repo_ref(cmd, repo, "github.com", cache)
        if not ref:
            if err and "NOT-FOUND" not in err:
                warn.append(f"tracks for {repo}: {err}")
            continue
        after, pages = None, 0
        while True:
            if pages >= TRACKS_PAGES or time.monotonic() > end:   # a bound, said out loud: the rest of the tracks weren't checked
                warn.append(f"tracks for {repo}: stopped after {pages} pages ({'time' if pages < TRACKS_PAGES else 'page'} limit); later tracks were not checked")
                break
            pages += 1
            res, err = _read(cmd, "find-tracks", ["--repo-provider", "github", "--repo-host", "github.com", "--repo-ref", str(ref),
                                                  "--status", "active", "--limit", "100"] + (["--after", after] if after else []))
            if err:
                warn.append(f"tracks for {repo}: {err}")
                break
            for t in res.get("items") or []:
                doc = t.get("document") or {}
                text, tid = doc.get("contentMarkdown") or "", t.get("id")
                if not text:
                    continue
                for pr in [p for p in prs if p["repo"] == repo and own.get(p["key"]) != tid]:
                    ours = _ours(pr, o["max_paths"])
                    for path in [x for x in ours if mention(x, text)]:
                        other = {"repo": repo, "number": None, "key": None, "title": doc.get("title") or "a development track",
                                 "state": "agent session", "agent_source": "tracks", "track_id": tid}
                        out.append(_hit(pr, "agent", other, path, ours[path], [], o["tolerance"]))
            after = res.get("nextCursor")
            if not after:
                break
    return out


AGENT_SOURCES = {"checkpoints": _checkpoints, "tracks": _tracks}


def external(prs: list[dict], cfg: dict, session: str | None = None) -> tuple[list[dict], list[str]]:
    """Every overlap with work outside this review, closest first. Also marks each PR's `overlap_spans`: its
    new-side lines that another piece of work changes too, for the reading plan."""
    o, warn, out = conf(cfg), [], []
    if not o.get("enabled", True) or not prs:
        return [], []
    src = o["sources"]
    for name, fn in (("open_prs", lambda: open_prs(prs, o, warn)), ("merged", lambda: merged(prs, o, warn)),
                     ("sessions", lambda: sessions(prs, o, warn, session))):
        if src.get(name):
            try:
                out += fn()
            except Exception as e:   # one source never breaks the review
                warn.append(f"overlaps: {name} failed ({type(e).__name__}: {str(e)[:100]})")
    if src.get("agent_sessions"):
        for name in o.get("agent_sources") or []:
            fn = AGENT_SOURCES.get(name)
            if fn:
                try:
                    out += fn(prs, o, warn)
                except Exception as e:
                    warn.append(f"overlaps: agent source {name} failed ({type(e).__name__}: {str(e)[:100]})")
    seen, uniq = set(), []   # one entry per other work and file: the closest, from the most live source
    for h in sorted(out, key=lambda h: (RANK[h["closeness"]], SOURCE_RANK.get(h["source"], 9), h["for"], h["path"])):
        k = (h["for"], h.get("key") or h.get("commit") or h.get("track_id") or h.get("at"), h["path"])
        if k not in seen:
            seen.add(k); uniq.append(h)
    for pr in prs:
        pr["overlap_spans"] = [{"path": h["path"], "side": "new" if h.get("ours_new") else "old",
                                "from": (h.get("ours_new") or h["ours"])[0], "to": (h.get("ours_new") or h["ours"])[1], "who": h.get("key") or h.get("title")}
                               for h in uniq if h["for"] == pr["key"] and h["closeness"] in ("lines", "function") and (h.get("ours_new") or h.get("ours"))]
    return uniq, warn

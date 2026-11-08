"""Collect PR data (gh + Qodo adapters + memory) into sessions/<id>/review-data.json."""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import re
import secrets
import sys
from pathlib import Path

from . import threads
from .adapters import annotation_checks, collect_findings, pr_context, scan_summary
from .memory import AMR, OKF
from .semantic import annotate
from .attention import compute as attention
from .overlaps import external as other_work
from .util import ROOT, SESSIONS, gh, gh_json, load_config, mem_path, memory_on, now_iso, write_json

REF = re.compile(r"(?:https?://github\.com/)?(?P<repo>[\w.-]+/[\w.-]+)(?:/pull/|#)(?P<num>\d+)")


def parse_ref(ref: str, default_repo: str | None) -> tuple[str, int]:
    m = REF.search(ref)
    if m:
        return m.group("repo"), int(m.group("num"))
    if ref.isdigit() and default_repo:
        return default_repo, int(ref)
    raise ValueError(f"Can't parse PR reference '{ref}'. Use 1234 with --repo, owner/repo#1234, or a PR URL.")


def parse_diff(diff: str) -> dict[str, list[dict]]:
    """Unified diff -> {path: [hunk]} where hunk = {id, header, lines:[[kind, old, new, text]]}."""
    files: dict[str, list[dict]] = {}
    path = None
    hunk = None
    old = new = 0
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            path, hunk = None, None
            continue
        if line.startswith("+++ ") and hunk is None:   # inside a hunk, "+++ x" is an added "++ x"
            p = line[4:].strip()
            path = p[2:] if p.startswith("b/") else p
            if path == "/dev/null":
                path = None
            files.setdefault(path or "(deleted)", [])
            continue
        if line.startswith("--- ") and hunk is None:
            continue
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$", line)
        if m:
            old, new = int(m.group(1)), int(m.group(2))
            key = path or "(deleted)"
            hunk = {"id": f"h{len(files.get(key, []))}", "header": line, "lines": []}
            files.setdefault(key, []).append(hunk)
            continue
        if hunk is None:
            continue
        if line.startswith("+"):
            hunk["lines"].append(["+", None, new, line[1:]]); new += 1
        elif line.startswith("-"):
            hunk["lines"].append(["-", old, None, line[1:]]); old += 1
        elif line.startswith("\\"):
            continue
        else:
            hunk["lines"].append([" ", old, new, line[1:] if line else ""]); old += 1; new += 1
    return files


def human_reviews(reviews: list[dict], head: str | None = None) -> dict:
    """Each human reviewer's latest decisive review: who approved the current head, and who still requests changes.
    Bots and Qodo don't count; an approval of an earlier commit doesn't vouch for code pushed after it."""
    last: dict[str, dict] = {}
    for r in sorted(reviews, key=lambda r: r.get("submitted_at") or ""):
        u = r.get("user") or {}
        login, state = u.get("login") or "", str(r.get("state") or "").upper()
        if not login or u.get("type") == "Bot" or login.endswith("[bot]") or login.lower().startswith("qodo"):
            continue
        if state in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):   # a comment doesn't change a verdict
            last[login] = {"state": state, "commit": r.get("commit_id")}
    return {"approvals": sorted(k for k, v in last.items() if v["state"] == "APPROVED" and (not head or v["commit"] == head)),
            "changes_requested": sorted(k for k, v in last.items() if v["state"] == "CHANGES_REQUESTED")}


def latest_checks(rollup: list[dict]) -> list[dict]:
    """One entry per check name: the latest attempt, so a failure that was re-run green doesn't count."""
    last: dict[str, tuple] = {}
    for c in rollup:
        name = c.get("name") or c.get("context")
        when = c.get("completedAt") or c.get("startedAt") or ""
        if name not in last or when >= last[name][0]:
            last[name] = (when, {"name": name, "state": c.get("conclusion") or c.get("state") or c.get("status"),
                                 **({"url": u} if (u := c.get("detailsUrl") or c.get("targetUrl")) else {}),
                                 **({"workflow": c["workflowName"]} if c.get("workflowName") else {})})
    return [x for _, x in last.values()]


def fetch_annotations(repo: str, sha: str, globs: list[str]) -> list[dict]:
    """Check-run annotations of the scanners that report per-line issues only there (SonarQube Cloud)."""
    if not (globs and sha):
        return []
    try:
        # every page of runs (a busy commit has more than 100): one array per page, which gh_json joins
        runs = gh_json(["api", f"repos/{repo}/commits/{sha}/check-runs?per_page=100", "--paginate", "--jq", "[.check_runs[]]"]) or []
    except RuntimeError:
        return []
    out = []
    for r in runs:
        app = (r.get("app") or {}).get("slug") or ""
        if not (r.get("output") or {}).get("annotations_count") or not any(
                fnmatch.fnmatchcase(r.get("name") or "", g) or fnmatch.fnmatchcase(app, g) for g in globs):
            continue
        try:
            anns = gh_json(["api", f"repos/{repo}/check-runs/{r['id']}/annotations", "--paginate"]) or []
        except RuntimeError:
            continue
        out += [{"check": r.get("name"), "app": app, "url": r.get("html_url"), "path": a.get("path"),
                 "line": a.get("start_line"), "end_line": a.get("end_line"), "level": a.get("annotation_level"),
                 "title": a.get("title") or "", "message": a.get("message") or ""} for a in anns]
    return out


def _tests_and_coverage(repo: str, sha: str | None, comments: list[dict]) -> dict:
    """The PR's test counts (test-result checks) and coverage (a coverage check or bot comment), when it has them."""
    from .impact import coverage, test_results
    runs = []
    if sha:
        try:
            runs = gh_json(["api", f"repos/{repo}/commits/{sha}/check-runs?per_page=100", "--paginate", "--jq", "[.check_runs[]]"]) or []
        except RuntimeError:
            runs = []
    return {"test_results": test_results(runs), "coverage": coverage(runs, comments)}


def prior_bases(repo: str, number: int) -> list[str]:
    """Base branches the PR had before it was retargeted (oldest first). A stacked PR is usually moved to main
    once its parent merges; this keeps its place in the stack."""
    owner, name = repo.split("/", 1)
    q = ("query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){pullRequest(number:$p){"
         "timelineItems(itemTypes:[BASE_REF_CHANGED_EVENT],first:20){nodes{... on BaseRefChangedEvent{previousRefName}}}}}}")
    try:
        v = gh_json(["api", "graphql", "-f", f"query={q}", "-F", f"o={owner}", "-F", f"n={name}", "-F", f"p={number}"]) or {}
        nodes = (((v.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get("timelineItems", {}).get("nodes", [])
        return [x["previousRefName"] for x in nodes if x.get("previousRefName")]
    except (RuntimeError, AttributeError, ValueError):
        return []


def fetch_pr(repo: str, number: int, annotation_checks: list[str] | None = None) -> dict:
    from .product import enabled
    if enabled():
        from .adapters.managed import Client
        return Client().change(repo, number)
    fields = ("number,title,body,author,url,headRefName,baseRefName,additions,deletions,"
              "changedFiles,files,labels,statusCheckRollup,headRefOid,createdAt")
    v = gh_json(["pr", "view", str(number), "--repo", repo, "--json", fields])
    # every file: `gh pr view --json files` stops at 100, the REST list pages (up to GitHub's 3000)
    try:
        rest_files = gh_json(["api", f"repos/{repo}/pulls/{number}/files?per_page=100", "--paginate"]) or []
    except RuntimeError:
        rest_files = []
    try:
        diff = gh(["pr", "diff", str(number), "--repo", repo])
    except RuntimeError:   # GitHub refuses the whole diff for very large PRs; each file's patch still comes
        diff = ""
    # REST, not `gh pr view --json comments,reviews`: that gives node ids and no review URLs.
    issue = gh_json(["api", f"repos/{repo}/issues/{number}/comments", "--paginate"]) or []
    reviews = gh_json(["api", f"repos/{repo}/pulls/{number}/reviews", "--paginate"]) or []
    inline = gh_json(["api", f"repos/{repo}/pulls/{number}/comments", "--paginate"]) or []
    raw = []
    for c in issue:
        raw.append({"id": c["id"], "author": (c.get("user") or {}).get("login"), "body": c.get("body") or "",
                    "url": c.get("html_url"), "path": None, "line": None, "created": c.get("created_at"),
                    "updated": c.get("updated_at")})
    for r in reviews:
        if r.get("body"):
            raw.append({"id": r["id"], "author": (r.get("user") or {}).get("login"), "body": r["body"],
                        "url": r.get("html_url"), "path": None, "line": None, "created": r.get("submitted_at")})
    for c in inline:
        raw.append({"id": c["id"], "author": (c.get("user") or {}).get("login"), "body": c.get("body", ""),
                    "url": c.get("html_url"), "path": c.get("path"), "line": c.get("line") or c.get("original_line"),
                    "start_line": c.get("start_line"),
                    # GitHub sets line=null once a comment no longer maps to the current diff
                    "outdated": c.get("line") is None and c.get("original_line") is not None,
                    "reply_to": c.get("in_reply_to_id"),
                    "created": c.get("created_at")})
    try:   # which findings can be answered in their own thread (and resolved); without it notes go in the review body
        review_threads = threads.fetch(repo, number)
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"warning: {repo}#{number}: could not read review threads ({str(e).split('failed: ')[-1][:120]}); notes on findings go in the review body",
              file=sys.stderr)
        review_threads = None
    hunks = parse_diff(diff)
    listed = [{"path": f["filename"], "additions": f.get("additions", 0), "deletions": f.get("deletions", 0), "patch": f.get("patch"),
               **({"previous": f["previous_filename"]} if f.get("previous_filename") else {})}   # a rename's old path: protection checks both
              for f in rest_files if f.get("filename")] or [{**f, "patch": f.get("patch")} for f in v.get("files", [])]
    seen = {f["path"] for f in listed}
    for path, hs in hunks.items():   # the whole diff has no file cap: anything the lists missed
        if path not in seen and path != "(deleted)":
            seen.add(path)
            listed.append({"path": path, "additions": sum(1 for h in hs for l in h["lines"] if l[0] == "+"),
                           "deletions": sum(1 for h in hs for l in h["lines"] if l[0] == "-"), "patch": None})
    changed = v.get("changedFiles") or 0
    missing = max(0, changed - len(listed))
    if missing:   # GitHub's lists and diff both gave out (3000-file cap, a failed call): never silently partial
        print(f"warning: {repo}#{number}: collected {len(listed)} of {changed} changed files; {missing} are not in the review", file=sys.stderr)
    files = []
    for f in listed:
        h = hunks.get(f["path"]) or (parse_diff(f"+++ b/{f['path']}\n{f['patch']}").get(f["path"], []) if f["patch"] else [])
        files.append({"path": f["path"], "additions": f.get("additions", 0), "deletions": f.get("deletions", 0), "hunks": h,
                      **({"previous": f["previous"]} if f.get("previous") else {})})
    checks = latest_checks(v.get("statusCheckRollup") or [])
    return {
        "key": f"{repo}#{number}", "repo": repo, "number": number, "title": v["title"], "body": v.get("body") or "",
        "url": v["url"], "author": (v.get("author") or {}).get("login"), "base": v.get("baseRefName"),
        "head": v.get("headRefName"), "prior_bases": prior_bases(repo, number), "head_sha": v.get("headRefOid"), "additions": v.get("additions", 0),
        "deletions": v.get("deletions", 0), "labels": [l["name"] for l in v.get("labels", [])], **human_reviews(reviews, v.get("headRefOid")),
        "files": files, "checks": checks, "created": v.get("createdAt"), "_raw_comments": raw, "_threads": review_threads,
        "unresolved_threads": sum(1 for t in review_threads.values() if not t["resolved"]) if review_threads is not None else None,
        "unresolved_ids": sorted(c for c, t in review_threads.items() if not t["resolved"])[:50] if review_threads is not None else [],   # first comment of each, for links
        "_annotations": fetch_annotations(repo, v.get("headRefOid"), annotation_checks or []),
        **_tests_and_coverage(repo, v.get("headRefOid"), raw),
        "summary": "", "risk": "", "diagrams": [], **({"files_missing": missing} if missing else {}),
    }


def overlaps(prs: list[dict]) -> dict:
    by_file: dict[str, list[str]] = {}
    for pr in prs:
        for f in pr["files"]:
            by_file.setdefault(f["path"], []).append(pr["key"])
    by_concept: dict[str, dict] = {}
    for pr in prs:
        for c in pr.get("concepts", []):
            by_concept.setdefault(c, {"path": c, "prs": []})["prs"].append(pr["key"])
    return {"files": [{"path": p, "prs": k} for p, k in sorted(by_file.items()) if len(k) > 1],
            "concepts": [v for v in by_concept.values() if len(v["prs"]) > 1]}


LINK = re.compile(r"https?://[^\s)\]>\"'`]+")
MENTION = re.compile(r"(?:(?P<hint>(?:[\w.-]+\s){0,3}))#(?P<num>\d{2,6})\b")
TICKET = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d{1,6})\b")
GH_PR_URL = re.compile(r"https?://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)", re.I)
OWNER_REF = re.compile(r"(?<![\w./-])([\w.-]+/[\w.-]+)#(\d+)\b")
LINK_KINDS = [("linear.app", "ticket"), ("atlassian.net", "ticket"), ("/issues/", "issue"), ("/pull/", "pr"),
              ("notion.so", "doc"), ("notion.com", "doc"), ("docs.google.com", "doc"), ("figma.com", "design"),
              ("confluence", "doc"), ("loom.com", "video")]
NOT_TICKETS = ("HTTP-", "UTF-", "SHA-", "ISO-", "RFC-", "CVE-", "FEAT-", "FIX-", "V-", "PR-")
SKIP_LINKS = ("claude.com/claude-code", "claude.ai/code", "img.shields.io", "qodo.ai/wp-content", "/commit/", "githubusercontent.com", "/files#diff")


def stacks(prs: list[dict]) -> list[list[str]]:
    """Merge paths through session PRs where one PR's base branch is another's head, root first.
    A stack can branch (two PRs on the same base); each root-to-leaf path is one list."""
    by_head = {(p["repo"], p.get("head")): p for p in prs}
    children: dict[str, list[str]] = {}
    has_parent = set()
    for p in prs:
        # its base, else the base it had before a retarget (a stacked PR moved to main once its parent merged)
        parent = next((by_head[(p["repo"], b)] for b in [p.get("base")] + (p.get("prior_bases") or [])[::-1]
                       if (p["repo"], b) in by_head and by_head[(p["repo"], b)]["key"] != p["key"]), None)
        if parent and parent["key"] != p["key"]:
            children.setdefault(parent["key"], []).append(p["key"])
            has_parent.add(p["key"])
    order = {p["key"]: i for i, p in enumerate(prs)}
    out: list[list[str]] = []

    def walk(key: str, path: list[str]):
        if key in path:   # defensive: a branch cycle
            return
        kids = sorted(children.get(key, []), key=order.get)
        if not kids:
            out.append(path + [key])
        for k in kids:
            walk(k, path + [key])

    for p in prs:
        if p["key"] in children and p["key"] not in has_parent:
            walk(p["key"], [])
    return out


def context(prs: list[dict], open_prs: dict[str, list[dict]] | None = None) -> dict:
    """What the skill should read before writing the session story: linked tickets/specs/docs,
    stack order, and related PRs (same branch lineage) that are not in this session."""
    sources: dict[str, dict] = {}
    for p in prs:
        for url in LINK.findall(p.get("body") or ""):
            url = url.rstrip(".,;")
            if any(s in url for s in SKIP_LINKS) or url.rstrip("/") == p["url"]:
                continue
            if len([x for x in url.split("/")[3:] if x]) == 0:   # a bare domain says nothing
                continue
            kind = next((k for frag, k in LINK_KINDS if frag in url), "link")
            sources.setdefault(url, {"url": url, "kind": kind, "prs": []})["prs"].append(p["key"])
    tickets: dict[str, list[str]] = {}
    strong: set[str] = set()
    for p in prs:
        # Keys in the title/body as written; in the branch name lower-case is the norm (plt-123-foo).
        keep = lambda m: m.group(0) if any(f in m.group(0) for f in ("linear.app", "atlassian.net")) else " "
        text = LINK.sub(keep, " ".join([p.get("title") or "", p.get("body") or ""]))
        branch = (p.get("head") or "").split("/")[-1]
        found = set(TICKET.findall(text)) | set(TICKET.findall(branch.upper()[:12]))
        linked = " ".join(m.group(0) for m in LINK.finditer(" ".join([p.get("title") or "", p.get("body") or ""])) if any(f in m.group(0) for f in ("linear.app", "atlassian.net")))
        for t in found:
            if not t.startswith(NOT_TICKETS):
                tickets.setdefault(t, []).append(p["key"])
                if t in branch.upper() or t in (p.get("title") or "").upper() or t in linked.upper():   # named on purpose, not "AES-256" in prose
                    strong.add(t)
    keys = {p["key"] for p in prs}
    # "gateway #813", "analytics SDK contract #18": references the skill has to resolve (maybe other repos)
    mentions: dict[str, dict] = {}
    related: dict[str, dict] = {}   # PRs in other repos (or this one) the descriptions name by owner/repo#N or link
    for p in prs:
        raw = p.get("body") or ""
        named = [m.groups() for u in LINK.findall(raw) for m in [GH_PR_URL.match(u)] if m]   # github.com/o/r/pull/N links
        named += [m.groups() for m in OWNER_REF.finditer(LINK.sub(" ", raw))]   # plain o/r#N, never a path inside some other URL
        for repo, num in named:
            k = f"{repo}#{num}"
            if k.lower() not in {x.lower() for x in keys}:   # GitHub names are case-insensitive
                e = related.setdefault(k.lower(), {"key": k, "why": "mentioned in the description", "prs": []})   # one entry however it's spelled
                if p["key"] not in e["prs"]:
                    e["prs"].append(p["key"])
        body = OWNER_REF.sub(" ", LINK.sub(" ", raw))   # a bare "#N" left over is this repo's, or a hint the skill resolves
        for m in MENTION.finditer(body):
            ref = f"{p['repo']}#{m.group('num')}"
            if ref in keys:
                continue
            hint = " ".join(m.group("hint").split()[-3:])
            e = mentions.setdefault(ref, {"ref": "#" + m.group("num"), "hints": [],   # same number, other repo: separate
                                          "same_repo_guess": ref, "prs": []})
            if hint and hint not in e["hints"]:
                e["hints"].append(hint)
            if p["key"] not in e["prs"]:
                e["prs"].append(p["key"])
    missing = []
    for repo, rows in (open_prs or {}).items():
        heads = {p.get("head") for p in prs if p["repo"] == repo}
        bases = {p.get("base") for p in prs if p["repo"] == repo}
        for r in rows:
            k = f"{repo}#{r['number']}"
            if k in keys:
                continue
            if r.get("baseRefName") in heads:
                missing.append({"key": k, "url": r.get("url"), "title": r.get("title"), "why": "stacked on a PR in this session"})
            elif r.get("headRefName") in bases:
                missing.append({"key": k, "url": r.get("url"), "title": r.get("title"), "why": "a PR in this session is stacked on it"})
    return {"sources": list(sources.values()), "mentions": list(mentions.values()), "tickets": [{"key": t, "prs": v, **({"strong": True} if t in strong else {})} for t, v in sorted(tickets.items())],
            "stacks": stacks(prs), "missing_stack": missing, "related": list(related.values())}


RELATED_MAX, RELATED_SECONDS, RELATED_BUDGET = 50, 20, 45   # results per search, seconds per lookup, seconds for all of them


def related_elsewhere(prs: list[dict], ctx: dict) -> list[dict]:
    """Open PRs that belong with these but aren't in the session: the ones the descriptions name (with their title and
    state), and every open PR, in any repo gh can see, that names one of the same tickets. Read-only; a failed lookup
    is skipped, never fatal."""
    from .product import enabled
    if enabled() or any(p.get('product') for p in prs):
        from .managed_work import related
        return related(prs, ctx)
    import subprocess
    import time
    deadline = time.monotonic() + RELATED_BUDGET   # many tickets or owners never hold up a collect or refresh for long
    keys = {p["key"].lower() for p in prs}
    out = {r["key"].lower(): dict(r) for r in ctx.get("related") or []}   # keyed lowercase: one entry per PR however it's spelled
    missed = [0]
    def gh_q(args):
        left = deadline - time.monotonic()
        if left <= 1:   # out of time: skip the rest; the PRs a description names are listed anyway
            missed[0] += 1
            return None
        try:
            r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=min(RELATED_SECONDS, left))
            if r.returncode != 0 and "Could not resolve to a PullRequest" in (r.stderr or ""):
                return False   # GitHub answered: it's an issue (or nothing), not a PR
            if r.returncode != 0:
                missed[0] += 1
            return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
        except (OSError, subprocess.TimeoutExpired, ValueError):
            missed[0] += 1
            return None
    gone: set[str] = set()
    for k, e in out.items():   # first, so the budget always covers them: the PRs a description names
        if not e.get("title"):
            repo, num = e["key"].rsplit("#", 1)
            v = gh_q(["pr", "view", num, "--repo", repo, "--json", "title,url,state,isDraft"])
            if v is False:
                gone.add(k); continue
            if v:
                e.update({"title": v.get("title"), "url": v.get("url"), "state": str(v.get("state") or "").lower(), "draft": bool(v.get("isDraft"))})
    # only where this work lives: the session's owners and the ones its descriptions name (a ticket key like WF-1182 is
    # also a number in thousands of unrelated public PRs), and only PRs whose title or body has the exact key
    owners = sorted({p["repo"].split("/")[0] for p in prs} | {e["key"].split("/")[0] for e in out.values()})
    for k in gone:
        out.pop(k, None)
    for t in ctx.get("tickets") or []:
        if not t.get("strong"):   # only keys named on purpose (branch, title, a Linear or Jira link) search other repos
            continue
        exact = re.compile(rf"(?<![A-Za-z0-9]){re.escape(t['key'])}(?![A-Za-z0-9])", re.I)   # any case, as the search; WF-1182-fix counts, WF-11820 and WF-1182abc don't
        hits = [r for o in owners for r in gh_q(["search", "prs", t["key"], "--state", "open", "--limit", str(RELATED_MAX), "--owner", o,
                                                  "--json", "repository,number,title,url,isDraft,body"]) or []]   # one owner per call: older gh takes one
        for r in hits:
            k = f"{(r.get('repository') or {}).get('nameWithOwner')}#{r.get('number')}"
            if k.lower() in keys or "None#" in k or not exact.search(f"{r.get('title') or ''} {r.get('body') or ''}"):
                continue
            e = out.setdefault(k.lower(), {"key": k, "why": "", "prs": []})
            e.update({"title": r.get("title"), "url": r.get("url"), "draft": bool(r.get("isDraft")), "state": "open"})
            if f"names {t['key']}" not in e["why"]:   # the same PR can come back from more than one search
                e["why"] = ", ".join(x for x in (e["why"], f"names {t['key']}") if x)
            e["prs"] = sorted(set(e["prs"]) | set(t.get("prs") or []))
    ctx["related_missed"] = missed[0]   # lookups that didn't answer: the list may be incomplete, and the page says so
    if missed[0]:
        import sys
        print(f"related work: {missed[0]} lookup(s) didn't answer (out of time or failed); the list may be incomplete", file=sys.stderr)
    return sorted(out.values(), key=lambda e: (e.get("state") != "open", e["key"]))   # all of them: each search is already bounded


def import_own_comments(pr: dict, reviewer_login: str | None, session: str) -> list[dict]:
    """Comments the reviewer already left on GitHub become events, so they feed memory too."""
    if not reviewer_login:
        return []
    out = []
    for c in pr["_raw_comments"]:
        if (c.get("author") or "").lower() != reviewer_login.lower():
            continue
        target = {"kind": "line", "id": f"{c['path']}:{c['line']}"} if c.get("path") else {"kind": "pr", "id": pr["key"]}
        out.append({"ts": c.get("created") or now_iso(), "session": session, "pr": pr["key"], "source": "github",
                    "type": "note", "target": target, "text": c.get("body", ""), "posted": True,
                    "github_id": c.get("id"), "path": c.get("path"), "line": c.get("line")})
    return out


def build(prs: list[dict], cfg: dict, *, demo: bool = False, session: str | None = None,
          reviewer_login: str | None = None, open_prs: dict | None = None,
          skip_github_ids: set | None = None, dest: Path | None = None,
          collection_meta: dict | None = None, require_complete_budget: bool = False) -> tuple[str, Path]:
    """`dest` pins the session folder (a refresh), so a work package folder change mid-run can't redirect the writes."""
    session = session or _dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
    sdir = dest or SESSIONS / session
    sdir.mkdir(parents=True, exist_ok=True)
    amr, okf = AMR(mem_path(cfg, "amr")), OKF(mem_path(cfg, "okf"))
    reviewer = cfg.get("reviewer") or reviewer_login or "reviewer"   # unset (e.g. a plugin install): your gh login
    if memory_on(cfg):
        amr.ensure(reviewer); okf.ensure()

    events = []
    for pr in prs:
        if not pr.get("findings"):
            pr["findings"] = collect_findings(pr, cfg)
        if pr.get("_threads") is not None:
            threads.attach(pr["findings"], pr["_threads"])
        pr["scans"] = scan_summary(pr, cfg, pr["findings"])
        ctx = pr_context(pr, cfg)
        if ctx:
            pr["qodo"] = {**pr.get("qodo", {}), **ctx}
            d = ctx.get("diagram")
            if d and not any(x.get("id") == d["id"] for x in pr.get("diagrams", [])):
                pr.setdefault("diagrams", []).append(d)
        pr["semantic"] = annotate(pr["files"])   # moves, whitespace-only and token-level edits
        pr["concepts"] = [c.path for c in okf.match([f["path"] for f in pr["files"]])]
        events += [e for e in import_own_comments(pr, reviewer_login, session)
                   if e.get("github_id") not in (skip_github_ids or set())]
        pr["collected_at"] = now_iso()
        pr.pop("_raw_comments", None); pr.pop("_annotations", None); pr.pop("_threads", None)

    if not demo:   # the plan the coding agent left: before other work, which leaves out each PR's own track
        from .notes import collect as collect_notes
        collect_notes(prs, cfg)
    from .product import enabled
    product = enabled() or any(p.get('product') for p in prs)
    if product and not demo:
        from .managed_work import overlaps as managed_overlaps
        external, overlap_warnings = managed_overlaps(prs, cfg, session)
    else:
        external, overlap_warnings = ([], []) if demo else other_work(prs, cfg, session)   # marks pr["overlap_spans"]
    for w in overlap_warnings:
        print(f"warning: {w}", file=sys.stderr)
    concept_dicts = [c.as_dict() for c in okf.concepts()]
    rules = amr.active_rules(cfg["distill"]["dismiss_threshold"])
    for pr in prs:   # what a human must read, can skim, can skip (refined later by enrich)
        pr["attention"], _ = attention(pr, concepts=concept_dicts, rules=rules,
                                       additive_tests=(cfg.get("attention") or {}).get("additive_tests", "skip"))
    data = {
        "session": session, "created": now_iso(), "demo": demo,
        **({'product': True, 'provider_writes': False} if product else {}),
        "reviewer": reviewer, "reviewer_login": reviewer_login,
        "memory": {k: str(v) for k, v in cfg["memory"].items()},
        "emoji": cfg["emoji"], "threshold": cfg["distill"]["dismiss_threshold"],
        "prefs": {"rules": amr.active_rules(cfg["distill"]["dismiss_threshold"]),
                  "bullets": [{"text": b.text, "file": b.file, **b.meta} for b in amr.bullets()]},
        "okf": {"concepts": [c.as_dict() for c in okf.concepts()], "candidates": []},
        "prs": prs, "overlaps": {**overlaps(prs), "external": external}, "context": context(prs, open_prs),
    }
    if not demo:   # sister PRs elsewhere: by ticket, and by the descriptions' owner/repo#N mentions
        data["context"]["related"] = related_elsewhere(prs, data["context"])
    if product:
        from .adapters.managed import current_budget, BudgetExceeded
        budget = current_budget()
        if budget:
            data['managed_read_budget'] = budget.summary()
            if require_complete_budget and data['managed_read_budget']['exhausted']:
                raise BudgetExceeded('Refresh read budget exhausted; the previous saved session is unchanged')
        if collection_meta is not None:
            meta = dict(collection_meta)
            if (data.get('managed_read_budget') or {}).get('exhausted'):
                meta.update(complete=False, reason='budget_exhausted')
            data['collection'] = meta
            if not meta['complete']:
                print(f"Collection incomplete: {len(prs)} of {len(meta['requested_refs'])} requested changes retained; missing evidence remains unknown", file=sys.stderr)
    write_json(sdir / "review-data.json", data)
    ev_path = sdir / "events.jsonl"
    with ev_path.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    (sdir.parent / "latest").write_text(session)
    return session, sdir


def live_state(prs: list[dict], since_default: str = "") -> dict:
    """What changed on GitHub since this snapshot: new commits, new comments, merge blockers."""
    from .product import enabled
    if enabled() or any(p.get('product') for p in prs):
        from .managed_work import live_state as managed_live
        return managed_live(prs, since_default)
    out = {}
    for pr in prs:
        key, repo, num = pr["key"], pr["repo"], pr["number"]
        try:
            v = gh_json(["pr", "view", str(num), "--repo", repo, "--json",
                         "headRefOid,state,mergeStateStatus,reviewDecision,isDraft,comments,reviews"]) or {}
        except RuntimeError as e:
            out[key] = {"error": str(e)[:200]}
            continue
        head, old = v.get("headRefOid"), pr.get("head_sha")
        ahead = 0
        if head and old and head != old:
            try:
                ahead = int(gh(["api", f"repos/{repo}/compare/{old}...{head}", "--jq", ".ahead_by"]).strip() or 0)
            except (RuntimeError, ValueError):
                ahead = -1   # unknown (force-push or rebase)
        since = pr.get("collected_at") or since_default   # older sessions: the session's creation time
        new_reviews = [r for r in (v.get("reviews") or []) if (r.get("submittedAt") or "") > since]
        approvers = sorted({(r.get("author") or {}).get("login") or "someone" for r in new_reviews if r.get("state") == "APPROVED"})
        # an approval is news of its own, not "a comment"; the other reviews are comments to read
        new_comments = sum(1 for c in (v.get("comments") or []) if (c.get("createdAt") or "") > since) + \
            sum(1 for r in new_reviews if r.get("state") != "APPROVED")
        try:   # review conversations still open, for the verdict: how many, and the first comment of each for its link
            open_ids = sorted(c for c, t in threads.fetch(repo, num).items() if not t["resolved"])
            unresolved = len(open_ids)
        except (RuntimeError, ValueError, KeyError):
            open_ids, unresolved = [], None
        out[key] = {"head": head, "snapshot_head": old, "moved": bool(head and old and head != old), "new_commits": ahead, "unresolved": unresolved, "unresolved_ids": open_ids[:50],
                    "state": v.get("state"), "merge_state": v.get("mergeStateStatus"), "review_decision": v.get("reviewDecision"),
                    "draft": v.get("isDraft"), "new_comments": new_comments, "approved_by": approvers}
    return out


def refresh(sdir: Path, cfg: dict | None = None) -> dict:
    """Re-collect the session's PRs into the same session: notes, marks and verdicts stay, the
    enrichment (sessions/<id>/enrich.json) is re-applied so its warnings show what drifted."""
    old = json.loads((sdir / "review-data.json").read_text())
    from .product import enabled
    if enabled(old):
        from .managed_work import refresh as managed_refresh
        from .util import session_config
        return managed_refresh(sdir, old, cfg or session_config(sdir))
    cfg = cfg or load_config()
    try:
        login = gh(["api", "user", "--jq", ".login"]).strip()
    except RuntimeError:
        login = None
    prs = [fetch_pr(p["repo"], p["number"], annotation_checks(cfg)) for p in old["prs"]]
    evs = _events(sdir)
    known = {e.get("github_id") for e in evs if e.get("github_id")}
    known |= {g for e in evs if e.get("type") == "published" for g in e.get("github_ids") or []}   # posted from here
    build(prs, cfg, session=sdir.name, reviewer_login=login, skip_github_ids=known, dest=sdir)
    if old.get("reviewers"):   # kept, but marked stale when the changed paths or the reviewer moved since they were found
        from .reviewers import basis
        new = json.loads((sdir / "review-data.json").read_text())
        new["reviewers"] = {**old["reviewers"], "stale": old["reviewers"].get("basis") != basis(new)}
        write_json(sdir / "review-data.json", new)
    result = {"session": sdir.name, "warnings": []}
    enr = sdir / "enrich.json"
    if enr.exists():
        from .enrich import enrich
        result["warnings"] = enrich(sdir, json.loads(enr.read_text()))["warnings"]
    return result


def _events(sdir: Path) -> list[dict]:
    p = sdir / "events.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def collect(refs: list[str], default_repo: str | None = None) -> tuple[str, Path]:
    cfg = load_config()
    from .product import enabled
    if enabled():
        from .managed_work import collect as managed_collect
        return managed_collect(refs, default_repo, cfg)
    try:
        login = gh(["api", "user", "--jq", ".login"]).strip()
    except RuntimeError:
        login = None
    prs = [fetch_pr(*parse_ref(r, default_repo), annotation_checks(cfg)) for r in refs]
    open_prs = {}
    for repo in sorted({p["repo"] for p in prs}):   # to spot stack members that weren't passed in
        try:
            open_prs[repo] = gh_json(["pr", "list", "--repo", repo, "--state", "open", "--limit", "300",
                                      "--json", "number,title,url,headRefName,baseRefName"]) or []
        except RuntimeError:
            pass
    return build(prs, cfg, reviewer_login=login, open_prs=open_prs)


def collect_demo() -> tuple[str, Path]:
    """Demo uses a throwaway copy of fixtures/demo-memory so your real memory is untouched."""
    import shutil
    cfg = load_config()
    fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
    session = "demo-" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    mem, on = SESSIONS / session / "memory", memory_on(cfg)
    if on:   # with memory off the demo has none either
        shutil.copytree(ROOT / "fixtures" / "demo-memory", mem)
    cfg["memory"] = {"enabled": on, "amr": str(mem / "amr"), "okf": str(mem / "okf"), "auto_commit": False}
    sid, sdir = build(fx["prs"], cfg, demo=True, session=session, reviewer_login=fx.get("reviewer_login"))
    from .enrich import enrich   # the demo story, written the way the skill would write it
    res = enrich(sdir, json.loads((ROOT / "fixtures" / "demo-enrich.json").read_text()))
    for w in res["warnings"]:
        print("demo story warning:", w)
    return sid, sdir

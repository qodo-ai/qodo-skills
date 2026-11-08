"""Who should review: people who know the changed code, from read-only GitHub signals (and Qodo's, when it's
there), strongest first. Never a bot, a PR's author or the person reviewing. Each suggestion carries its evidence,
and one with thin evidence says so."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from urllib.parse import quote

from .util import gh_json

MAX_CALLS, DIRS, COMMITS, PRS_PER_DIR, TOP, CALL_SECONDS, REVIEWS = 60, 3, 15, 8, 3, 20, 100
BOTS = re.compile(r"(\[bot\]|-bot|^bot-|^dependabot|^renovate|^github-actions|^copilot|^qodo|^claudette|^chatgpt|^codex|^upwind|^snyk|^sonar)", re.I)
WEIGHT = {"approved": 3, "reviewed": 2, "owner": 4, "requested": 2, "commits": 1, "similar": 1, "prior": 1}


class Budget:
    def __init__(self, n: int):
        self.left, self.failed = n, 0

    def api(self, path: str):
        if self.left <= 0:
            return None
        self.left -= 1
        try:   # a stalled call is an absent signal, never a hang
            r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=CALL_SECONDS)
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
            if "404" not in (r.stderr or ""):   # a missing CODEOWNERS is an answer; an error or timeout is a gap
                self.failed += 1
            return None
        except (OSError, subprocess.TimeoutExpired, ValueError):
            self.failed += 1
            return None


def _dirs(files: list[dict], n: int = DIRS) -> list[str]:
    """The directories with the most changed lines (two levels deep, so one big module isn't the whole repo)."""
    c = Counter()
    for f in files:
        parts = (f.get("path") or "").split("/")
        c["/".join(parts[:min(len(parts) - 1, 3)]) or parts[0]] += (f.get("additions") or 0) + (f.get("deletions") or 0) or 1
    return [d for d, _ in c.most_common(n) if d]


def _owners(repo: str, base: str, files: list[dict], b: Budget, rules_out: dict | None = None) -> dict[str, list[str]]:
    """Who owns each changed file; `rules_out` also gets path -> the rule that owns it (for the criticality map)."""
    for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        doc = b.api(f"repos/{repo}/contents/{path}?ref={quote(base, safe='')}")
        if isinstance(doc, dict) and "content" in doc:   # an empty CODEOWNERS still wins: GitHub uses the first one it finds
            import base64
            text = base64.b64decode(doc["content"]).decode(errors="replace")
            break
    else:
        return {}
    rules = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if line:   # a path with no owners is a rule too: as the last match, it leaves those files unowned
            pat, *who = line.split()
            rules.append((pat, [w.lstrip("@") for w in who if "/" not in w], bool(who)))   # team handles can't be people, but they still own
    out = defaultdict(list)
    for f in files:
        p = f.get("path") or ""
        for pat, who, owned in reversed(rules):   # the last matching rule wins, as on GitHub
            if _owns(pat, p):
                for w in who:
                    out[w].append(p)
                if rules_out is not None and owned:   # a team-only rule protects the file too
                    rules_out.setdefault(p, []).append(pat)
                break
    return out


def _owns(pat: str, path: str) -> bool:
    """GitHub's CODEOWNERS matching: a pattern with a slash (other than a trailing one) is anchored at the root, else it
    matches at any depth; `*` stays inside one directory and `**` crosses them; `dir/*` owns only dir's own files,
    while `dir/` and a bare `dir` own everything below it."""
    anchored = pat.startswith("/") or "/" in pat.rstrip("/")
    body = pat.strip("/")
    rx = re.sub(r"\\\*\\\*/?|\\\*|\\\?", lambda m: {"\\*": "[^/]*", "\\?": "[^/]"}.get(m.group(0), "(?:.*/)?" if m.group(0).endswith("/") else ".*"), re.escape(body))
    tail = "$" if body.endswith("/*") else "/.*$" if pat.endswith("/") else "(?:/.*)?$"
    return re.match(("^" if anchored else "^(?:.*/)?") + rx + tail, path) is not None


def qodo_cmd(cfg: dict | None) -> str | None:
    """Qodo's CLI as configured (qodo_findings.command, the findings adapter's setting), else `qodo` on PATH."""
    cmd = str(((cfg or {}).get("qodo_findings") or {}).get("command") or "qodo")
    from pathlib import Path
    return shutil.which(cmd) or (cmd if Path(cmd).is_file() else None)


def _similar(repo: str, title: str, b: "Budget", why: dict, qodo: str | None = None) -> list[int]:
    """PR numbers Qodo finds similar, when the CLI is there and logged in; charged to the budget; never a blocker.
    When it can't answer, `why[repo]` says so, so an absent signal isn't mistaken for "no similar PRs"."""
    if not qodo or b.left <= 0:
        why[repo] = "no Qodo CLI" if not qodo else "out of calls"
        return []
    b.left -= 1
    try:   # the CLI's own flags for this tool (qodo read pull-request similar --help)
        r = subprocess.run([qodo, "read", "pull-request", "similar", "--repo", repo, "--query", title[:200], "--similarity-top-k", "6", "--json"],
                           capture_output=True, text=True, timeout=CALL_SECONDS)
        doc, _ = json.JSONDecoder().raw_decode(r.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        why[repo] = f"Qodo didn't answer ({type(e).__name__})"
        return []
    if isinstance(doc, dict) and isinstance(doc.get("error"), dict):   # e.g. MT-REPO-NOT-IN-SCOPE: the repo isn't in Qodo's workspace
        why[repo] = str(doc["error"].get("code") or "error")[:60]
        return []
    items = doc if isinstance(doc, list) else (doc.get("results") or doc.get("pull_requests") or doc.get("items") or []) if isinstance(doc, dict) else []
    if not isinstance(items, list):   # an unexpected shape is a missing signal, never a crash
        why[repo] = "Qodo's answer wasn't a list"
        return []
    nums = []
    for it in items:
        n = it.get("number") or it.get("pr_number") if isinstance(it, dict) else None
        if isinstance(n, int):
            nums.append(n)
    return nums[:6]


def basis(data: dict) -> str:
    """What a suggestion was computed from (the changed paths and the reviewer), so a refresh can tell it's out of date."""
    import hashlib
    key = sorted(f"{p.get('repo')}:{f.get('path')}" for p in data.get("prs", []) for f in p.get("files") or [])
    return hashlib.sha1(json.dumps([key, data.get("reviewer_login") or data.get("reviewer")]).encode()).hexdigest()[:16]


def _reviews(repo: str, n: int, b: Budget, author: str | None = None) -> dict[str, str]:
    """Who reviewed PR n and how, once per person: "approved" beats "reviewed" (a review with a real body, or inline
    comments). Reads the first REVIEWS reviews; inline comments cost one more call, only when a short review needs them."""
    best, short = {}, set()
    for r in b.api(f"repos/{repo}/pulls/{n}/reviews?per_page={REVIEWS}") or []:
        u, st = (r.get("user") or {}).get("login"), r.get("state")
        if not u or (author and u.lower() == author.lower()):   # an author's replies in their own threads are reviews too, on GitHub
            continue
        if st == "APPROVED":   # reviews come oldest first: a person's latest verdict is the one that counts
            best[u] = "approved"
        elif st == "CHANGES_REQUESTED":   # a later request for changes replaces an earlier approval
            if len(r.get("body") or "") > 40 or best.get(u) == "approved":
                best[u] = "reviewed"
            else:
                short.add(u)
        elif st == "COMMENTED":   # a comment isn't a verdict: it never replaces one
            if len(r.get("body") or "") > 40:
                best.setdefault(u, "reviewed")
            else:
                short.add(u)
    if short - set(best):   # the review may be all inline comments, with no summary
        inline = {(c.get("user") or {}).get("login") for c in b.api(f"repos/{repo}/pulls/{n}/comments?per_page={REVIEWS}") or []}
        for u in (short - set(best)) & inline:
            best[u] = "reviewed"
    return best


def suggest(data: dict, cfg: dict | None = None, max_calls: int = MAX_CALLS) -> dict:
    """The work package's suggested reviewers: [{login, score, weak, evidence: [str], prs: [keys]}], best first."""
    cfg = cfg or {}
    from .product import enabled
    if enabled(data):
        from .managed_work import reviewers
        return reviewers(data, cfg, max_calls)
    mine = {(data.get(k) or "").lower() for k in ("reviewer_login", "reviewer")} - {""}   # the GitHub login, and the display name
    authors = {(p.get("author") or "").lower() for p in data.get("prs", [])}
    logins = lambda v: [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)] if isinstance(v, list) else []   # one login, or a list
    service = {x.lower() for x in logins(cfg.get("qodo_bot_logins")) + logins((cfg.get("reviewers") or {}).get("exclude"))}
    service |= {x.lower() for s in (cfg.get("scanners") or {}).values() if isinstance(s, dict) for x in logins(s.get("logins"))}   # review bots under any name
    skip = lambda u: not u or BOTS.search(u) or u.lower() in authors or u.lower() in mine or u.lower() in service
    score, ev, where = Counter(), defaultdict(Counter), defaultdict(set)
    shown = {}   # logins are case-insensitive on GitHub: one person, one entry, spelled as first seen
    def credit(u, kind, keys, n=1):
        if not skip(u):
            k = shown.setdefault(u.lower(), u)
            score[k] += WEIGHT[kind] * n; ev[k][kind] += n; where[k].update([keys] if isinstance(keys, str) else keys)
    by_repo = defaultdict(list)
    for p in data.get("prs", []):
        by_repo[p["repo"]].append(p)
    left, missed, failed, owned = max(0, max_calls), {}, 0, {}
    for i, (repo, prs) in enumerate(by_repo.items()):   # each repo gets an equal share of what's left, so a big one can't crowd out the rest
        share = left // (len(by_repo) - i)   # zero when there are more repos than calls: the total never goes over
        b = Budget(share)
        files = [f for p in prs for f in p.get("files") or []]
        own = set(p["number"] for p in prs)
        for p in prs:   # who's already asked comes first, before the budget goes to history
            for u in ((b.api(f"repos/{repo}/pulls/{p['number']}") or {}).get("requested_reviewers") or []):
                credit(u.get("login"), "requested", p["key"])
        under = lambda pred: [p["key"] for p in prs if any(pred(f.get("path") or "") for f in p.get("files") or [])] or [p["key"] for p in prs]
        bases = defaultdict(list)
        for p in prs:
            bases[p.get("base") or "main"].append(p)
        for base, ps in bases.items():   # CODEOWNERS as it is on each PR's own base branch
            for u, paths in _owners(repo, base, [f for p in ps for f in p.get("files") or []], b, owned.setdefault(repo, {})).items():
                credit(u, "owner", [p["key"] for p in ps if any((f.get("path") or "") in paths for f in p.get("files") or [])])
        seen_prs, qodo = set(), qodo_cmd(cfg)
        held = 1 if qodo and b.left > 0 else 0   # one call kept back for Qodo's similar PRs, so history can't use it up
        b.left -= held
        dirs = _dirs(files)
        for i, d in enumerate(dirs):   # each directory gets an equal share of what's left, so the first can't take it all
            share_d = b.left // (len(dirs) - i)
            sub = Budget(share_d)
            here = under(lambda x: x == d or x.startswith(d + "/"))   # the PRs that changed this directory
            commits = sub.api(f"repos/{repo}/commits?path={quote(d, safe='/')}&per_page={COMMITS}") or []   # a path with & or # stays one value
            for c in commits:
                credit((c.get("author") or {}).get("login"), "commits", here)
            for c in commits[:PRS_PER_DIR]:
                for pr in sub.api(f"repos/{repo}/commits/{c['sha']}/pulls") or []:
                    if pr.get("number") in own or pr.get("number") in seen_prs:
                        continue
                    seen_prs.add(pr["number"])
                    for u, how in _reviews(repo, pr["number"], sub, (pr.get("user") or {}).get("login")).items():   # one credit per person per PR
                        credit(u, how, here)
            b.left -= share_d - sub.left; b.failed += sub.failed   # unused calls go back for the next directory
        b.left += held
        for n in _similar(repo, " ".join(p.get("title") or "" for p in prs)[:200], b, missed, qodo):   # once per repo, from all its PRs' titles
            if n in own or n in seen_prs:
                continue
            seen_prs.add(n)
            for u, how in _reviews(repo, n, b).items():
                if how == "approved":   # only approvals, which GitHub never lets an author give their own PR
                    credit(u, "similar", [p["key"] for p in prs])   # from all the repo's titles: every PR there
        seeds = ((cfg.get("reviewers") or {}).get("priors") or {}).get(repo) or []
        seeds = [seeds] if isinstance(seeds, str) else seeds if isinstance(seeds, list) else []   # one login, or a list of them
        for u in (x for x in seeds if isinstance(x, str)):   # the team's own seed list, ties only
            credit(u, "prior", [p["key"] for p in prs])
        left -= share - b.left; failed += b.failed
    words = {"approved": "approved {n} recent PR{s} on these paths", "reviewed": "reviewed {n} recent PR{s} here in depth",
             "owner": "a code owner of the changed files", "requested": "already requested on this PR",
             "commits": "wrote {n} of the latest commits here", "similar": "approved {n} similar PR{s} (Qodo)", "prior": "on the team's list for this area"}
    strong = lambda u: ev[u]["approved"] + ev[u]["reviewed"] + ev[u]["owner"] > 0
    out = []
    for u in sorted(score, key=lambda u: (not strong(u), -score[u], u.lower()))[:TOP]:   # approvals, reviews or ownership first: many commits alone never outrank them
        e = ev[u]
        evidence = [words[k].format(n=e[k], s="" if e[k] == 1 else "s") for k in ("owner", "approved", "reviewed", "requested", "commits", "similar", "prior") if e[k]]
        out.append({"login": u, "score": score[u], "weak": not strong(u), "evidence": evidence, "prs": sorted(where[u])})
    return {"suggested": out, "owned": owned, "basis": basis(data), "similar_unavailable": missed, "failed_calls": failed, "calls": max(0, max_calls) - left, "excluded": sorted(x for x in authors | mine if x)}

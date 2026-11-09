"""Findings from the security scanners and AI reviewers that comment on PRs: Snyk, Upwind, GitHub code scanning,
SonarQube, GitGuardian, Socket, Copilot, Codex, and any tool's check-run annotations.

Which bots count, and how each is read, is the config's `scanners` map: {parser: {name, logins, statuses}}.
Each parser turns that bot's comments into the same findings the Qodo adapter returns, with
`source` set to the parser and `scanner` = {name, kind: sast|sca|iac|secret|license|gate, rule}.
Ids are fingerprints (rule + place), so a re-run that edits the comment keeps them stable.
"""
from __future__ import annotations

import fnmatch
import hashlib
import re
from html import unescape

SEV = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}   # the cockpit's three levels
RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _bot(login: str | None, globs: list[str]) -> bool:
    # only * is a wildcard: the [bot] suffix is literal, not a character class
    return bool(login) and any(fnmatch.fnmatchcase(login.lower(), g.lower().replace("[", "[[]")) for g in globs)


def _fid(pr: dict, source: str, *parts) -> str:
    h = hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:10]
    return f"s-{source}-{pr['key'].replace('/', '-').replace('#', '-')}-{h}"


def _strip(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s)).replace("`", "").strip()


def _finding(pr, source, name, kind, *, key, severity, title, body, path=None, line=None, end_line=None, rule=None, url=None, status=None):
    sev = (severity or "medium").lower()
    f = {"id": _fid(pr, source, *key), "pr": pr["key"], "source": source, "category": "security",
         "severity": SEV.get(sev, "medium"), "path": path, "line": line, "end_line": end_line if end_line is not None else line, "side": "RIGHT",
         "title": title, "body": body, "url": url, "scanner": {"name": name, "kind": kind, "rule": rule, "severity": sev}}
    if status:
        f["status"] = status
    return f


MANIFESTS = re.compile(r"(^|/)(requirements[^/]*\.(txt|in)|pyproject\.toml|setup\.(py|cfg)|Pipfile(\.lock)?|poetry\.lock|uv\.lock"
                       r"|package\.json|go\.mod|Cargo\.toml|Gemfile|pom\.xml|build\.gradle(\.kts)?|composer\.json|[^/]+\.csproj"
                       r"|\.github/workflows/[^/]+\.ya?ml)$")
LOCKS = re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|go\.sum|Cargo\.lock|Gemfile\.lock|composer\.lock)$")


def _added(f: dict):
    for h in f.get("hunks", []):
        for ln in h["lines"]:
            if ln[0] == "+":
                yield ln[2], ln[3] or ""


def _manifest_at(pr: dict, pkg: str | None = None) -> tuple[str | None, int | None]:
    """Where a dependency changed: the added line declaring `pkg` in a manifest (then a lockfile), or
    with no package the first added line of a changed manifest. Nothing when there is no such line."""
    decl = _named(pkg) if pkg else None
    for pat in (MANIFESTS, LOCKS):
        for f in pr.get("files", []):
            if not pat.search(f["path"]):
                continue
            for n, text in _added(f):
                if decl is None or decl.search(text):
                    return f["path"], n
    return None, None


def _named(pkg: str):
    """A package name as a whole token in a manifest line: "gitpython" matches `gitpython==3`, never `mygitpython`."""
    return re.compile(r"(^|[\s\"'/=:@\[,])" + re.escape(pkg) + r"([\s\"'=<>~!^@:,\]\[;]|$)", re.I)


def _line_with(pr: dict, path: str, tokens: list[str]) -> int | None:
    """The first added line of `path` that names one of `tokens` (a dependency), else its first change."""
    f = next((x for x in pr.get("files", []) if x["path"] == path), None)
    for t in tokens:
        hit = next((n for n, text in _added(f) if _named(t).search(text)), None) if f else None
        if hit:
            return hit
    return _first_change(pr, path)


def _first_change(pr: dict, path: str) -> int | None:
    f = next((x for x in pr.get("files", []) if x["path"] == path), None)
    return next((n for n, _ in _added(f)), None) if f else None


def _tables(md: str) -> list[tuple[str, list[dict]]]:
    """Each <details> block of a summary comment: its <summary> label and its table rows as dicts."""
    out = []
    for m in re.finditer(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", md, re.S):
        label, inner = _strip(m.group(1)), m.group(2)
        rows = [r for r in inner.splitlines() if r.strip().startswith("|")]
        if len(rows) < 3:
            continue
        cols = [_strip(c) for c in rows[0].strip().strip("|").split("|")]
        out.append((label, [dict(zip(cols, [c.strip() for c in r.strip().strip("|").split("|")])) for r in rows[2:]]))
    return out


def _gate(pr: dict, globs: list[str]) -> dict:
    """Latest state of this scanner's commit statuses, by context."""
    return {c["name"]: (c.get("state") or "").lower() for c in pr.get("checks", [])
            if any(fnmatch.fnmatch(c.get("name") or "", g) for g in globs)}


SNYK_SEV = re.compile(r"severity-(critical|high|medium|low)\.svg")


def snyk(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    name, out = conf.get("name", "Snyk"), []
    gate = _gate(pr, conf.get("statuses", ["*snyk*"]))
    code_ok = any(k.startswith("code/") and v == "success" for k, v in gate.items())
    inline_code = 0
    summaries = [c for c in comments if not c.get("path") and "Snyk checks have" in (c.get("body") or "")[:200]]
    comments = [c for c in comments if c.get("path")] + summaries[:1]   # inline issues, then the latest summary only
    for c in comments:
        body = c.get("body") or ""
        if c.get("path"):   # Snyk Code: one inline comment per issue
            head = re.search(r"^###\s*(.*)$", body, re.M)
            if not head:
                continue
            sev = SNYK_SEV.search(head.group(1))
            title = _strip(head.group(1).replace("&nbsp;", " "))
            msg = body[head.end():].split("<h6>")[0].strip()
            h6 = re.search(r"<h6>(.*?)</h6>", body, re.S)
            cwe = re.search(r">(CWE-\d+)<", h6.group(1)) if h6 else None
            score = re.search(r"Priority score (\d+)", body)
            learn = re.search(r'href="(https://learn\.snyk\.io[^"]+)"', body)
            steps = re.search(r"Data flow: (\d+) steps", body)
            extra = " · ".join(x for x in (cwe and cwe.group(1), score and f"priority score {score.group(1)}",
                                           steps and f"data flow of {steps.group(1)} steps") if x)
            status = "outdated" if c.get("outdated") else ("resolved" if code_ok else None)
            out.append(_finding(pr, "snyk", name, "sast", key=(c["path"], cwe and cwe.group(1), title),
                                severity=sev.group(1) if sev else "medium", title=title,
                                body=_strip(msg) + (f"\n\n{extra}." if extra else "") + (f" [Learn more]({learn.group(1)})" if learn else ""),
                                path=c["path"], line=c.get("line"), rule=cwe and cwe.group(1), url=c.get("url"), status=status))
            inline_code += status is None
            continue
        if "Snyk checks have" not in body[:200]:
            continue
        # The summary table: Open Source and Licenses have no per-issue detail on GitHub, only counts and a link
        for r in [r for r in body.splitlines() if r.startswith("|") and ":no_entry:" in r]:
            cells = [x.strip() for x in r.strip().strip("|").split("|")]
            if len(cells) < 7:
                continue
            engine, counts = cells[1], dict(zip(("critical", "high", "medium", "low"), (int(x) if x.isdigit() else 0 for x in cells[2:6])))
            if engine.startswith("Code") and inline_code:
                continue   # already listed one by one
            worst = next((k for k in RANK if counts[k]), "medium")
            link = re.search(r"\((https://app\.snyk\.io[^)]+)\)", cells[6])
            n = sum(counts.values())
            kind = "license" if engine.startswith("Licen") else "sca" if engine.startswith("Open") else "sast"
            what = ", ".join(f"{v} {k}" for k, v in counts.items() if v)
            path, line = _manifest_at(pr) if kind in ("sca", "license") else (None, None)
            out.append(_finding(pr, "snyk", name, kind, key=("summary", engine), severity=worst, path=path, line=line,
                                title=f"Snyk {engine}: {n} issue{'s' if n != 1 else ''} ({what})",
                                body=f"Snyk lists these only in its console, not on GitHub.{f' [Open in Snyk]({link.group(1)})' if link else ''}",
                                url=link.group(1) if link else c.get("url")))
    return out


UPWIND_KIND = {"code": "sca", "iac": "iac", "secrets": "secret"}


def upwind(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    name, out, done = conf.get("name", "Upwind"), [], set()
    for c in comments:   # newest first: each scan's latest result wins, older ones are history
        body = c.get("body") or ""
        head = re.search(r"Upwind (Code|IaC|Secrets)? ?Scan(?: - ([^\n<]+))?", body[:600])
        if not head or (head.group(1) or "") in done:
            continue
        done.add(head.group(1) or "")
        if "Scan Failed" in (head.group(2) or ""):
            out.append(_finding(pr, "upwind", name, "gate", key=("failed",), severity="low", title="Upwind scan failed",
                                body="Upwind could not scan this PR, so its findings are unknown.", url=c.get("url")))
            continue
        kind = UPWIND_KIND.get((head.group(1) or "").lower(), "sca")
        console = re.search(r"\((https://console\.upwind\.io[^)]+)\)", body)
        groups: dict[tuple, dict] = {}
        for label, rows in _tables(body):
            lab = re.sub(r"[^a-z ]", "", label.split("·")[0].lower()).strip()   # "🔴 Critical · 1 finding" -> "critical"
            if lab.startswith("scan history"):
                continue
            resolved = lab.startswith("resolved")
            sev = lab if lab in RANK else ("medium" if lab == "pii" else "high") if kind == "secret" else "medium"
            for r in rows:
                if kind == "sca":
                    pkg, cve = _strip(r.get("Package", "")), _strip(r.get("CVE", ""))
                    g = groups.setdefault((pkg, resolved), {"cves": [], "sev": sev, "ver": _strip(r.get("Version", "")), "fix": set()})
                    if cve not in g["cves"]:
                        g["cves"].append(cve)
                    g["sev"] = min(g["sev"], sev, key=lambda s: RANK.get(s, 9))
                    if _strip(r.get("Fix", "")) not in ("", "—"):
                        g["fix"].add(_strip(r["Fix"]))
                elif kind == "iac":
                    rule, file, res = _strip(r.get("Rule", "")), _strip(r.get("File", "")), _strip(r.get("Resource", ""))
                    g = groups.setdefault((rule, resolved), {"places": [], "sev": sev})
                    g["places"].append((file, res))
                    g["sev"] = min(g["sev"], sev, key=lambda s: RANK.get(s, 9))
                else:
                    m = re.search(r"\[`?([^\]`]+)`?\]\(([^)]+)\)", r.get("File", ""))
                    file = m.group(1) if m else _strip(r.get("File", ""))
                    ln = int(_strip(r.get("Line", "")) or 0) or None
                    typ = _strip(r.get("Type", "")) or "Secret"
                    out.append(_finding(pr, "upwind", name, "secret", key=(file, ln, typ), severity=sev,
                                        title=f"{typ} committed in {file.rsplit('/', 1)[-1]}",
                                        body=f"Upwind flags a value of type {typ} ({_strip(r.get('Value', '')) or 'masked'}). "
                                             "A pushed secret stays in git history even after the line is removed.",
                                        path=file, line=ln, rule=typ, url=m.group(2) if m else c.get("url"),
                                        status="resolved" if resolved else None))
        for (k, resolved), g in groups.items():
            if kind == "sca":
                path, line = _manifest_at(pr, k)
                fix = max(g["fix"], key=lambda v: [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", v)]) if g["fix"] else None
                out.append(_finding(pr, "upwind", name, "sca", key=("sca", k), severity=g["sev"],
                                    title=f"{k} {g['ver']} has {len(g['cves'])} known vulnerabilit{'ies' if len(g['cves']) > 1 else 'y'}",
                                    body=f"{', '.join(g['cves'])}." + (f" Upgrade to {fix} or later." if fix else " No fixed version yet.")
                                         + (f" [Upwind console]({console.group(1)})" if console else ""),
                                    path=path, line=line, rule=g["cves"][0], url=console.group(1) if console else c.get("url"),
                                    status="resolved" if resolved else None))
            else:
                files = sorted({f for f, _ in g["places"] if f})
                res = [r for _, r in g["places"] if r and r != "—"]
                changed = {x["path"] for x in pr.get("files", [])}
                at = next((f for f in files if f in changed), files[0] if files else None)
                out.append(_finding(pr, "upwind", name, "iac", key=("iac", k), severity=g["sev"],
                                    title=f"{k} ({len(g['places'])} place{'s' if len(g['places']) > 1 else ''})",
                                    body="In " + ", ".join(f"`{f}`" for f in files) + "." + (f" Resources: {', '.join(res[:6])}." if res else ""),
                                    path=at, line=_first_change(pr, at) if at else None, rule=k,
                                    url=console.group(1) if console else c.get("url"),
                                    status="resolved" if resolved else None))
    return out


def code_scanning(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """GitHub code scanning's inline comments: "## <Tool> / <rule>" for CodeQL and any tool that uploads
    SARIF (Semgrep, Trivy, Checkov, SonarQube Cloud...). The tool becomes the scanner's name."""
    out = []
    for c in comments:
        body = c.get("body") or ""
        m = re.match(r"\s*##\s*([^/\n]+?)\s*/\s*(.+)", body)
        if not (m and c.get("path")):
            continue
        tool, rule = m.group(1).strip(), m.group(2).strip()
        more = re.search(r"\[Show more details\]\((\S+/code-scanning/(\d+))\)", body)
        sonar_key = re.search(r"SONAR_ISSUE_KEY:([\w-]+?)-->", body)
        msg = re.sub(r"\[([^\]]+)\]\(\d+\)", r"\1", body[m.end():].split("[Show more details]")[0])
        f = _finding(pr, "code_scanning", tool, "sast", key=(more.group(2) if more else c["path"], rule), severity="medium",
                     title=rule, body=_strip(msg), path=c["path"], line=c.get("line"), rule=rule,
                     url=more.group(1) if more else c.get("url"), status="outdated" if c.get("outdated") else None)
        if sonar_key:   # the same issue as Sonar's own annotation: one id, so it is listed once
            f["id"], f["category"] = _fid(pr, "sonar", "issue", sonar_key.group(1)), "general"
        out.append(f)
    return out


SONAR_GATE = re.compile(r"\*\*Quality Gate (passed|failed)(?: for '([^']+)')?\*\*|SonarCloud Quality Gate (passed|failed)", re.I)
# "![](.../failed-16px.png '') [16.8% Duplication on New Code](url) (required ≤ 3%)"
SONAR_ITEM = re.compile(r"!\[\]\([^)]*/(passed|failed|accepted)[^)]*\)\s*\[([^\]]+)\]\((https://[^)\s]+)\)(?:\s*\((required[^)]*)\))?")
SONAR_OLD = re.compile(r"\[(\d+) (Bugs?|Vulnerabilit(?:y|ies)|Security Hotspots?|Code Smells?)\]")


def _sonar_category(conds: list[str]) -> str:
    text = " ".join(conds)
    return ("security" if re.search(r"Security|Vulnerab", text) else "bug" if re.search(r"Reliability|Bug", text)
            else "tests" if "Coverage" in text else "general")


def _sonar_sev(conds: list[str]) -> str:
    for c in conds:
        m = re.match(r"([A-E]) (Security|Reliability) Rating", c)
        if (m and m.group(1) in "DE") or (m and m.group(2) == "Security") or re.search(r"Security Hotspots?|Vulnerabilit", c):
            return "high"
    return "medium"


def sonar(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """SonarQube Cloud: the quality gate from its PR comment (the latest per project; it reposts on every
    analysis), and one finding per issue from its check run's annotations, which is the only place
    Sonar puts file and line."""
    name, out, seen = conf.get("name", "SonarQube"), [], set()
    anns = [a for a in _annotations(pr, conf) if a.get("path")]
    for c in comments:   # newest first
        body = c.get("body") or ""
        g = SONAR_GATE.search(body)
        if not g:
            continue
        dash = re.search(r"\((https://[^)\s]*/dashboard\?[^)\s]+)\)", body)
        proj = g.group(2) or (re.search(r"[?&]id=([^&)\s]+)", dash.group(1)).group(1) if dash else "")
        if proj in seen:
            continue
        seen.add(proj)
        state, url, tag = (g.group(1) or g.group(3)).lower(), dash.group(1) if dash else c.get("url"), f" ({g.group(2)})" if g.group(2) else ""
        items = SONAR_ITEM.findall(body)
        if state == "failed":
            failed = [(label.strip(), u, req) for st, label, u, req in items if st == "failed"]
            failed = failed or [(f"{n} {what}", url, "") for n, what in SONAR_OLD.findall(body) if n != "0"]   # the 2023 format
            conds = [l for l, _, _ in failed]
            f = _finding(pr, "sonar", name, "gate", key=("gate", proj), severity=_sonar_sev(conds),
                         title=f"SonarQube quality gate failed{tag}" + (f": {', '.join(conds)}"[:140] if conds else ""),
                         body="; ".join(f"[{l}]({u})" + (f" ({r})" if r else "") for l, u, r in failed) + f". [Analysis]({url})",
                         url=url)
            f["category"] = _sonar_category(conds)
            out.append(f)
        else:
            n = next((int(m.group(1)) for _, label, _, _ in items if (m := re.match(r"(\d+) New issues?", label.strip()))), 0)
            if n and not anns:   # without the annotations, at least the count
                f = _finding(pr, "sonar", name, "sast", key=("issues", proj), severity="low",
                             title=f"SonarQube: {n} new issue{'s' if n != 1 else ''}, gate passed{tag}",
                             body=f"[Open the issues]({url}).", url=url)
                f["category"] = "general"
                out.append(f)
    for a in anns:
        link = re.search(r"(https://\S+)", a.get("message") or "")
        key = re.search(r"issues=([\w-]+)", a.get("message") or "")
        out.append(_finding(pr, "sonar", name, "sast", key=("issue", key.group(1)) if key else (a["path"], a.get("line"), a["title"]),
                            severity={"failure": "high", "warning": "medium"}.get(a.get("level"), "low"), title=a["title"],
                            body=f"[Open in SonarQube]({link.group(1)})" if link else "", path=a["path"], line=a.get("line"), end_line=a.get("end_line"),
                            url=link.group(1) if link else a.get("url")))
        out[-1]["category"] = "general"   # an annotation doesn't say bug, smell or vulnerability
    return out


def _review(f: dict) -> dict:
    """An AI reviewer's finding: a code issue, not necessarily a security one."""
    f["category"] = "general"
    return f


CODEX_SEV = {"P0": "critical", "P1": "high", "P2": "medium", "P3": "low"}


def codex(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """OpenAI Codex review: one inline comment per suggestion, "![P1 Badge](...)  **Title**" then the reasoning."""
    out = []
    for c in comments:
        body = c.get("body") or ""
        m = re.search(r"!\[(P[0-3]) Badge\][^\n]*?</sub></sub>\s*(.+?)\*\*", body)
        if not (m and c.get("path")):
            continue
        text = body[m.end():].split("Useful? React with")[0]
        out.append(_review(_finding(pr, "codex", conf.get("name", "Codex"), "review", key=(c["path"], m.group(2).strip(), c.get("id") or c.get("line")),
                                    severity=CODEX_SEV[m.group(1)], title=_strip(m.group(2)), body=_strip(text),
                                    path=c["path"], line=c.get("line"), rule=m.group(1), url=c.get("url"),
                                    status="outdated" if c.get("outdated") else None)))
    return out


COPILOT_ITEM = re.compile(r'alt="(High|Medium|Low|Critical) severity"[^\n]*?\[([^\]]+)\]\(#discussion_r(\d+)\)')


def copilot(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """GitHub Copilot code review: inline comments by "Copilot", with severity and a title only in the
    latest review overview, which lists them as Open or Resolved and links each by its comment id."""
    sev, resolved = {}, set()
    overview = next((c for c in comments if "ccr-overview" in (c.get("body") or "")), None)
    if overview:
        for part in re.split(r"<summary>", overview["body"])[1:]:
            closed = re.match(r"\s*<strong>\s*(Resolved|Addressed|Fixed|Dismissed)", part)
            for level, title, cid in COPILOT_ITEM.findall(part):
                sev[int(cid)] = (level.lower(), _strip(title))
                if closed:
                    resolved.add(int(cid))
    out = []
    for c in comments:
        if not c.get("path"):
            continue
        level, title = sev.get(c.get("id"), ("medium", None))
        body = _strip(c.get("body") or "")
        title = title or (re.split(r"(?<=[.!?])\s", body, 1)[0][:120])
        status = "resolved" if c.get("id") in resolved else "outdated" if c.get("outdated") else None
        out.append(_review(_finding(pr, "copilot", conf.get("name", "Copilot"), "review", key=(c.get("id"),), severity=level,
                                    title=title, body=body, path=c["path"], line=c.get("line"), url=c.get("url"), status=status)))
    return out


def gitguardian(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """GitGuardian: a table of hardcoded secrets in the latest comment, one row per occurrence (per commit);
    one finding per incident, on the line the "View secret" link points at."""
    c = next((c for c in comments if "GitGuardian" in (c.get("body") or "")[:300]), None)
    if not c:
        return []
    out = []
    for inc, url, rest, cells in _gg_incidents(c["body"]):
        state, kind, path = cells[0], cells[1], cells[3]
        line = re.search(r"R(\d+)\)", rest)
        out.append(_finding(pr, "gitguardian", conf.get("name", "GitGuardian"), "secret", key=(inc,), severity="high",
                            title=f"{kind} committed in {path.rsplit('/', 1)[-1]}",
                            body=f"GitGuardian incident {inc} ({state}). A pushed secret stays in git history even after the "
                                 f"line is removed: rotate it. [Open the incident]({url})",
                            path=path, line=int(line.group(1)) if line else None,
                            rule=kind, url=url, status=None if state.lower() == "triggered" else "resolved"))
    return out


def _gg_incidents(body: str):
    """GitGuardian's table, one (incident, url, row, cells) per incident; cells[0] is its state."""
    seen = set()
    for inc, url, rest in re.findall(r"^\|\s*\[(\d+)\]\((https://dashboard\.gitguardian\.com[^)]+)\)\s*\|(.+)$", body, re.M):
        cells = [x.strip() for x in rest.split("|")]
        if inc not in seen and len(cells) >= 4:
            seen.add(inc)
            yield inc, url, rest, cells


def _pkg(spec: str) -> str:
    """A package without its version: "@scope/pkg@1.0" -> "@scope/pkg", "npm/left-pad@1" -> "npm/left-pad"."""
    at = spec.rfind("@")
    return spec[:at] if at > 0 and spec[at - 1] != "/" else spec


SOCKET_SEV = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}


def socket(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """Socket: the latest "Review the following alerts" comment; one row per dependency alert (Block, Warn, Monitor)."""
    c = next((c for c in comments if "Review the following alerts" in (c.get("body") or "")[:400]), None)
    if not c:
        return []
    out = []
    for row in re.findall(r"<tr>\s*<td[^>]*>(?:<strong>)?(Block|Warn|Monitor|Ignore)(?:</strong>)?</td>(.*?)</tr>", c["body"], re.S):
        action, cells = row
        level = re.search(r'title="(\w+)"', cells)
        head = re.search(r"<summary><strong>([^<]+)</strong>:\s*(.*?)</summary>", cells, re.S)
        alert = re.search(r'href="(https://socket\.dev/dashboard/[^"]*(?:alert_item_key=|/alert/)([^"&/?]+))"', cells)
        src = re.search(r"<strong>From:</strong>\s*<a[^>]*>([^<]+)</a>(?:\s*→\s*<code>([^<]+)</code>)?", cells)
        if not head:
            continue
        what, detail = _strip(head.group(1)), _strip(head.group(2))
        pkg = re.search(r"<code>([^<]+)</code>", head.group(2))
        name = pkg and _pkg(pkg.group(1))
        name = name and (name if name.startswith("@") else name.rsplit("/", 1)[-1])
        direct = src and src.group(2) and _pkg(src.group(2)).split("/", 1)[-1]   # golang/github.com/x/y@v1 -> github.com/x/y, npm/@s/p@1 -> @s/p
        path, line = (src.group(1), _line_with(pr, src.group(1), [t for t in (direct, name) if t])) if src else _manifest_at(pr, name)
        sev = SOCKET_SEV.get((level.group(1) if level else "medium").lower(), "medium")
        out.append(_finding(pr, "socket", conf.get("name", "Socket"), "sca", key=(alert.group(2),) if alert else (what, detail, path, direct),
                            severity=sev, title=f"{what}: {pkg.group(1) if pkg else detail}"[:140],
                            body=f"Socket ({action}): {detail}." + (f" [Open the alert]({alert.group(1)})" if alert else ""),
                            path=path, line=line, rule=what, url=alert.group(1) if alert else c.get("url"),
                            status="dismissed" if action == "Ignore" else None))
    return out


ANN_SEV = {"failure": "medium", "warning": "low"}


def check_annotations(pr: dict, comments: list[dict], conf: dict) -> list[dict]:
    """Check-run annotations of the tools the config names (Codacy, DeepSource, Qlty, a linter job):
    failure is medium, warning low; notices, annotations without a file and .github ones are noise."""
    out, src = [], conf.get("_key", "check_annotations")
    for a in _annotations(pr, conf):
        if not a.get("path") or a["path"].startswith(".github") or a.get("level") not in ANN_SEV:
            continue
        title, msg = _strip(a.get("title") or ""), _strip(a.get("message") or "")
        if not title or title.startswith(a["path"]):   # Codacy titles an annotation with its own path#L35
            title, msg = msg.split("\n")[0], "\n".join(msg.split("\n")[1:]).strip()
        # a linter job's config says `"kind": "lint"` (its findings group with conventions); the default stays sast
        out.append(_finding(pr, src, conf.get("name", a.get("check") or "Checks"), conf.get("kind", "sast"), key=(a["path"], a.get("line"), title),
                            severity=ANN_SEV[a["level"]], title=title[:140] or a.get("check") or "Check annotation",
                            body=msg, path=a["path"], line=a.get("line"), end_line=a.get("end_line"), url=a.get("url")))
        out[-1]["category"] = "general"
    return out


PARSERS = {"snyk": snyk, "upwind": upwind, "code_scanning": code_scanning, "codeql": code_scanning, "sonar": sonar,
           "codex": codex, "copilot": copilot, "gitguardian": gitguardian, "socket": socket, "check_annotations": check_annotations}


def _annotations(pr: dict, conf: dict) -> list[dict]:
    """The check-run annotations that belong to this scanner, by check name or app slug."""
    return [a for a in pr.get("_annotations", []) if any(fnmatch.fnmatchcase(a.get("check") or "", g)
            or fnmatch.fnmatchcase(a.get("app") or "", g) for g in conf.get("checks", []))]


def _mine(pr: dict, cfg: dict):
    """(parser, conf, its bot's comments newest first) for each enabled scanner."""
    raw = [c for c in pr.get("_raw_comments", []) if not c.get("reply_to")]
    for key, conf in (cfg.get("scanners") or {}).items():
        if conf.get("parser", key) not in PARSERS or conf.get("enabled") is False:
            continue
        yield key, {**conf, "_key": key}, sorted((c for c in raw if _bot(c.get("author"), conf.get("logins", []))),
                                   key=lambda c: c.get("updated") or c.get("created") or "", reverse=True)   # latest scan first


def _headline(parser: str, comments: list[dict]) -> str | None:
    """The scanner's own verdict from its latest comment, in a few words."""
    if parser == "copilot":
        c = next((c for c in comments if "ccr-overview" in (c.get("body") or "")), None)
        m = c and re.search(r"^###\s*(.+)$", c["body"], re.M)
        return re.sub(r"[^\w ,.-]", "", m.group(1)).strip().lower() if m else None
    if parser == "gitguardian":
        c = next((c for c in comments if "GitGuardian" in (c.get("body") or "")[:300]), None)
        m = c and re.search(r"GitGuardian has uncovered", c["body"])
        if c and not m and re.search(r"no secrets", c["body"], re.I):
            return "passed, no secrets"
        if m and not any(cells[0].lower() == "triggered" for *_, cells in _gg_incidents(c["body"])):
            return "passed, secrets resolved"
        return "failed, hardcoded secrets" if m else None   # its count is occurrences; the findings are incidents
    if parser == "snyk":
        c = next((c for c in comments if "Snyk checks have" in (c.get("body") or "")[:200]), None)
        m = c and re.search(r"Snyk checks have (passed|failed)", c["body"])
        return ("passed, no issues" if m.group(1) == "passed" else "failed") if m else None
    if parser == "upwind":
        parts, done = [], set()
        for c in comments:
            body = c.get("body") or ""
            m = re.search(r"Upwind (Code|IaC|Secrets)? ?Scan(?: - ([^\n<]+))?", body[:600])
            if not m or (m.group(1) or "") in done:
                continue
            done.add(m.group(1) or "")
            new = re.search(r"\*\*(\d+) newly introduced", body)
            tot = re.search(r"\*\*(\d+) total\*\*", body)
            verdict = re.sub(r"[^A-Za-z ]", "", m.group(2) or "").strip().lower()
            if not verdict:   # the Secrets scan says it in its quote line instead of the heading
                verdict = "passed" if re.search(r"No secrets found", body) else "scanned"
            parts.append(f"{m.group(1) or 'scan'} {verdict}" + (f", {new.group(1)} new" if new else "") + (f" of {tot.group(1)}" if tot else ""))
        return " · ".join(sorted(parts)) or None
    if parser == "sonar":
        m = next((re.search(r"Quality Gate (passed|failed)", c.get("body") or "", re.I) for c in comments
                  if re.search(r"Quality Gate", c.get("body") or "", re.I)), None)
        return f"quality gate {m.group(1).lower()}" if m else None
    return None


def scans(pr: dict, cfg: dict, findings: list[dict]) -> list[dict]:
    """One line per scanner that ran on the PR, so a clean scan shows up too: {name, status, open, text, url}."""
    out = []
    for parser, conf, mine in _mine(pr, cfg):
        gate = _gate(pr, conf.get("statuses", []))
        anns = _annotations(pr, conf)
        if not (mine or gate or anns):
            continue
        n = sum(1 for f in findings if parser in (f.get("source"), (f.get("scanner") or {}).get("key")) and not f.get("status"))
        head = _headline(conf.get("parser", parser), mine)
        if head:   # the scanner's own verdict; its open findings are counted next to it
            failed = bool(re.search(r"failed|blocked|changes", head, re.I))
            text = head + (f" · {n} open" if n else "")
        elif not (n or gate or anns) and all(c.get("path") for c in mine):
            continue   # only inline comments, none open: outdated, or another scanner's issues (code scanning relaying Sonar)
        else:
            failed = bool(n) or any(v in ("failure", "error") for v in gate.values())
            text = f"{n} open finding{'s' if n != 1 else ''}" if (mine or anns) else ", ".join(f"{k}: {v}" for k, v in gate.items())
        out.append({"name": conf.get("name", parser), "status": "failed" if failed else "passed", "open": n, "text": text,
                    "url": mine[0].get("url") if mine else None})
    return out


def collect(pr: dict, cfg: dict) -> list[dict]:
    out, seen = [], set()
    for parser, conf, mine in _mine(pr, cfg):
        for f in PARSERS[conf.get("parser", parser)](pr, mine, conf):
            if f["id"] not in seen:
                f["scanner"]["key"] = parser   # the config key, which may name another parser (scans() counts by it)
                seen.add(f["id"]); out.append(f)
    return out

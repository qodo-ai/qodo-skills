"""Parse Qodo bot comments already present on a PR into findings.

Qodo posts three kinds of comments (format verified on Qodo's own PRs, 2026-10):
- "PR Summary by Qodo": description, labels and a mermaid diagram. Not findings; see `pr_context`.
- "Code Review by Qodo": one big comment holding every open finding as a `<details>` item under a
  severity badge (High/Medium/Low), followed by a "Resolved findings" section.
- Inline review comments: one finding each, anchored to a line, with the same badge and labels.
Plus one-line "Code review by qodo was updated up to the latest commit <sha>" notices, which we skip.

Every finding carries a Qodo finding UUID (Dismiss/View links), used to merge the summary item with
its inline comment.

A top-level comment counts only under a findings header, the one part of a Qodo comment that isn't
configurable; notices and answers are ignored. Inline comments always count: they sit on a line.
"""
from __future__ import annotations

import html
import re

CATEGORIES = [
    ("security", r"secur|inject|xss|csrf|secret|credential|auth"),
    ("bug", r"\bbug\b|null|none\b|undefined|race|off-by|exception|crash|incorrect"),
    ("performance", r"perf|slow|n\+1|latency|memory|cache|o\(n"),
    ("tests", r"\btest|coverage"),
    ("naming", r"\bname|naming|rename|typo"),
    ("style", r"style|format|lint|readab"),
    ("docs", r"docstring|comment|documentation|readme"),
]
HIGH = re.compile(r"critical|high|security|vulnerab|data loss|🔴", re.I)
LOW = re.compile(r"\bnit\b|minor|low|style|suggestion|🟢", re.I)

# Qodo labels -> cockpit categories. The aspect (≡ Correctness, ⛨ Security, ...) wins over the type.
ASPECTS = {"correctness": "bug", "reliability": "bug", "security": "security", "testability": "tests",
           "performance": "performance", "maintainability": "style", "readability": "style",
           "documentation": "docs"}
TYPES = {"bug": "bug", "rule violation": "rule", "requirement gap": "requirement",
         "cross-repo conflict": "cross-repo", "skill insight": "general", "memory": "general"}
SEVERITY = {"high": "high", "critical": "high", "action_required": "high", "medium": "medium", "low": "low",
            "optional": "low", "informational": "low", "info": "low"}

BADGE = re.compile(r'img\.shields\.io/badge/(?P<sev>[A-Za-z_]+)-[0-9A-Fa-f]+[^>]*>')
FINDING_LINK = re.compile(r"\((?P<url>https://[^)\s]+/findings/(?P<uuid>[0-9a-f-]{36}))\)")
CODE_REF = re.compile(r"\[(?P<path>[^\[\]\s]+)\[(?P<side>[RL]?)(?P<a>\d+)(?:-(?P<b>\d+))?\]\]")
LABEL = re.compile(r"<code>\s*(?P<text>[^<]+?)\s*</code>")
RULE = re.compile(r"Rule (?P<id>\d+): \[(?P<title>[^\]]+)\]")
UPDATED = re.compile(r"was updated up to the latest commit", re.I)
NOTHING = re.compile(r"^\s*No reviewable changes\.?\s*$", re.I)   # posted on stacked PRs with nothing new
# Header titles of top-level comments that hold findings. Older Qodo Merge: /review and /improve.
LEGACY_HEADERS = re.compile(r"\A\s*(?:#{1,4}\s*|<h[1-4][^>]*>\s*)(?:PR Reviewer Guide|PR Code Suggestions)\b", re.I)


def classify(text: str) -> tuple[str, str]:
    t = text.lower()
    cat = next((c for c, rx in CATEGORIES if re.search(rx, t)), "general")
    sev = "high" if HIGH.search(text) else "low" if LOW.search(text) else "medium"
    return cat, sev


def _title(body: str) -> str:
    for line in body.splitlines():
        s = re.sub(r"[#*_`>]|<[^>]+>", "", line).strip()
        if len(s) > 8:
            return s[:120]
    return "Qodo finding"


def plain(s: str) -> str:
    """Qodo HTML/markdown fragment -> readable text (keeps `code` for <b><i>identifiers</i></b>)."""
    s = re.sub(r"^> ?", "", s, flags=re.M)
    s = re.sub(r"<b><i>(.+?)</i></b>", r"`\1`", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\\.", ".").replace("\\[", "[").replace("\\]", "]")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def unwrap(s: str) -> str:
    """Join Qodo's hard-wrapped <pre> lines; keep blank lines and bullet lines."""
    return re.sub(r"(?<!\n)\n(?![\n•\-*])", " ", s)


def _section(block: str, name: str) -> str:
    """Body of a `<summary>name</summary>` sub-section inside one finding block."""
    m = re.search(rf"<summary>{name}</summary>(.*?)</details>", block, re.S | re.I)
    return m.group(1) if m else ""


def _labels(s: str) -> tuple[str | None, str | None, list[str]]:
    """`<code>🐞 Bug</code> <code>≡ Correctness</code> <code>⭐ New</code>` -> (type, aspect, other)."""
    kind = aspect = None
    other = []
    for m in LABEL.finditer(s):
        text = re.sub(r"^[^\w]+", "", m.group("text")).strip()   # drop the emoji/symbol prefix
        low = text.lower()
        if low in TYPES and not kind:
            kind = text
        elif low in ASPECTS and not aspect:
            aspect = text
        elif text:
            other.append(text)
    return kind, aspect, other


def _category(kind: str | None, aspect: str | None) -> str:
    if aspect and aspect.lower() in ASPECTS:
        return ASPECTS[aspect.lower()]
    return TYPES.get((kind or "").lower(), "general")


def _fix(prompt: str) -> str:
    m = re.search(r"## Recommended Fix\s*\n(.*?)(?:\n## |\n```|$)", prompt, re.S)
    return m.group(1).strip() if m else ""


def _norm(title: str) -> str:
    return re.sub(r"\W+", " ", title).strip().lower()


def _parse_item(head: str, block: str, sev: str | None) -> dict:
    """One finding: `head` holds the numbered title and labels, `block` the details."""
    title_html = re.sub(r"<code>.*?</code>", "", head)
    title = plain(re.sub(r"^\s*\d+\\?\.\s*", "", plain(title_html))).strip()
    kind, aspect, other = _labels(head)
    desc = _section(block, "Description") or ""
    if not desc:   # inline format: description is the first <pre> block
        m = re.search(r"<pre>(.*?)</pre>", block, re.S)
        desc = m.group(1) if m else ""
    evidence = _section(block, "Evidence")
    prompt_m = re.search(r"```\n?(.*?)```", re.sub(r"^> ?", "", _section(block, "Agent prompt") or block, flags=re.M), re.S)
    prompt = prompt_m.group(1).strip() if prompt_m else ""
    code = CODE_REF.search(_section(block, "Code") or "")
    if not code and prompt:   # inline format: "## Fix Focus Areas\n- path[a-b]"
        m = re.search(r"Fix Focus Areas\s*\n-\s*(?P<path>[^\[\s]+)\[(?P<a>\d+)(?:-(?P<b>\d+))?\]", prompt)
        code = m
    link = FINDING_LINK.search(block)
    rule = RULE.search(evidence or block)
    ev_text = plain(re.sub(r"<code>.*?</code>", "", re.sub(r"<pre>|</pre>", "", evidence)))
    fix = _fix(prompt)
    parts = (unwrap(plain(desc)), ev_text and f"**Evidence.** {unwrap(ev_text)}", fix and f"**Fix.** {unwrap(fix)}")
    body = "\n\n".join(x for x in parts if x)
    a = int(code.group("a")) if code else None
    return {
        "title": title or "Qodo finding", "severity": SEVERITY.get((sev or "").lower(), "medium"),
        "category": _category(kind, aspect), "qodo_type": kind, "qodo_aspect": aspect, "labels": other,
        "path": code.group("path") if code else None, "line": a,
        "end_line": int(code.group("b")) if code and code.group("b") else a,
        "side": "LEFT" if code and code.groupdict().get("side") == "L" else "RIGHT",
        "body": body, "prompt": prompt,
        "rule": {"id": rule.group("id"), "title": rule.group("title")} if rule else None,
        "qodo_id": link.group("uuid") if link else None,
        "qodo_url": link.group("url") if link else None,
    }


def parse_review(body: str) -> tuple[list[dict], set[str], str | None]:
    """'Code Review by Qodo' comment -> (open findings, normalized titles of resolved/outdated, omitted note)."""
    # The closed section has had several headings; split on any of them (or the collapsed toggle).
    m = re.search(r"<h3>\s*(?:Resolved|Closed|Addressed)[^<]*</h3>|<summary>\s*<ins>\s*<strong>\s*View resolved", body, re.I)
    open_part, resolved_part = (body[:m.start()], body[m.start():]) if m else (body, "")
    out = []
    # Each item: <details>\n<summary>  N.  Title <code>..</code></summary> ... up to the next item.
    starts = list(re.finditer(r"<details>\s*<summary>\s*\d+\.\s+(?P<head>.*?)</summary>", open_part, re.S))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(open_part)
        badges = list(BADGE.finditer(open_part, 0, m.start()))
        sev = badges[-1].group("sev") if badges else None
        item = _parse_item(m.group("head").replace("<s>", "").replace("</s>", ""), open_part[m.end():end], sev)
        if sev and sev.lower() not in SEVERITY:   # grouped by type ("Bugs"), not by action level
            item["severity_guessed"] = True
        if "<s>" in m.group("head"):            # closed but listed in an open group
            verdict = next((v for v in ("Dismissed", "Outdated", "Resolved") if v in m.group("head")), "Resolved")
            item.update(status=verdict.lower(), status_why=f"{verdict} in Qodo's review.")
        out.append(item)
    resolved = {_norm(plain(t)) for t in re.findall(r"<s>(.*?)</s>", resolved_part)}
    # Closed items keep their verdict, so the reviewer sees what the author dismissed and why it closed.
    rs = list(re.finditer(r"<summary>\s*\d+\.\s+<s>(?P<title>.*?)</s>\s*(?P<labels>(?:<code>.*?</code>\s*)*)</summary>", resolved_part, re.S))
    for i, m in enumerate(rs):
        end = rs[i + 1].start() if i + 1 < len(rs) else len(resolved_part)
        f = _parse_item(m.group("title") + " " + m.group("labels"), resolved_part[m.end():end], None)
        verdict = next((v for v in ("Dismissed", "Outdated", "Resolved") if v in m.group("labels")), "Resolved")
        f.update(title=plain(m.group("title")), severity="low", status=verdict.lower(),
                 status_why=f"{verdict} in Qodo's review.")
        out.append(f)
    om = re.search(r"⚠️\s*_?(.+?omitted[^_\n]*)_?", body)
    return out, resolved, (plain(om.group(1)) if om else None)


def parse_inline(body: str) -> dict | None:
    """One inline finding. Some Qodo versions omit the portal links; the severity badge and the
    numbered title are enough. A struck-through title (<s>...</s>) means Qodo already closed it."""
    m = re.search(r"^\s*(?:<s>)?\s*\d+\\?\.\s+(?P<head>.+)$", body, re.M)
    b = BADGE.search(body)
    if not m or not (FINDING_LINK.search(body) or b):
        return None
    f = _parse_item(m.group("head").replace("<s>", "").replace("</s>", ""), body[m.end():], b.group("sev") if b else None)
    if "<s>" in m.group(0):
        f["status"], f["status_why"] = "resolved", "Struck through by Qodo."
    return f


def _thread(f: dict, rs: list[dict]):
    """Attach replies; a Qodo 'Dismissed - <reason>' reply closes the finding."""
    if not rs:
        return
    f["replies"] = rs
    for r in rs:
        if r["bot"] and re.match(r"\s*Dismissed\b", r["body"]):
            f["status"] = "dismissed"
            f["status_why"] = plain(r["body"].split("If the rule")[0]).strip()
            break


def _is_qodo(c: dict, bots: set[str]) -> bool:
    login = (c.get("author") or "").lower()
    return login in bots or login.startswith("qodo")


def _fid(pr: dict, suffix) -> str:
    return f"q-{pr['key'].replace('/', '-').replace('#', '-')}-{suffix}"


def reviewed(pr: dict, cfg: dict) -> bool:
    """Whether Qodo posted a review on the PR (its findings, or that it found nothing), not only a summary."""
    bots = {b.lower() for b in cfg.get("qodo_bot_logins", [])}
    for c in pr.get("_raw_comments", []):
        body = c.get("body") or ""
        if _is_qodo(c, bots) and not c.get("reply_to") and (
                "Code Review by Qodo" in body[:200] or NOTHING.match(body) or LEGACY_HEADERS.match(body) or c.get("path")):
            return True
    return False


def collect(pr: dict, cfg: dict) -> list[dict]:
    bots = {b.lower() for b in cfg.get("qodo_bot_logins", [])}
    raw = pr.get("_raw_comments", [])
    replies: dict = {}   # comment id -> replies in its thread (Qodo's verdicts and the author's answers)
    for c in raw:
        if c.get("reply_to"):
            replies.setdefault(c["reply_to"], []).append(
                {"author": c.get("author"), "body": (c.get("body") or "")[:600], "url": c.get("url"), "bot": _is_qodo(c, bots)})
    comments = [c for c in raw if _is_qodo(c, bots) and not c.get("reply_to")]
    by_uuid: dict[str, dict] = {}
    resolved: set[str] = set()
    legacy = []
    base = {"pr": pr["key"], "source": "qodo"}

    for c in comments:
        body = c.get("body") or ""
        if (c.get("path") or len(body.strip()) < 10 or UPDATED.search(body[:300]) or NOTHING.match(body)
                or "PR Summary by Qodo" in body[:200]):
            continue
        if "Code Review by Qodo" in body[:200]:
            items, res, note = parse_review(body)
            resolved |= res
            if note:
                pr.setdefault("qodo", {})["omitted"] = note
            for f in items:
                key = f["qodo_id"] or _norm(f["title"])
                if key in by_uuid:   # the same item listed twice (e.g. under 'View resolved')
                    continue
                by_uuid[key] = {**base, **f, "id": _fid(pr, f["qodo_id"] or "r-" + _norm(f["title"]).replace(" ", "-")[:48]),
                                "url": c.get("url")}
            continue
        if LEGACY_HEADERS.match(body):
            legacy.append(c)
        # anything else is not a findings comment: notices, answers, banners

    for c in comments:   # inline comments: anchor to the GitHub line, merge with the summary item
        if not c.get("path") or NOTHING.match(c.get("body") or ""):
            continue
        f = parse_inline(c.get("body") or "")
        if f is None:
            legacy.append(c)
            continue
        tkey = _norm(f["title"])
        if tkey in resolved and f["qodo_id"] not in by_uuid:
            closed = by_uuid.get(tkey)
            if closed is not None and not closed.get("path"):   # give the closed item its place in the code
                closed.update(path=c["path"], line=c.get("line"), url=closed.get("url") or c.get("url"))
            continue
        key = f["qodo_id"] or tkey
        if key not in by_uuid and tkey in by_uuid:   # summary items without finding ids are keyed by title
            by_uuid[key] = by_uuid.pop(tkey)
        prev = by_uuid.get(key, {})
        if c.get("outdated"):
            if prev:   # still open in the summary: keep the summary's location, link the old thread
                prev.setdefault("thread_url", c.get("url"))
                continue
            by_uuid[key] = {**base, **f, "id": _fid(pr, f["qodo_id"] or c["id"]), "url": c.get("url"),
                            "path": c["path"], "line": None, "status": "outdated",
                            "status_why": "The inline comment no longer maps to the current diff."}
            _thread(by_uuid[key], replies.get(c["id"], []))
            continue
        # The inline comment's badge is per finding; a summary group badge may be a guess.
        keep_inline = ("path", "line", "url") + (("severity", "severity_guessed") if prev.get("severity_guessed") else ())
        merged = {**base, **f, **{k: v for k, v in prev.items() if v and k not in keep_inline}}
        merged.update(id=prev.get("id") or _fid(pr, f["qodo_id"] or c["id"]), url=c.get("url"),
                      path=c["path"], line=c.get("start_line") or prev.get("line") or c.get("line") or f["line"],
                      end_line=c.get("line") or prev.get("end_line") or f["end_line"],
                      qodo_aspect=f["qodo_aspect"] or prev.get("qodo_aspect"),
                      category=_category(f["qodo_type"] or prev.get("qodo_type"), f["qodo_aspect"] or prev.get("qodo_aspect")))
        by_uuid[key] = merged
        _thread(merged, replies.get(c["id"], []))

    out = list(by_uuid.values())
    for c in legacy:
        body = c.get("body") or ""
        cat, sev = classify(body)
        out.append({**base, "id": _fid(pr, c["id"]), "category": cat, "severity": sev,
                    "path": c.get("path"), "line": c.get("line"), "title": _title(body), "body": body,
                    "url": c.get("url")})
    return out


def pr_context(pr: dict, cfg: dict) -> dict:
    """What the 'PR Summary by Qodo' comment adds: description bullets, labels, mermaid diagram."""
    bots = {b.lower() for b in cfg.get("qodo_bot_logins", [])}
    for c in pr.get("_raw_comments", []):
        body = c.get("body") or ""
        if c.get("path") or not _is_qodo(c, bots) or "PR Summary by Qodo" not in body[:200]:
            continue
        head = re.search(r"</h3>\s*(.+?)\n", body)
        desc = re.search(r"<summary>AI Description</summary>(.*?)</details>", body, re.S)
        assess = re.search(r"<summary>High-Level Assessment</summary>(.*?)</details>", body, re.S)
        mer = re.search(r"```mermaid\n(.*?)```", body, re.S)
        _, _, labels = _labels(body[:body.find("<details>")] if "<details>" in body else "")
        return {
            "headline": plain(head.group(1)) if head else "",
            "description": plain(desc.group(1)) if desc else "",
            "assessment": plain(assess.group(1)) if assess else "",
            "labels": labels, "url": c.get("url"),
            "diagram": {"id": "qodo", "title": "Qodo: change flow", "mermaid": mer.group(1).strip(),
                        "source": "qodo"} if mer else None,
        }
    return {}

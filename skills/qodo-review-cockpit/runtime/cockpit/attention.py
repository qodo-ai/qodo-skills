"""Review attention: what a human must read closely, read, skim, or can safely skip, and why.

Every meaningful changed line gets a tier (review | skim | skip), a reason, and evidence the reader
can check. Defaults are computed from the diff (semantic marks, file roles, CI, findings); the skill
may override ranges with a stated reason (`prs[key].attention` in enrich.json). Guards win over any
skim or skip: an open high-severity finding, a weakened or disabled test, or code under a confirmed
knowledge invariant always stays on the reading list. Nothing is deleted; skipped code is one click away.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .util import glob_match

TIERS = ("deep", "review", "skim", "skip")   # deep read <= DEEP_SHARE of lines; review is shown as "read"
DEEP_SHARE = 0.05
DEEP_MIN_LINES = 12
DEEP_MIN_SIGNAL = 35   # deep needs a real signal (finding, invariant, story anchor, config, failing or weakened test); test churn alone isn't
ASSERT = re.compile(r"\b(assert\w*|expect\s*\(|should\b|toBe|toEqual|toHave\w*|pytest\.raises|self\.assert\w*|verify\s*\()")
DISABLE = re.compile(r"(@pytest\.mark\.skip|@unittest\.skip|\b(it|describe|test)\.skip\s*\(|\bxit\s*\(|\bxdescribe\s*\(|@Disabled\b|t\.Skip\()")
GENERATED_MARK = re.compile(r"(@generated|DO NOT EDIT|Code generated .* DO NOT EDIT|auto-generated)", re.I)
TRANSLATION = re.compile(r"(^|/)(locales?|i18n|translations?)/|\.(po|xliff)$")
SNAPSHOT = re.compile(r"(^|/)__snapshots__/|\.snap$")
SENSITIVE = re.compile(r"(^|/)\.github/workflows/|(^|/)(Dockerfile|docker-compose[^/]*)$|requirements[^/]*\.txt$|(^|/)(package|pyproject)\.(json|toml)$|\.(tf|hcl)$|(^|/)(auth|security|permissions?|iam)[^/]*(/|\.)", re.I)
GAP = 3   # review lines this close together read as one range
# lines with nothing to read on their own: imports, comments and docstrings. Skipped only as a whole run of
# changed lines, so a comment next to the code it explains stays with it.
BOILER = re.compile(r"""^\s*($|(import|from\s+\S+\s+import)\s|(export\s+)?\*?\s*from\s+['"]|(const|let|var)\s+\w+\s*=\s*require\(|use\s+[\w:]+;|#include\b|package\s+[\w.]+;?$|#(?![!\s]*(if|ifdef|ifndef|elif|else|endif|define|undef|pragma|error|line)\b)(?!!)|//|/\*|\*(\s|/|$)|\)\s*$)""")
DOCQ = re.compile(r'"""|\'\'\'')
DOC_OPEN = re.compile(r"""^\s*[rRbBuUfF]{0,2}(\"\"\"|\'\'\')""")   # a docstring starts its line; `return """x"""` is code
REWRITE_SHARE = 0.5   # removed lines in a hunk that adds at least half as many back: the old side of a rewrite
REWRITE_LIKE = 0.6    # ...and only a removed line the new side has a close version of; one with none was deleted, and stays on Read


def _has_new_version(old: str, new: list[str]) -> bool:
    o = old.strip()
    if not o:
        return True
    for t in new[:200]:
        sm = SequenceMatcher(None, o, t)
        if sm.real_quick_ratio() >= REWRITE_LIKE and sm.quick_ratio() >= REWRITE_LIKE and sm.ratio() >= REWRITE_LIKE:
            return True
    return False


def _ci_ran_green(pr: dict) -> int:
    """How many checks ran and succeeded, when none failed or is still running: 0 otherwise.
    Skipped, neutral or cancelled checks didn't run anything, so they never count as tests passing."""
    if _ci_passed(pr) is not True:
        return 0
    states = [str(k.get("state") or "").upper() for k in pr.get("checks") or []]
    ran = [x for x in states if not re.search(r"SKIP|NEUTRAL|CANCEL", x)]
    if not ran or not all(re.search(r"SUCC|PASS", x) for x in ran):
        return 0
    return len(ran)


def _ci_passed(pr: dict) -> bool | None:
    """True when every check passed, False when one failed, None when unknown or still running."""
    ks = pr.get("checks") or []
    if not ks:
        return None
    states = [str(k.get("state") or "") for k in ks if not re.search(r"CANCEL", str(k.get("state")), re.I)]   # superseded runs
    if any(re.search(r"FAIL|ERROR|TIMED_OUT|ACTION_REQUIRED", x, re.I) for x in states):
        return False
    from .product import enabled
    sections = (pr.get('read_evidence') or {}).get('sections', {})
    if enabled(pr) and any(sections.get(kind, {}).get('complete') is not True for kind in ('checks', 'statuses')):
        return None
    if all(re.search(r"SUCC|PASS|SKIP|NEUTRAL", x, re.I) for x in states):
        return True
    return None


def _boiler_runs(f: dict) -> set[tuple[str, int]]:
    """(side, line) of changed lines in runs made only of imports, comments, docstrings and blanks."""
    out = set()
    for h in f.get("hunks", []):
        runs, cur, sign = [], [], None   # a run: consecutive changed lines of one sign
        for l in h["lines"]:
            if l[0] not in "+-" or l[0] != sign:
                if cur:
                    runs.append(cur)
                cur, sign = [], (l[0] if l[0] in "+-" else None)
            if l[0] in "+-":
                cur.append(l)
        if cur:
            runs.append(cur)
        for run in runs:
            doc, ok = False, True
            for l in run:
                q = len(DOCQ.findall(l[3]))
                if not (doc or (q and DOC_OPEN.match(l[3])) or (BOILER.match(l[3]) and not q)):
                    ok = False
                    break
                if q % 2:
                    doc = not doc
            if ok and any(l[3].strip() for l in run):   # a run of blanks alone isn't worth naming
                out.update(("new", l[2]) if l[0] == "+" else ("old", l[1]) for l in run)
    return out


def _file_default(f: dict, pr: dict, additive_tests: str = "skip") -> tuple[str, str, str]:
    """Tier, reason and evidence for a file's ordinary changed lines."""
    path, role = f["path"], f.get("role", "source")
    added = [l[3] for h in f.get("hunks", []) for l in h["lines"] if l[0] == "+"]
    if role == "generated" or any(GENERATED_MARK.search(t) for t in added[:5]):
        return "skip", "generated", "generated or lock file (path or header marker)"
    if SNAPSHOT.search(path):
        return "skim", "snapshots", "test snapshot output"
    if TRANSLATION.search(path):
        return "skim", "translation strings", "copy in a locale file"
    if role == "test":
        ci = _ci_passed(pr)
        edited = sum(1 for h in f.get("hunks", []) for l in h["lines"]
                     if l[0] == "-" and not (len(l) > 4 and (l[4].get("move") or l[4].get("ws"))))
        if ci is False:
            return "review", "tests, CI failing", "a required check did not pass"
        if edited:   # existing expectations changed: that is behavior, not just more coverage
            return "review", "tests changed", f"{edited} existing test line(s) edited or removed"
        green = _ci_ran_green(pr)
        if green and additive_tests == "skip":   # CI ran and passed; the walkthrough lists the new tests by name
            return "skip", "tests, additive", f"only new test lines · {green} check(s) ran and passed · the walkthrough lists them by name"
        return "skim", "tests, additive", "only new test lines" + (" · CI passed" if ci else "")
    if role == "docs":
        return "skim", "docs", "documentation only"
    if SENSITIVE.search(path):
        return "review", "build, dependency or access config", path
    return "review", "code", ""


def weakening(f: dict) -> dict:
    """What a test file's diff loses: assertions removed and tests disabled, each with its line, and the assertions
    added back. `net` is what counts: a rewrite that swaps assertions one for one is not a weakening."""
    plain = lambda l: not (len(l) > 4 and (l[4].get("move") or l[4].get("ws")))
    lines = [l for h in f.get("hunks", []) for l in h["lines"]]
    removed = [{"side": "old", "line": l[1], "text": l[3].strip()} for l in lines if l[0] == "-" and ASSERT.search(l[3]) and plain(l)]
    disabled = [{"side": "new", "line": l[2], "text": l[3].strip()} for l in lines if l[0] == "+" and DISABLE.search(l[3])]
    added = sum(1 for l in lines if l[0] == "+" and ASSERT.search(l[3]))
    return {"removed": removed, "disabled": disabled, "asserts_added": added, "net": len(disabled) + max(0, len(removed) - added)}


def _weakened(f: dict) -> tuple[int, str]:
    """Assertions removed (net) or tests disabled in a test file, with examples for the evidence."""
    w = weakening(f)
    if not w["net"]:
        return 0, ""
    ex = [x["text"] for x in w["disabled"] + w["removed"]][:2]
    return w["net"], f"{w['net']} assertion(s) lost or test(s) disabled, e.g. " + "; ".join(f"`{x[:70]}`" for x in ex)


def _overrides_for(overrides: list[dict], path: str, n: int, side: str = "new") -> dict | None:
    hit = None
    for o in overrides:
        if o.get("side", "new") != side and (o.get("from") is not None or o.get("side")):
            continue   # line ranges are per side; a path or glob without side covers both
        if o.get("path") != path and not (o.get("glob") and glob_match(path, o["glob"])):
            continue
        if o.get("from") is not None and not (o["from"] <= n <= o.get("to", o["from"])):
            continue
        hit = o   # the last matching override wins
    return hit


def compute(pr: dict, *, overrides: list[dict] | None = None, concepts: list[dict] | None = None,
            rules: list[dict] | None = None, anchors: list[dict] | None = None,
            additive_tests: str = "skip") -> tuple[dict, list[str]]:
    """Return (attention, warnings). attention = {summary, ranges, blocks, must_read}.
    `anchors` are spans the story points at ({path, from, to, why}); they weigh toward deep read."""
    warn: list[str] = []
    overrides = overrides or []
    for o in overrides:
        if o.get("tier") not in TIERS:
            warn.append(f"{pr['key']} attention: tier must be deep|review|skim|skip ({o})")
        if not o.get("reason"):
            warn.append(f"{pr['key']} attention: every override needs a reason ({o.get('path') or o.get('glob')})")
    invariants = [c for c in (concepts or []) if c.get("status") == "stable" and c.get("type", "").lower() in ("invariant", "riskarea", "risk area")]
    # open high findings guard their whole span (line..end_line) on their side, padded by GAP
    high: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for f in pr.get("findings", []):
        if f.get("severity") == "high" and f.get("status", "open") == "open" and f.get("path") and f.get("line"):
            side = "old" if str(f.get("side", "")).upper() == "LEFT" else "new"
            end = f.get("end_line") or f["line"]
            high.setdefault((f["path"], side), []).append((min(f["line"], end) - GAP, max(f["line"], end) + GAP))
    # any open finding: an override may not move its own lines off the reading list
    flagged: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for f in pr.get("findings", []):
        if f.get("status", "open") == "open" and f.get("path") and f.get("line"):
            side = "old" if str(f.get("side", "")).upper() == "LEFT" else "new"
            end = f.get("end_line") or f["line"]
            flagged.setdefault((f["path"], side), []).append((min(f["line"], end), max(f["line"], end)))
    held = set()   # overrides refused somewhere, reported once
    # reviewer preferences from memory: e.g. promote 'tests, additive' to review for this reviewer
    promote = {r.get("reason", "").replace("-", " "): r.get("tier") for r in (rules or []) if r.get("action") == "attention"}

    per_line = []   # (path, side, n, tier, reason, evidence)
    for f in pr.get("files", []):
        path = f["path"]
        tier0, reason0, ev0 = _file_default(f, pr, additive_tests)
        boiler = _boiler_runs(f) if reason0 == "code" else set()
        if promote.get(reason0) in TIERS:
            tier0, ev0 = promote[reason0], ev0 + " · your preference"
        weak, weak_ev = _weakened(f) if f.get("role") == "test" else (0, "")
        guarded_inv = next((c for c in invariants if any(glob_match(path, g) for g in c.get("paths") or [])), None)
        for h in f.get("hunks", []):
            plain = lambda l: not (len(l) > 4 and (l[4].get("move") or l[4].get("ws")))
            added = sum(1 for l in h["lines"] if l[0] == "+" and plain(l))
            removed = sum(1 for l in h["lines"] if l[0] == "-" and plain(l))
            # the hunk rewrites these lines: the new side is what to read; a removal with little added back stays on Read
            rewrite = reason0 == "code" and removed and added >= REWRITE_SHARE * removed
            new_text = [l[3].strip() for l in h["lines"] if l[0] == "+" and plain(l)] if rewrite else []
            for l in h["lines"]:
                if l[0] not in "+-":
                    continue
                m = l[4] if len(l) > 4 else {}
                side, n = ("new", l[2]) if l[0] == "+" else ("old", l[1])
                if m.get("move"):
                    where = m.get("to") or m.get("from") or {}
                    tier, reason, ev = "skip", "moved, unchanged", f"identical after normalization ({where.get('path', '').split('/')[-1]}:{where.get('line', '')})"
                elif m.get("ws"):
                    tier, reason, ev = "skip", "formatting only", "identical after normalization"
                elif (side, n) in boiler:
                    tier, reason, ev = "skip", "imports, comments, docstrings", "a run of changed lines with no code in it"
                elif side == "old" and rewrite and _has_new_version(l[3], new_text):
                    tier, reason, ev = "skip", "old side of a rewrite", "the new side has its rewritten version; read that"
                else:
                    tier, reason, ev = tier0, reason0, ev0
                o = _overrides_for(overrides, path, n, side)
                agent_deep = False
                if o and o.get("tier") in ("skim", "skip") and tier == "skip" and (m.get("move") or m.get("ws")):
                    o = None   # already skipped as a move or formatting; an override can't make it louder
                if o and o.get("tier") in ("skim", "skip") and any(x <= n <= y for x, y in flagged.get((path, side), [])):
                    held.add(f"{path}:{n}")
                    o = None   # an open finding sits on this line
                if o and o.get("tier") in TIERS:
                    tier, reason, ev = o["tier"], o.get("reason") or reason, "your agent's call"
                    if tier == "deep":   # deep is earned within the budget; the agent's call weighs heavily
                        tier, agent_deep = "review", True
                # guards: these never leave the reading list
                if weak and not m.get("move"):   # most specific reason for a test file, even if already on the list
                    tier, reason, ev = "review", "test weakened", weak_ev
                elif tier != "review":
                    if any(a <= n <= b for a, b in high.get((path, side), [])):
                        tier, reason, ev = "review", "open high finding", "a Qodo, agent or scanner finding"
                    elif guarded_inv:
                        tier, reason, ev = "review", "under a confirmed invariant", guarded_inv.get("title", "")
                per_line.append((path, side, n, tier, reason, ev, agent_deep))
    if held:
        warn.append(f"{pr['key']} attention: overrides left {len(held)} line(s) on Read because an open finding sits on them "
                    f"({', '.join(sorted(held)[:4])}{' …' if len(held) > 4 else ''})")
    # high findings pull their surrounding range in even when the line itself is context
    ranges = _ranges(per_line)
    blocks = _blocks(pr, ranges)
    _choose_deep(pr, blocks, ranges, anchors or [], len(per_line), warn)
    for i, r in enumerate(ranges):
        r["id"] = f"r{i + 1}"
        r.pop("_ns", None)
    summary = {t: sum(r["lines"] for r in ranges if r["tier"] == t) for t in TIERS}
    summary["total"] = sum(summary.values())
    deep = [b["id"] for b in sorted((b for b in blocks if b["tier"] == "deep"), key=lambda b: -b["score"])]
    return {"summary": summary, "ranges": ranges, "blocks": blocks,
            "must_read": deep + [i for i in _order(pr, blocks) if i not in deep]}, warn


# What makes a block worth a deep read, strongest first. Points per line hit, plus the reason shown.
DEEP_SIGNALS = [
    ("open high finding", 100), ("test weakened", 80), ("under a confirmed invariant", 70),
    ("deep (agent)", 65), ("the story points here", 60), ("other work changes these lines", 55), ("build, dependency or access config", 50),
    ("open finding", 40), ("tests, CI failing", 35), ("tests changed", 20),
]


def _choose_deep(pr: dict, blocks: list[dict], ranges: list[dict], anchors: list[dict], total: int, warn: list[str]):
    """Mark the highest-risk reading blocks as deep read, within DEEP_SHARE of all changed lines."""
    weight = dict(DEEP_SIGNALS)
    fs = [{**f, "side": "old" if str(f.get("side", "")).upper() == "LEFT" else "new"}
          for f in pr.get("findings", []) if f.get("status", "open") == "open" and f.get("path") and f.get("line")]
    inside = lambda r, b: sum(1 for n in r.get("_ns") or range(r["from"], r["to"] + 1) if b["from"] <= n <= b["to"])
    for b in blocks:
        hits: dict[str, int] = {}
        for r in ranges:   # a range cut at a layer boundary lends each block the lines it holds
            n = inside(r, b) if r["path"] == b["path"] and r["side"] == b["side"] and r["tier"] == "review" else 0
            if n:
                key = "deep (agent)" if r.get("deep") else r["reason"]
                if key in weight:
                    hits[key] = hits.get(key, 0) + n
        for f in fs:   # findings count directly, whatever reason the lines already carry
            if f["path"] == b["path"] and f["side"] == b["side"] and b["from"] - GAP <= f["line"] <= b["to"] + GAP:
                k = "open high finding" if f.get("severity") == "high" else "open finding"
                hits[k] = hits.get(k, 0) + 1
        for a in anchors:
            if a.get("path") == b["path"] and a.get("side", "new") == b["side"] and a.get("from", 0) <= b["to"] and b["from"] <= a.get("to", a.get("from", 0)):
                hits["the story points here"] = hits.get("the story points here", 0) + 1
        for a in pr.get("overlap_spans") or []:   # lines another open, merged or in-review change touches too
            if a.get("path") == b["path"] and b["side"] == a.get("side", "new") and a.get("from", 0) <= b["to"] and b["from"] <= a.get("to", 0):
                hits["other work changes these lines"] = hits.get("other work changes these lines", 0) + 1
        b["score"] = sum(weight[k] * min(n, 10) for k, n in hits.items())
        b["why"] = [k for k, _ in sorted(hits.items(), key=lambda kv: -weight[kv[0]])]
    budget = max(DEEP_MIN_LINES, int(total * DEEP_SHARE))   # small PRs still get one real deep block
    used = 0
    new_blocks = []
    focus_lines = {}
    for b in blocks:   # where inside a block the signal sits: findings, anchors, and small signal ranges
        pts = [f["line"] for f in fs if f["path"] == b["path"] and f["side"] == b["side"] and b["from"] - GAP <= f["line"] <= b["to"] + GAP]
        pts += [x for a in anchors if a.get("path") == b["path"] if a.get("side", "new") == b["side"] for x in (a.get("from"), a.get("to", a.get("from")))
                if x and b["from"] <= x <= b["to"]]
        pts += [x for r in ranges if r["path"] == b["path"] and r["side"] == b["side"] and r["tier"] == "review"
                and inside(r, b) and (r.get("deep") or r["reason"] in weight)
                and r["lines"] <= budget for x in (max(r["from"], b["from"]), min(r["to"], b["to"]))]
        focus_lines[b["id"]] = sorted(set(pts))
    for b in sorted((b for b in blocks if b["why"] and weight[b["why"][0]] >= DEEP_MIN_SIGNAL), key=lambda b: (-b["score"], b["lines"])):
        room = budget - used
        if room < min(DEEP_MIN_LINES, b["lines"]):
            break
        lo, hi = b["from"], b["to"]
        if b["lines"] > room:   # too big to read closely: zoom into the densest signal window that fits
            pts = focus_lines.get(b["id"]) or [b["from"]]
            fits = lambda x: [y for y in pts if x <= y and y - x + 2 * GAP < room] or [x]
            start = max(pts, key=lambda x: (len(fits(x)), -x))   # the window holding the most signal, earliest first
            lo = max(b["from"], start - GAP)
            hi = min(b["to"], lo + room - 1, fits(start)[-1] + GAP)
        n = _split(ranges, b["path"], b["side"], lo, hi)
        if n <= 0:
            continue
        used += n
        if (lo, hi) == (b["from"], b["to"]):
            b["tier"] = "deep"
        else:   # a focused deep block inside a larger read block
            new_blocks.append({**b, "id": f"{b['id']}d", "from": lo, "to": hi, "lines": n, "tier": "deep", "zoom_of": b["id"]})
            b["lines"] -= n
    blocks.extend(new_blocks)


def _split(ranges: list[dict], path: str, side: str, lo: int, hi: int) -> int:
    """Move the review lines of path/side inside lo..hi to their own deep ranges; return how many lines moved."""
    moved = 0
    for i in range(len(ranges) - 1, -1, -1):
        r = ranges[i]
        if r["path"] != path or r["side"] != side or r["tier"] != "review" or r["to"] < lo or r["from"] > hi:
            continue
        parts = [[n for n in r["_ns"] if n < lo], [n for n in r["_ns"] if lo <= n <= hi], [n for n in r["_ns"] if n > hi]]
        pieces = [{**r, "from": ns[0], "to": ns[-1], "lines": len(ns), "_ns": ns, **({"tier": "deep"} if k == 1 else {})}
                  for k, ns in enumerate(parts) if ns]
        moved += len(parts[1])
        ranges[i:i + 1] = pieces
    return moved


BLOCK_GAP = 25   # unchanged lines between two edits that still read as one sitting


def _blocks(pr: dict, ranges: list[dict]) -> list[dict]:
    """Review ranges merged into reading blocks: same file and side, same layer, edits close together."""
    out: list[dict] = []
    for r, li in sorted(_by_layer(pr, ranges), key=lambda x: (x[0]["path"], x[0]["side"], x[0]["from"])):
        last = out[-1] if out else None
        if (last and last["path"] == r["path"] and last["side"] == r["side"] and last["layer"] == li
                and r["from"] - last["to"] <= BLOCK_GAP):
            last["to"] = max(last["to"], r["to"])
            last["lines"] += r["lines"]
            if r["reason"] not in last["reasons"]:
                last["reasons"].append(r["reason"])
        else:
            out.append({"path": r["path"], "side": r["side"], "from": r["from"], "to": r["to"], "lines": r["lines"],
                        "reasons": [r["reason"]], "layer": li, "tier": "review", "reason": r["reason"]})
    for i, b in enumerate(out):
        b["id"] = f"b{i + 1}"
        b["reason"] = next((x for x in b["reasons"] if x != "code"), "code")   # the most specific reason
    return out


def _by_layer(pr: dict, ranges: list[dict]):
    """(span, layer) for each review range, cut where its lines change layer, so a block (and the walkthrough's
    unit) never runs across a layer boundary: a long new file spread over three layers reads as three units."""
    spans = {}
    for li, ly in enumerate(pr.get("layers") or []):
        for lr in ly.get("ranges", []):
            spans.setdefault((lr["path"], lr.get("side", "new")), []).append((lr["from"], lr["to"], li))
    for r in ranges:
        if r["tier"] not in ("review", "deep"):
            continue
        mine = spans.get((r["path"], r["side"]))
        if not mine:
            yield r, None
            continue
        ns = list(r.get("_ns") or range(r["from"], r["to"] + 1))
        lis = [next((li for a, b, li in mine if a <= n <= b), None) for n in ns]
        for i in range(1, len(lis)):   # a line in no layer stays with the layer before it, else the one after
            lis[i] = lis[i] if lis[i] is not None else lis[i - 1]
        for i in range(len(lis) - 2, -1, -1):
            lis[i] = lis[i] if lis[i] is not None else lis[i + 1]
        if all(li is None for li in lis):
            yield r, layer_index(pr, r)
            continue
        start = 0
        for i in range(1, len(ns) + 1):
            if i == len(ns) or lis[i] != lis[start]:
                part = ns[start:i]
                yield {**r, "from": part[0], "to": part[-1], "lines": len(part)}, lis[start]
                start = i


def _ranges(per_line: list[tuple]) -> list[dict]:
    out: list[dict] = []
    for path, side, n, tier, reason, ev, agent_deep in sorted(per_line, key=lambda x: (x[0], x[1], x[2])):
        last = out[-1] if out else None
        gap = GAP if tier == "review" else 0
        if (last and last["path"] == path and last["side"] == side and last["tier"] == tier and last["reason"] == reason
                and n - last["to"] <= gap + 1):
            last["to"] = n
            last["lines"] += 1
            last["_ns"].append(n)
        else:
            out.append({"path": path, "side": side, "from": n, "to": n, "tier": tier, "reason": reason, "evidence": ev, "lines": 1, "_ns": [n],
                        **({"deep": True} if agent_deep else {})})
    return out


def _order(pr: dict, ranges: list[dict]) -> list[str]:
    """Must-read order: the layer walk first (foundations before consumers), then severity, then place."""
    layer_of = {}
    for li, ly in enumerate(pr.get("layers") or []):
        for lr in ly.get("ranges", []):
            layer_of.setdefault((lr["path"], lr.get("side", "new")), []).append((lr["from"], lr["to"], li))
    sev = {"high": 0, "medium": 1, "low": 2}
    fs = [f for f in pr.get("findings", []) if f.get("status", "open") == "open" and f.get("path")]

    def key(r):
        li = r["layer"] if r.get("layer") is not None else next((x[2] for x in layer_of.get((r["path"], r["side"]), []) if x[0] <= r["to"] and r["from"] <= x[1]), 99)
        s = min((sev.get(f["severity"], 3) for f in fs if f["path"] == r["path"] and f.get("line") and r["from"] <= f["line"] <= r["to"]), default=3)
        return (li, s, r["path"], r["from"])

    return [r["id"] for r in sorted(ranges, key=key)]


def layer_index(pr: dict, r: dict) -> int | None:
    for li, ly in enumerate(pr.get("layers") or []):
        for lr in ly.get("ranges", []):
            if lr["path"] == r["path"] and lr.get("side", "new") == r["side"] and lr["from"] <= r["to"] and r["from"] <= lr["to"]:
                return li
    return None


def plan(pr: dict) -> dict:
    """The review plan as plain data (CLI, GitHub summary, other tools)."""
    att = pr.get("attention") or {"summary": {}, "ranges": [], "must_read": []}
    by_id = {r["id"]: r for r in att.get("blocks") or att["ranges"]}
    names = {i: ly.get("title") for i, ly in enumerate(pr.get("layers") or [])}
    must = []
    for rid in att["must_read"]:
        r = by_id[rid]
        li = r.get("layer") if "layer" in r else layer_index(pr, r)
        must.append({"path": r["path"], "side": r["side"], "from": r["from"], "to": r["to"], "lines": r["lines"],
                     "tier": r.get("tier", "review"), "reason": r["reason"], "why_deep": r.get("why") or [],
                     "layer": names.get(li) if li is not None else None})
    rest: dict[str, dict] = {}
    for r in att["ranges"]:
        if r["tier"] in ("review", "deep"):
            continue
        g = rest.setdefault(f"{r['tier']}: {r['reason']}", {"tier": r["tier"], "reason": r["reason"], "lines": 0,
                                                            "evidence": r["evidence"], "files": set()})
        g["lines"] += r["lines"]
        g["files"].add(r["path"])
    groups = sorted(({**g, "files": sorted(g["files"])} for g in rest.values()), key=lambda g: (g["tier"] != "skim", -g["lines"]))
    out = {"pr": pr["key"], "summary": att["summary"], "must_read": must, "safe_to_skip": groups}
    from .product import enabled, project_pr
    if enabled(pr):
        complete = project_pr(pr)['product_evidence']['patches_complete']
        out['coverage'] = {'complete': complete, 'scope': 'complete' if complete else 'observed_subset'}
    return out


def plan_markdown(pr: dict) -> str:
    """Compact plan for the GitHub review body, collapsed so it never crowds the reviewer's comments."""
    p = plan(pr)
    s = p["summary"]
    if not s.get("total"):
        return ""
    deep, read = s.get("deep", 0), s.get("review", 0)
    partial = (p.get("coverage") or {}).get("complete") is False
    scope = "observed changed lines" if partial else "changed lines"
    lines = [f"<details><summary>Review plan: deep-read {deep}, read {read} of {s['total']} {scope} "
             f"({round(100 * (deep + read) / s['total'])}%)</summary>", ""]
    if partial:
        lines += ["Coverage incomplete: this plan covers only the observed patch subset; percentages describe that subset.", ""]
    lines += [f"- {'Deep-read' if m['tier'] == 'deep' else 'Read'} `{m['path']}` {m['from']}–{m['to']}"
              + (f" ({', '.join(m['why_deep']) if m['tier'] == 'deep' else m['reason']})" if m["tier"] == "deep" or m["reason"] != "code" else "")
              for m in p["must_read"][:15]]
    if len(p["must_read"]) > 15:
        lines.append(f"- … {len(p['must_read']) - 15} more ranges")
    for g in p["safe_to_skip"]:
        lines.append(f"- {g['tier'].title()}: {g['lines']} lines, {g['reason']} ({g['evidence']})")
    lines += ["", "</details>"]
    return "\n".join(lines)

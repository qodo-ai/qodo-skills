"""Semantic diff: tell moves and formatting apart from real edits, without a model.

Runs on parsed hunks (collect.parse_diff) for one PR and annotates lines in place. A hunk line is
[kind, old, new, text]; a fifth element, a dict, carries what this module found:
  {"ws": True}                       a -/+ pair that differs only in whitespace (the - side is hidden)
  {"move": id, "to"/"from": {...}}   part of a block of >= MOVE_MIN_LINES lines moved within the PR
  {"spans": [[a, b], ...]}           character ranges that really changed inside an edited line
It also returns counts so the agent and the reviewer know how much of the diff is noise.
"""
from __future__ import annotations

import difflib
import re

MOVE_MIN_LINES = 3
MOVE_MIN_CHARS = 40
TOKEN = re.compile(r"\w+|\s+|[^\w\s]")


STRING = re.compile(r"""("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`[^`\n]*`)""")


def _interior(text: str) -> str:
    """Spacing around punctuation dropped and runs collapsed, but only outside string literals:
    spaces inside a string are data."""
    parts = STRING.split(text.strip())
    out = []
    for i, part in enumerate(parts):
        if i % 2:          # a string literal: keep as is
            out.append(part)
        else:
            part = re.sub(r"\s*([^\w\s])\s*", r"\1", part)
            out.append(re.sub(r"\s+", " ", part))
    return "".join(out).strip()


def _lead(text: str) -> str:
    return text[: len(text) - len(text.lstrip())]


def _norm(text: str) -> str:
    """Formatting-insensitive form for whitespace-only detection. Leading indentation is kept
    (it is behavior in Python and YAML) and string contents are kept."""
    return _lead(text) + _interior(text)


def _move_key(text: str) -> str:
    """For moves, indentation may shift as a whole block (checked separately); the rest is strict."""
    return _interior(text)


def _meta(line: list) -> dict:
    if len(line) < 5:
        line.append({})
    return line[4]


def _blocks(lines: list[list]) -> list[tuple[list[int], list[int]]]:
    """Consecutive runs of '-' then '+' lines inside a hunk (one edit block each)."""
    out, i = [], 0
    while i < len(lines):
        if lines[i][0] in "+-":
            dels, adds = [], []
            while i < len(lines) and lines[i][0] == "-":
                dels.append(i); i += 1
            while i < len(lines) and lines[i][0] == "+":
                adds.append(i); i += 1
            out.append((dels, adds))
        else:
            i += 1
    return out


def _spans(a: str, b: str) -> tuple[list, list] | None:
    """Changed character ranges in a and b, if the two lines are similar enough to compare."""
    ta, tb = TOKEN.findall(a), TOKEN.findall(b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    if sm.ratio() < 0.6:
        return None
    pa, pb = [0], [0]
    for t in ta:
        pa.append(pa[-1] + len(t))
    for t in tb:
        pb.append(pb[-1] + len(t))
    sa, sb = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        if i2 > i1 and "".join(ta[i1:i2]).strip():
            sa.append([pa[i1], pa[i2]])
        if j2 > j1 and "".join(tb[j1:j2]).strip():
            sb.append([pb[j1], pb[j2]])
    # highlight only real edits: if most of a line changed, the line color already says so
    changed_a, changed_b = sum(y - x for x, y in sa), sum(y - x for x, y in sb)
    if changed_a > 0.4 * len(a.strip() or "x") or changed_b > 0.4 * len(b.strip() or "x"):
        return None
    return sa, sb


ROLES = [   # first match wins: tests before migrations, config before docs
    ("generated", r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock|go\.sum)$|\.(min\.js|snap|pb\.go)$|(^|/)(dist|build|vendor|__generated__)/"),
    ("test", r"(^|/)(tests?|__tests__|spec|e2e)/|(^|/)test_[^/]+$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$"),
    ("migration", r"(^|/)(migrations?|alembic)/"),
    ("config", r"\.(ya?ml|toml|ini|cfg|json|tf|hcl)$|(^|/)(Dockerfile|Makefile)$|requirements[^/]*\.txt$"),
    ("docs", r"\.(md|mdx|rst|txt)$|(^|/)docs?/"),
]


def role(path: str) -> str:
    """What a changed file is for, so layers can keep tests and config with the code they cover."""
    return next((r for r, rx in ROLES if re.search(rx, path)), "source")


def annotate(files: list[dict]) -> dict:
    """Annotate every file's hunks in place; return {"moved", "whitespace", "meaningful", "files"}."""
    stats = {"moved": 0, "whitespace": 0, "meaningful": 0, "files": {}}
    # 1) whitespace-only pairs and token-level spans, inside each edit block
    for f in files:
        for h in f.get("hunks", []):
            lines = h["lines"]
            for dels, adds in _blocks(lines):
                for di, ai in zip(dels, adds):
                    a, b = lines[di][3], lines[ai][3]
                    if a != b and _norm(a) == _norm(b):
                        _meta(lines[di])["ws"] = True
                        _meta(lines[ai])["ws"] = True
                    elif a != b:
                        sp = _spans(a, b)
                        if sp and (sp[0] or sp[1]):
                            _meta(lines[di])["spans"], _meta(lines[ai])["spans"] = sp
    # 2) moved blocks across the whole PR: a run of deleted lines that reappears as added lines
    added: dict[str, list[tuple[int, int, int]]] = {}
    flat_add = []   # (file index, hunk index, line index)
    for fi, f in enumerate(files):
        for hi, h in enumerate(f.get("hunks", [])):
            for li, l in enumerate(h["lines"]):
                if l[0] == "+" and not (len(l) > 4 and l[4].get("ws")):
                    key = _move_key(l[3])
                    if key:
                        added.setdefault(key, []).append((fi, hi, li))
                    flat_add.append((fi, hi, li))
    used = set()
    move_id = 0
    for fi, f in enumerate(files):
        for hi, h in enumerate(f.get("hunks", [])):
            lines = h["lines"]
            li = 0
            while li < len(lines):
                l = lines[li]
                key = _move_key(l[3]) if l[0] == "-" else ""
                best = None
                for cand in added.get(key, []) if key else []:
                    if cand in used:
                        continue
                    n, chars = 0, 0
                    while True:
                        dl = li + n
                        cf, ch, cl = cand[0], cand[1], cand[2] + n
                        alines = files[cf]["hunks"][ch]["lines"]
                        if dl >= len(lines) or cl >= len(alines):
                            break
                        d, a = lines[dl], alines[cl]
                        if (d[0] != "-" or a[0] != "+" or (cf, ch, cl) in used or _move_key(d[3]) != _move_key(a[3])
                                or not _move_key(d[3]) or (len(d) > 4 and d[4].get("ws"))):
                            break
                        shift = len(_lead(a[3])) - len(_lead(d[3]))
                        if n == 0:
                            first_shift = shift
                        elif shift != first_shift:   # re-indented unevenly: nesting changed, not a move
                            break
                        chars += len(_move_key(d[3])); n += 1
                    if n >= MOVE_MIN_LINES and chars >= MOVE_MIN_CHARS and (best is None or n > best[0]):
                        best = (n, cand)
                if best:
                    n, (cf, ch, cl) = best
                    move_id += 1
                    to_path, from_path = files[cf]["path"], f["path"]
                    alines = files[cf]["hunks"][ch]["lines"]
                    for k in range(n):
                        _meta(lines[li + k]).update(move=move_id, to={"path": to_path, "line": alines[cl][2]}, run=n, first=k == 0)
                        _meta(alines[cl + k]).update(move=move_id, **{"from": {"path": from_path, "line": lines[li][1]}}, run=n, first=k == 0)
                        used.add((cf, ch, cl + k))
                    li += n
                    continue
                li += 1
    # 3) counts
    for f in files:
        c = {"moved": 0, "whitespace": 0, "meaningful": 0}
        for h in f.get("hunks", []):
            for l in h["lines"]:
                if l[0] not in "+-":
                    continue
                m = l[4] if len(l) > 4 else {}
                if m.get("move"):
                    c["moved"] += 1
                elif m.get("ws"):
                    c["whitespace"] += 1
                else:
                    c["meaningful"] += 1
        f["semantic"] = c
        f["role"] = role(f["path"])
        stats["files"][f["path"]] = c
        for k in ("moved", "whitespace", "meaningful"):
            stats[k] += c[k]
    return stats

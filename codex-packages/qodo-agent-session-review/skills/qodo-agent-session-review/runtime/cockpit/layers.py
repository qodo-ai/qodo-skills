"""Layers: the guided walk through one PR's code, in the order someone would explain it.

The skill writes `prs[key].layers` in enrich.json:
  [{id, title, summary, ranges: [{path, from, to, side?: new|old, note?}], depends_on?: [ids],
    visual?: {mermaid} | {shape: {form, text, diff?}}}]
A layer keeps a contract, its implementation and its tests together. This module checks the
shape, that every range lands on real diff lines, and how much of the meaningful diff the layers
cover, so nothing is skipped without the reviewer seeing it ("Not in any layer").
"""
from __future__ import annotations

import re

TITLE_WORDS, SUMMARY_WORDS, NOTE_WORDS = 8, 60, 30


def _words(s: str | None) -> int:
    return len(re.findall(r"\S+", s or ""))


def _changed(pr: dict) -> tuple[dict[tuple[str, str], set[int]], dict[tuple[str, int], int]]:
    """(path, side) -> meaningful changed line numbers (moves and whitespace excluded), plus each
    deleted line's anchor: the new-file line where it sat, so a new-side range covers it too."""
    out: dict[tuple[str, str], set[int]] = {}
    anchor: dict[tuple[str, int], int] = {}
    for f in pr.get("files", []):
        for h in f.get("hunks", []):
            last_new = None
            pending = []
            for l in h["lines"]:
                if l[2] is not None:
                    last_new = l[2]
                    for o in pending:
                        anchor[(f["path"], o)] = l[2]
                    pending = []
                m = l[4] if len(l) > 4 else {}
                if l[0] not in "+-" or m.get("move") or m.get("ws"):
                    continue
                side, n = ("new", l[2]) if l[0] == "+" else ("old", l[1])
                out.setdefault((f["path"], side), set()).add(n)
                if side == "old":
                    if last_new is not None:
                        anchor[(f["path"], n)] = last_new
                    pending.append(n)
    return out, anchor


def _runs(nums: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def normalize(layers: list[dict], pr: dict) -> tuple[list[dict], dict, list[str]]:
    """Return (clean layers, coverage, warnings)."""
    tag = f"{pr['key']} layers"
    warn: list[str] = []
    files = {f["path"] for f in pr.get("files", [])}
    changed, anchor = _changed(pr)
    seen_ids: list[str] = []
    covered: dict[tuple[str, str], set[int]] = {}
    out = []
    for i, ly in enumerate(layers or []):
        ly = dict(ly)
        ly.setdefault("id", f"L{i + 1}")
        t = f"{tag} {ly['id']}"
        if ly["id"] in seen_ids:
            warn.append(f"{t}: duplicate id")
        if _words(ly.get("title")) > TITLE_WORDS:
            warn.append(f"{t}: title has {_words(ly.get('title'))} words (aim for <= {TITLE_WORDS})")
        if not ly.get("summary"):
            warn.append(f"{t}: missing summary (what this layer adds and why it comes here)")
        elif _words(ly.get("summary")) > SUMMARY_WORDS:
            warn.append(f"{t}: summary has {_words(ly['summary'])} words (aim for <= {SUMMARY_WORDS})")
        for dep in ly.get("depends_on") or []:
            if dep not in seen_ids:
                warn.append(f"{t}: depends_on {dep!r} is not an earlier layer; order layers so foundations come first")
        rs = []
        for r in ly.get("ranges") or []:
            r = dict(r)
            side = r.setdefault("side", "new")
            if r.get("path") not in files:
                warn.append(f"{t}: range path {r.get('path')} is not in the changed files")
                continue
            if not (isinstance(r.get("from"), int) and isinstance(r.get("to"), int) and r["to"] >= r["from"]):
                warn.append(f"{t}: range on {r['path']} needs integer from <= to")
                continue
            hits = {n for n in changed.get((r["path"], side), set()) if r["from"] <= n <= r["to"]}
            if not hits:
                warn.append(f"{t}: {r['path']} {side} lines {r['from']}-{r['to']} contain no meaningful change")
            covered.setdefault((r["path"], side), set()).update(range(r["from"], r["to"] + 1))
            if _words(r.get("note")) > NOTE_WORDS:
                warn.append(f"{t}: range note has {_words(r.get('note'))} words (aim for <= {NOTE_WORDS})")
            rs.append(r)
        if not rs:
            warn.append(f"{t}: no valid ranges")
        ly["ranges"] = rs
        seen_ids.append(ly["id"])
        out.append(ly)
    total = sum(len(v) for v in changed.values())
    uncovered = []
    for (path, side), nums in sorted(changed.items()):
        cov = covered.get((path, side), set())
        new_cov = covered.get((path, "new"), set())
        rest = sorted(n for n in nums if n not in cov and not (side == "old" and anchor.get((path, n)) in new_cov))
        if rest:
            uncovered.append({"path": path, "side": side, "runs": _runs(rest)})
    n_unc = sum(r[1] - r[0] + 1 for u in uncovered for r in u["runs"])
    coverage = {"total": total, "covered": total - n_unc, "uncovered": uncovered}
    if out and n_unc:
        short = ", ".join(f"{u['path'].split('/')[-1]} ({sum(r[1] - r[0] + 1 for r in u['runs'])})" for u in uncovered[:6])
        warn.append(f"{tag}: {n_unc} of {total} meaningful changed lines are in no layer: {short}"
                    f"{' ...' if len(uncovered) > 6 else ''}. Add them to a layer, or accept that they show under 'Not in any layer'.")
    if out and not 2 <= len(out) <= 8 and total > 80:
        warn.append(f"{tag}: {len(out)} layers; a walk reads best in 2-8")
    return out, coverage, warn

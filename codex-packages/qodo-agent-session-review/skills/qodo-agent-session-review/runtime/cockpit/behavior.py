"""The behavior diff: each changed file as + / − / ~ lines of behaviors, interfaces and promises.

The skill writes it into enrich.json as `behavior` (format in skill/references/behavior.md). Every
−, + and ~ line must cite lines the PR changed; `check` enforces that and measures how much of the
read-tier code the sketch cites. `resolve` attaches the cited code, and per file the changed code
the sketch doesn't describe, for the `behavior` style to show under each line.
"""
from __future__ import annotations

KS = {" ", "-", "+", "~"}
KINDS = {"behavior", "interface", "config", "data", "proof"}
MAX_EV = 40     # code lines kept per cited range
MAX_GAPS = 6    # uncited runs shown per file


def changed(f: dict, side: str) -> set[int]:
    """Line numbers the PR changed in file f, on one side."""
    mark, col = ("+", 2) if side == "new" else ("-", 1)
    return {ln[col] for h in f.get("hunks", []) for ln in h["lines"] if ln[0] == mark}


def window(f: dict, side: str, lo: int, hi: int) -> list[list]:
    """Diff lines in [lo, hi] on one side, plus the other side's changed lines between them."""
    out, inside = [], False
    for h in f.get("hunks", []):
        for kind, old, new, text, *_ in h["lines"]:
            n = new if side == "new" else old
            if n is not None:
                inside = lo <= n <= hi
            if inside and (n is not None or kind in "+-"):
                out.append([kind, old, new, text])
    return out


def _runs(nums: list[int], gap: int = 2) -> list[list[int]]:
    runs: list[list[int]] = []
    for n in nums:
        if runs and n - runs[-1][1] <= gap:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return runs


def check(behavior: dict, data: dict, *, resolve: bool = False) -> tuple[dict, list[str], list[str]]:
    """Validate a behavior diff against the session. Returns (behavior, errors, warnings); with
    resolve=True, cited ranges carry their code and `coverage` lists per-file gaps."""
    import copy
    bh = copy.deepcopy(behavior or {})
    prs = {p["key"]: p for p in data.get("prs", [])}
    files = {(p["key"], f["path"]): f for p in data.get("prs", []) for f in p.get("files", [])}
    fids = {f["id"] for p in data.get("prs", []) for f in p.get("findings", [])}
    links = {l.get("id") for l in bh.get("links") or []}
    caps = {c.get("id") for c in bh.get("capabilities") or []}
    errs: list[str] = []
    warns: list[str] = []
    cited: dict[tuple, set] = {}

    def ev_of(where, pr, path, evs, need):
        if need and not evs:
            errs.append(f"behavior {where}: a -, + or ~ line needs ev (the changed lines that make it true)")
        out = []
        for e in evs or []:
            p = e.get("path", path)
            f = files.get((pr, p))
            side = e.get("side", "new")
            if side not in ("new", "old"):
                errs.append(f"behavior {where}: ev side must be new or old, not {side!r}")
                continue
            if not f:
                errs.append(f"behavior {where}: ev path {p} is not changed in {pr}")
                continue
            try:
                lo, hi = int(e["from"]), int(e.get("to", e["from"]))
            except (KeyError, TypeError, ValueError):
                errs.append(f"behavior {where}: ev needs integer from/to")
                continue
            hit = {n for n in changed(f, side) if lo <= n <= hi}
            if not hit:
                errs.append(f"behavior {where}: ev {p}:{side} {lo}-{hi} touches no changed line")
                continue
            cited.setdefault((pr, p), set()).update((side, n) for n in hit)
            r = {"path": p, "side": side, "from": lo, "to": hi}
            if resolve:
                w = window(f, side, lo, hi)
                r.update(lines=w[:MAX_EV], cut=max(0, len(w) - MAX_EV))
            out.append(r)
        return out

    used_links: dict[str, set] = {}
    for i, fe in enumerate(bh.get("files") or []):
        pr, path = fe.get("pr"), fe.get("path")
        if pr not in prs:
            errs.append(f"behavior files[{i}]: unknown pr {pr}")
            continue
        if (pr, path) not in files:
            errs.append(f"behavior files[{i}]: {path} is not changed in {pr}")
            continue
        if not fe.get("headline"):
            warns.append(f"behavior {path}: no headline")
        for j, h in enumerate(fe.get("hunks") or []):
            if h.get("cap") and h["cap"] not in caps:
                errs.append(f"behavior {path} hunk {j}: unknown capability {h['cap']}")
            for k, ln in enumerate(h.get("lines") or []):
                where = f"{path} hunk {j} line {k}"
                if ln.get("k") not in KS:
                    errs.append(f"behavior {where}: k must be ' ', '-', '+' or '~'")
                if ln.get("kind", "behavior") not in KINDS:
                    errs.append(f"behavior {where}: kind must be one of {', '.join(sorted(KINDS))}")
                if len(ln.get("text") or "") > 200:
                    warns.append(f"behavior {where}: text is over 200 characters")
                if ln.get("finding") and ln["finding"] not in fids:
                    errs.append(f"behavior {where}: unknown finding {ln['finding']}")
                if ln.get("link"):
                    if ln["link"] not in links:
                        errs.append(f"behavior {where}: link {ln['link']} is not in links")
                    used_links.setdefault(ln["link"], set()).add((pr, path))
                ln["ev"] = ev_of(where, pr, path, ln.get("ev"), ln.get("k") != " ")
    for lid, places in used_links.items():
        if len(places) < 2:
            warns.append(f"behavior link {lid} is used in only one file")
    for i, kp in enumerate(bh.get("kept") or []):
        if kp.get("pr") not in prs:
            errs.append(f"behavior kept[{i}]: unknown pr {kp.get('pr')}")
            kp["ev"] = []
            continue
        kp["ev"] = ev_of(f"kept[{i}]", kp.get("pr"), kp.get("path"), kp.get("ev"), True)

    # coverage: changed lines in read-tier source files that some line cites
    tiers: dict[tuple, set] = {}
    for p in data.get("prs", []):
        for r in (p.get("attention") or {}).get("ranges", []):
            tiers.setdefault((p["key"], r["path"]), set()).add(r.get("tier"))
    cov, tot, hit, bare = [], 0, 0, []
    for (pr, path), f in files.items():
        ch = {("new", n) for n in changed(f, "new")} | {("old", n) for n in changed(f, "old")}
        c = cited.get((pr, path), set()) & ch
        important = bool(tiers.get((pr, path), set()) & {"deep", "review"}) and f.get("role") not in ("test", "generated", "docs")
        if important:
            tot += len(ch); hit += len(c)
            if not c and bh.get("files"):
                bare.append(f"{path} ({len(ch)})")
        gaps = []
        if resolve and important:
            for side in ("new", "old"):
                for lo, hi in _runs(sorted(n for s, n in ch - c if s == side)):
                    if len(gaps) >= MAX_GAPS:
                        break
                    w = window(f, side, lo, hi)
                    gaps.append({"side": side, "from": lo, "to": hi, "lines": w[:24], "cut": max(0, len(w) - 24)})
        cov.append({"pr": pr, "path": path, "changed": len(ch), "cited": len(c), "uncited": len(ch - c),
                    "important": important, "gaps": gaps})
    if bare:
        warns.append(f"behavior: {len(bare)} read-tier file{'s' if len(bare) != 1 else ''} with no behavior line "
                     f"(changed lines): {', '.join(bare[:6])}{' …' if len(bare) > 6 else ''}")
    bh["coverage"] = {"important_lines": tot, "cited": hit, "files": cov}
    return bh, errs, warns

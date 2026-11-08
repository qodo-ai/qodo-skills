"""Impact: what a change reaches beyond its lines, and the evidence it was checked. Evidence comes from the
diff and the PR's checks; impact rows are the skill's research (enrich.json `impact`), else derived from the diff."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from .attention import weakening

CODE = re.compile(r"\.(py|js|mjs|cjs|ts|tsx|jsx|go|rb|java|kt|rs|cs|php|swift|scala|sql|html|vue|svelte)$")
MARKUP = re.compile(r"\.(html|vue|svelte)$")   # source a test renders, not calls: never flagged as untested
RISKS = ("high", "medium", "low")
LIST_FIELDS = ("affects", "workflows", "evidence", "gaps", "paths")
MAX_LOST, MAX_NAMES = 12, 8   # per weakened test: the lines shown; per untested file: the names it defines


def _added(f: dict) -> list[str]:
    return [l[3] for h in f.get("hunks", []) for l in h.get("lines", []) if l[0] == "+"]


def _stem(path: str) -> str:
    return PurePosixPath(path).name.split(".")[0]


DEF = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|class|func|fn|const|let|var)\s+([A-Za-z_]\w{2,})")


def _names(f: dict) -> set[str]:
    """What a source file's diff defines or redefines: the names a test would call."""
    return {m.group(1) for line in _added(f) if (m := DEF.match(line))}


def _test_text(f: dict) -> str:   # the test's code in the diff (added and context lines), never its path
    return "\n".join(l[3] for h in f.get("hunks", []) for l in h.get("lines", []) if l[0] in "+ ")


def _named_for(test_path: str, stem: str) -> bool:
    """A test file named for the module by convention: test_view.py, view_test.go, view.test.ts, ViewTest.java."""
    name = PurePosixPath(test_path).name
    return bool(re.match(rf"(?:test_{re.escape(stem)}|{re.escape(stem)}_test|{re.escape(stem)}\.(?:test|spec)|{re.escape(stem)}Tests?|Test{re.escape(stem)})\.", name, re.I))


def evidence(pr: dict) -> dict:
    """What the diff shows about how the change was checked."""
    files = pr.get("files", [])
    tests = [f for f in files if f.get("role") == "test"]
    said = "\n".join(_test_text(t) for t in tests)
    word = lambda w: re.search(rf"(?<![A-Za-z0-9_]){re.escape(w)}(?![A-Za-z0-9_])", said)
    ranges = (pr.get("attention") or {}).get("ranges", [])
    weakened = sorted({r["path"] for r in ranges if r.get("reason") == "test weakened"})
    by_path = {f["path"]: f for f in files}
    weak_detail = []   # what each weakened test lost, line by line, for the Quality tab
    for path in weakened:
        w = weakening(by_path[path]) if path in by_path else {"removed": [], "disabled": [], "asserts_added": 0, "net": 0}
        weak_detail.append({"path": path, **{k: w[k][:MAX_LOST] for k in ("removed", "disabled")}, "asserts_added": w["asserts_added"], "net": w["net"],
                            "more": max(0, len(w["removed"]) - MAX_LOST) + max(0, len(w["disabled"]) - MAX_LOST)})
    read = {}   # changed lines a human reads (deep or read), per file
    for r in ranges:
        if r.get("tier") in ("deep", "review"):
            read[r["path"]] = read.get(r["path"], 0) + r.get("lines", 0)
    untested = []
    for f in files:
        p = f["path"]
        if f.get("role", "source") != "source" or not CODE.search(p) or MARKUP.search(p) or not read.get(p):
            continue
        # tested here: a changed test named for the module, one whose code names it, or one calling something this diff defines
        stem = _stem(p)
        if not (any(_named_for(t["path"], stem) for t in tests) or (len(stem) >= 3 and stem not in ("__init__", "index") and word(stem))
                or any(word(n) for n in _names(f))):
            untested.append({"path": p, "lines": read[p], "names": sorted(_names(f))[:MAX_NAMES]})
    added = 0
    pat = re.compile(r"^\s*(?:async\s+)?def\s+test_|^\s*(?:it|test)(?:\.\w+)*\(|^\s*func\s+Test")
    for t in tests:
        added += sum(1 for line in _added(t) if pat.match(line))
    return {"tests_added": added, "weakened": weakened, "weakened_detail": weak_detail, "untested": untested}


# test-result checks (EnricoMi publish-unit-test-result, dorny/test-reporter, …) title their run with the counts:
# "1 fail, 2 skipped, 3 053 pass in 54m 35s", "All 7 040 tests pass in 1m 43s"
_N = r"(\d[\d,\s]*\d|\d)"   # thousands are grouped with any space (3 053 uses a narrow one) or a comma
_COUNT = {"failed": re.compile(_N + r"\s*(?:tests?\s+)?(?:fail|failed|failing|failures?|errors?|errored)\b", re.I),
          "skipped": re.compile(_N + r"\s*(?:tests?\s+)?(?:skipped|skip|ignored)\b", re.I),
          "passed": re.compile(_N + r"\s*(?:tests?\s+)?(?:pass|passed|passing)\b", re.I)}
_COV_NAME = re.compile(r"codecov|coveralls|sonar|coverage", re.I)
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _num(s: str) -> int:
    return int(re.sub(r"\D", "", s))


def test_results(runs: list[dict]) -> list[dict]:
    """Test counts from check runs whose title states them, the latest run per suite (a passing rerun replaces a failure)."""
    latest: dict[str, dict] = {}
    for r in runs:
        t = str((r.get("output") or {}).get("title") or "")
        got = {k: sum(_num(m.group(1)) for m in rx.finditer(t)) for k, rx in _COUNT.items()}   # "2 errors, 1 fail" is 3
        if not got["passed"] and not got["failed"]:
            continue
        name = r.get("name") or "tests"
        rec = {"name": name, **got, "title": t[:120], "url": r.get("html_url"), "conclusion": r.get("conclusion"), "_at": (r.get("completed_at") or "", r.get("id") or 0)}
        if name not in latest or rec["_at"] > latest[name]["_at"]:
            latest[name] = rec
    return [{k: v for k, v in r.items() if k != "_at"} for r in latest.values()]


def coverage(runs: list[dict], comments: list[dict]) -> list[dict]:
    """Coverage the PR reports: a coverage check's title, or a coverage bot's comment (patch and project %)."""
    out = []
    for r in runs:
        name, t = r.get("name") or "", str((r.get("output") or {}).get("title") or "")
        app = ((r.get("app") or {}).get("slug") or "")
        if (_COV_NAME.search(name) or _COV_NAME.search(app)) and _PCT.search(t):
            out.append({"name": name, "text": t[:120], "percent": float(_PCT.search(t).group(1)), "url": r.get("html_url")})
    for c in comments:
        who, body = str(c.get("author") or "").lower(), c.get("body") or ""
        if not re.search(r"codecov|coveralls|sonar", who):
            continue
        patch = re.search(r"patch coverage(?: is)?[^\d]{0,40}(\d+(?:\.\d+)?)\s*%", body, re.I)
        proj = re.search(r"project coverage(?: is)?[^\d]{0,40}(\d+(?:\.\d+)?)\s*%", body, re.I)
        if patch or proj:
            out.append({"name": who.split("[")[0], "text": " · ".join(x for x in (patch and f"patch {patch.group(1)}%", proj and f"project {proj.group(1)}%") if x),
                        "percent": float((patch or proj).group(1)), "url": c.get("url")})
    return out


# merge danger from the paths alone: what a revert may not undo (the skill confirms or corrects it per part)
ONEWAY = [(re.compile(r"(^|/)(migrations?|alembic|flyway|liquibase)/", re.I), "a migration"), (re.compile(r"\.sql$", re.I), "SQL"),
          (re.compile(r"(^|/)schemas?(/|\.)|\.prisma$|\.graphql$", re.I), "a schema"), (re.compile(r"openapi|swagger|\.proto$", re.I), "an API contract"),
          (re.compile(r"(^|/)(charts?|helm|terraform|k8s|deploy)/|\.tf$|\.tfvars$", re.I), "deploy config")]
# the first match wins: a spec file is a contract before a schema is a table, and front-end roots claim their .js/.ts before the backend does
DOMAINS = [("contract", "Contract", re.compile(r"openapi|swagger|\.proto$|\.graphql$", re.I)),
           ("db", "DB", re.compile(r"(^|/)(migrations?|alembic|flyway|liquibase)/|\.sql$|\.prisma$|(^|/)schemas?(/|\.)", re.I)),
           ("contract", "Contract", re.compile(r"(^|/)(api|routers?|routes|endpoints?|contracts?)(/|\.|_)", re.I)),
           ("config", "Config / flags", re.compile(r"\.(ya?ml|toml|ini|cfg|env|tf|tfvars)$|(^|/)(config|configs|settings|flags?|feature_flags?)(/|\.|_)|Dockerfile|(^|/)(charts?|helm|terraform|k8s|deploy)/|\.github/workflows/|(^|/)package(-lock)?\.json$|pyproject\.toml$|requirements[^/]*\.txt$", re.I)),
           ("frontend", "Frontend", re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|less|html)$|(^|/)(web|frontend|ui|client|app/components)/|(^|/)(app|components|pages|public|static|assets)/[^.]*\.(m?js|ts)$", re.I)),
           ("backend", "Backend", CODE)]
DOORS = ("one-way", "two-way")


def door_guess(pr: dict) -> dict:
    """One-way when the PR changes something a revert may not undo; from the file paths only."""
    hits = []
    for f in pr.get("files", []):
        if f.get("role") in ("test", "docs", "generated"):   # a fixture's .sql or a doc's example migration ships nothing
            continue
        for rx, what in ONEWAY:
            if rx.search(f["path"]) and what not in [h["what"] for h in hits]:
                hits.append({"what": what, "path": f["path"]})
    if hits:
        return {"verdict": "one-way", "why": "changes " + ", ".join(f"{h['what']} ({PurePosixPath(h['path']).name})" for h in hits), "source": "from the paths"}
    return {"verdict": "two-way", "why": "no migration, schema, API contract or deploy config among the changed files", "source": "from the paths"}


def domains(pr: dict) -> dict:
    """Changed files per domain (tests and docs left out): what changed where, at a glance."""
    out: dict[str, list[str]] = {}
    for f in pr.get("files", []):
        if f.get("role") in ("test", "docs", "generated"):
            continue
        key = next((k for k, _, rx in DOMAINS if rx.search(f["path"])), None)
        if key:
            out.setdefault(key, []).append(f["path"])
    return out


def _pr_key(k, prs: dict):
    """A step's PR as written: its key, or a bare number ("5279", 5279, "#5279") when one PR in the set has it."""
    if isinstance(k, str) and k in prs:
        return k
    n = str(k).lstrip("#") if isinstance(k, (int, str)) and not isinstance(k, bool) else ""
    hits = [key for key in prs if n.isdigit() and key.rsplit("#", 1)[-1] == n]
    return hits[0] if len(hits) == 1 else k


def normalize_deploy(steps, prs: dict) -> tuple[list[dict], list[str]]:
    warn, out = [], []
    for i, s in enumerate(steps if isinstance(steps, list) else []):
        if not isinstance(s, dict) or not str(s.get("step") or "").strip():
            warn.append(f"deploy step {i + 1}: needs a step"); continue
        ps = [_pr_key(k, prs) for k in (s.get("prs") if isinstance(s.get("prs"), list) else [])
              if isinstance(k, (str, int)) and not isinstance(k, bool)]
        bad = [k for k in ps if k not in prs] + [k for k in (s.get("prs") if isinstance(s.get("prs"), list) else [])
                                                  if not isinstance(k, (str, int)) or isinstance(k, bool)]
        if bad:
            warn.append(f"deploy step {i + 1}: unknown prs {bad}")
        out.append({"step": str(s["step"]).strip()[:200], "prs": [k for k in ps if k in prs], "why": str(s.get("why") or "").strip()[:240],
                    "verify": str(s.get("verify") or "").strip()[:240]})   # what to check before the next step
    if steps is not None and not isinstance(steps, list):
        warn.append("deploy: a list of {step, prs, why}")
    return out, warn


def normalize_door(d) -> tuple[dict | None, list[str]]:
    if not isinstance(d, dict) or d.get("verdict") not in DOORS:
        return None, (["door: {verdict: one-way|two-way, why}"] if d is not None else [])
    return {"verdict": d["verdict"], "why": str(d.get("why") or "").strip()[:240], "source": "review"}, []


def normalize(rows, prs: dict) -> tuple[list[dict], list[str]]:
    """The skill's impact rows as the page draws them, and what was wrong with them."""
    warn, out = [], []
    if not isinstance(rows, list):
        return [], ["impact: a list of rows {component, change, affects, workflows, risk, why, evidence, gaps, prs}"]
    for i, r in enumerate(rows):
        if not isinstance(r, dict) or not str(r.get("component") or "").strip():
            warn.append(f"impact row {i + 1}: needs a component")
            continue
        row = {"component": str(r["component"]).strip()[:80], "change": str(r.get("change") or "").strip()[:200],
               "door": r.get("door") if r.get("door") in DOORS else "", "undo": str(r.get("undo") or "").strip()[:200],
               "fails": str(r.get("fails") or "").strip()[:200], "notice": str(r.get("notice") or "").strip()[:200],
               "risk": r.get("risk") if r.get("risk") in RISKS else "medium", "why": str(r.get("why") or "").strip()[:240],
               "source": str(r.get("source") or "").strip()[:80]}
        if r.get("risk") not in RISKS:
            warn.append(f"impact row {i + 1} ({row['component']}): risk must be high, medium or low")
        for k in LIST_FIELDS:
            v = r.get(k) or []
            row[k] = [str(x).strip()[:160] for x in (v if isinstance(v, list) else [v]) if str(x).strip()][:8]
        prs_in = r.get("prs") or []
        if not isinstance(prs_in, list):
            warn.append(f"impact row {i + 1} ({row['component']}): prs must be a list of PR keys")
            prs_in = []
        row["prs"] = [k for k in prs_in if isinstance(k, str)]
        bad = [k for k in row["prs"] if k not in prs]
        if bad:
            warn.append(f"impact row {i + 1} ({row['component']}): unknown prs {bad}")
            row["prs"] = [k for k in row["prs"] if k in prs]
        if not row["affects"] and not row["workflows"]:
            warn.append(f"impact row {i + 1} ({row['component']}): say what it affects (affects or workflows)")
        if not row["evidence"] and not row["gaps"]:
            warn.append(f"impact row {i + 1} ({row['component']}): give the evidence, or the gap")
        if r.get("factors") is not None:   # Explainable Risk: this part as a failure scenario, its three factors with evidence
            from .risk import normalize_factors
            changed = {f["path"] for k in (row["prs"] or list(prs)) for f in prs[k].get("files", [])}
            repos = {k.split("#")[0] for k in prs} | {k.split("#")[0].split("/")[-1] for k in prs}
            row["factors"], w = normalize_factors(r["factors"], changed, repos)
            from .story import plain_layer   # the scenario's name heads its row on the overview
            w += plain_layer("component", row["component"], repos)
            warn += [f"impact row {i + 1} ({row['component']}): {x}" for x in w]
        out.append(row)
    order = {k: i for i, k in enumerate(RISKS)}
    return sorted(out, key=lambda r: order[r["risk"]]), warn


def _area(path: str) -> str:
    """The folder a file belongs to, as a reader names it: its last two folders."""
    parts = PurePosixPath(path).parent.parts
    return "/".join(parts[-2:]) if parts else "(root)"


def derived(data: dict) -> list[dict]:
    """Rows from the diff alone, when the skill wrote none: one per folder a human reads code in.
    High only where an open high finding sits; must-read lines or a file no changed test calls is medium."""
    rows: dict[str, dict] = {}
    order = {k: i for i, k in enumerate(RISKS)}
    for pr in data.get("prs", []):
        gaps = {u["path"] for u in evidence(pr)["untested"]}
        ranges = (pr.get("attention") or {}).get("ranges", [])
        open_high = {f.get("path") for f in pr.get("findings", []) if f.get("status", "open") == "open" and f.get("severity") in ("high", "critical")}
        for f in pr.get("files", []):
            p = f["path"]
            if f.get("role", "source") != "source" or not CODE.search(p):
                continue
            deep = sum(r.get("lines", 0) for r in ranges if r["path"] == p and r.get("tier") == "deep")
            read = sum(r.get("lines", 0) for r in ranges if r["path"] == p and r.get("tier") == "review")
            if not deep and not read:
                continue
            a = _area(p)
            row = rows.setdefault(a, {"component": a, "paths": [], "prs": [], "lines": 0, "files": set(), "untested": set(),
                                      "high": 0, "deep": 0})
            row["paths"].append(p); row["files"].add(p); row["lines"] += deep + read; row["deep"] += deep
            row["high"] += p in open_high
            if p in gaps:
                row["untested"].add(p)
            if pr["key"] not in row["prs"]:
                row["prs"].append(pr["key"])
    out = []
    for a, r in rows.items():
        n, u = len(r["files"]), len(r["untested"])
        risk = "high" if r["high"] else "medium" if r["deep"] or u else "low"
        names = sorted(PurePosixPath(x).name for x in r["files"])
        out.append({"component": a, "paths": sorted(set(r["paths"])), "prs": r["prs"], "risk": risk, "source": "from the diff",
                    "change": f"{n} file{'s' if n != 1 else ''}, {r['lines']} lines to read" + (f", {r['deep']} must read" if r["deep"] else ""),
                    "affects": [], "workflows": [], "why": ", ".join(names[:4]) + (f" and {n - 4} more" if n > 4 else "")
                    + (f"; {r['high']} with an open high finding" if r["high"] else ""),
                    "evidence": [f"a changed test calls {'it' if n == 1 else f'{n - u} of {n}'}"] if n - u else [],
                    "gaps": [f"no changed test calls {'it' if n == 1 else f'{u} of {n}'}"] if u else []})
    return sorted(out, key=lambda r: (order[r["risk"]], -len(r["paths"]), r["component"]))


QUALITY_VERDICTS = ("fine", "concern")


def normalize_quality(raw, pr: dict) -> tuple[dict | None, list[str]]:
    """The skill's read of a PR's tests (enrich.json `prs.<key>.quality`): {summary, tests: [{path, verdict, why,
    covered_by}]}. A test entry explains a weakened test or a changed file no test calls: why it's fine, or the gap."""
    where, warn = f"{pr['key']} quality", []
    if not isinstance(raw, dict):
        return None, [f"{where}: must be an object with summary and tests"]
    ev = evidence(pr)
    known = {w for w in ev["weakened"]} | {u["path"] for u in ev["untested"]}
    paths = {f["path"] for f in pr.get("files", [])}
    tests = []
    raw_tests = raw.get("tests")
    if raw_tests is None:
        raw_tests = []
    elif not isinstance(raw_tests, list):
        warn.append(f"{where}: tests must be a list; ignored")
        raw_tests = []
    for t in raw_tests:
        if (not isinstance(t, dict) or not isinstance(t.get("path"), str) or not t["path"]
                or not isinstance(t.get("why"), str) or not t["why"].strip()):   # a blank why explains nothing
            warn.append(f"{where}: every test entry needs a path and a why ({t})")
            continue
        if t["path"] not in paths:
            warn.append(f"{where}: {t['path']} is not a changed file of this PR; dropped")
            continue
        if t["path"] not in known:
            warn.append(f"{where}: {t['path']} is neither a weakened test nor an untested file; kept, but say why it's here")
        v = t.get("verdict") if t.get("verdict") in QUALITY_VERDICTS else "concern"
        if t.get("verdict") not in QUALITY_VERDICTS:
            warn.append(f"{where}: {t['path']} verdict must be fine|concern; read as concern")
        cov = t.get("covered_by")
        if cov is not None and not isinstance(cov, str):
            warn.append(f"{where}: {t['path']} covered_by must be text (name the test or file); dropped")
        entry = {"path": t["path"], "verdict": v, "why": t["why"].strip(), **({"covered_by": cov.strip()} if isinstance(cov, str) and cov.strip() else {})}
        prev = next((i for i, x in enumerate(tests) if x["path"] == t["path"]), None)
        if prev is not None:   # one entry per file: a later one is the agent's correction
            warn.append(f"{where}: {t['path']} appears more than once; the last entry wins")
            tests[prev] = entry
        else:
            tests.append(entry)
    q = {"summary": str(raw.get("summary") or ""), "tests": tests}
    return q, warn + unexplained(pr, q)


def unexplained(pr: dict, quality: dict | None) -> list[str]:
    """A warning when the PR has weakened tests or untested files its quality section doesn't explain (or it has none)."""
    ev = evidence(pr)
    known = set(ev["weakened"]) | {u["path"] for u in ev["untested"]}
    left = sorted(known - {t["path"] for t in (quality or {}).get("tests") or []})
    if not left:
        return []
    return [f"{pr['key']} quality: no word on {', '.join(left[:4])}{' …' if len(left) > 4 else ''} "
            "(weakened tests and untested files the Quality tab lists; say why each is fine or what's missing)"]

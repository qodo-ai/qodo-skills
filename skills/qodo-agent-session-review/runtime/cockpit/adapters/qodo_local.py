"""Local findings: what the author's `qodo review` found before the PR, and what became of each one.

A stand-in for `local-findings` (pr-review-session): until it reads them from Qodo's DB, `cockpit local add` keeps
`qodo review --json` results and `fetch` reads those. A saved result can't see later dispositions, so open means
open at that review.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from ..util import HOME, ROOT, now_iso, write_json
from .qodo_cli import CLOSED, _first, _severity, kind_of

STORE = HOME / "local-findings"
BUCKETS = ("introduced", "still_open", "resolved", "dismissed")
PR_REF = re.compile(r"^(?:https?://github\.com/)?([^/\s#]+/[^/\s#]+?)(?:#|/pull/)(\d+)/?$", re.I)


def _git(cwd: str | None, *args: str) -> str | None:
    if not cwd:
        return None
    try:
        p = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (p.stdout.strip() or None) if p.returncode == 0 else None


def _repo_of(url: str | None) -> str | None:
    m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", url or "")
    return m.group(1) if m else None


def _fid(f: dict) -> str:
    return str(_first(f, "id", "finding_id", "uuid") or "")


def _all(result: dict) -> list[dict]:
    """Every finding the result describes: this call's list and each finding_state bucket."""
    fs = result.get("finding_state") if isinstance(result.get("finding_state"), dict) else {}
    return [f for f in result.get("findings") or [] if isinstance(f, dict)] + \
           [f for k in BUCKETS for f in fs.get(k) or [] if isinstance(f, dict)]


def count(result: dict) -> int:
    """How many distinct findings a result describes (its list and buckets overlap)."""
    return len({_fid(f) or str(i) for i, f in enumerate(_all(result))})


def _review_id(result: dict) -> str:
    """The run's own id: its stated id, else its checkpoint's, else the id its new findings carry. Replayed
    findings keep their first run's id, so those count last, and a tie is broken by name, never by chance."""
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    cp = meta.get("checkpoint") if isinstance(meta.get("checkpoint"), dict) else {}
    rid = _first(result, "local_review_id", "review_id") or _first(meta, "local_review_id", "review_id") or _first(cp, "id")
    fs = result.get("finding_state") if isinstance(result.get("finding_state"), dict) else {}
    references = meta.get('local_review_ids') if isinstance(meta.get('local_review_ids'), dict) else {}
    introduced_ids = {_fid(f) if isinstance(f, dict) else f for f in fs.get('introduced') or [] if isinstance(f, (dict, str))}
    own_ids = {references[fid] for fid in introduced_ids if fid and isinstance(references.get(fid), str) and references[fid]}
    if not rid and len(own_ids) == 1:
        rid = next(iter(own_ids))   # only explicitly introduced findings identify this execution
    for group in ([f for f in result.get("findings") or [] if isinstance(f, dict)] + [f for f in fs.get("introduced") or [] if isinstance(f, dict)],
                  _all(result)):
        if rid:
            break
        ids = sorted(str(f["local_review_id"]) for f in group if f.get("local_review_id"))
        rid = max(dict.fromkeys(ids), key=ids.count) if ids else None
    return str(rid or "noid-" + _digest(result))


def _digest(result: dict) -> str:
    return hashlib.sha1(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _ran_at(result: dict) -> str | None:
    """When the review ran: its checkpoint, current run timing, else its newest finding."""
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    cp = meta.get("checkpoint") if isinstance(meta.get("checkpoint"), dict) else {}
    run = meta.get('run') if isinstance(meta.get('run'), dict) else {}
    timing = run.get('timing') if isinstance(run.get('timing'), dict) else {}
    made = [str(f["created_at"]) for f in _all(result) if f.get("created_at")]
    return _first(cp, "created_at") or _first(timing, 'finished_at', 'started_at') or (max(made) if made else None)


def norm_pr(ref: str | None) -> str | None:
    """owner/repo#12, or a GitHub PR URL, as Agent Session Review's PR key; ValueError for anything else."""
    if not ref:
        return None
    m = PR_REF.match(ref.strip())
    if not m:
        raise ValueError(f"--pr {ref!r}: give owner/repo#12 or the PR's URL")
    return f"{m.group(1)}#{m.group(2)}"


def add(result: dict, *, pr: str | None = None, repo: str | None = None, branch: str | None = None,
        commit: str | None = None, cwd: str | None = None) -> dict:
    """Keep one `qodo review --json` result for the PR it belongs to. Repo and branch come from the findings
    themselves, else from git in `cwd`, the author's checkout (never Agent Session Review's own, where its commands usually
    run); `pr` names the PR when those won't find it (a fork, say). The reviewed commit is never taken from the
    checkout: the author may have committed since the review ran."""
    if not isinstance(result, dict) or not isinstance(result.get("findings"), list):
        raise ValueError("not a `qodo review --json` result: no findings list")
    if cwd and Path(cwd).resolve() == ROOT:
        cwd = None
    pr = norm_pr(pr)
    found = _all(result)
    org = next((f"{f['git_organization_name']}/{f['git_repo_name']}" for f in found
                if f.get("git_organization_name") and f.get("git_repo_name")), None)
    rec = {"local_review_id": _review_id(result), "pr": pr,
           "repo": repo or (pr.split("#")[0] if pr else None) or org or _repo_of(_git(cwd, "remote", "get-url", "origin")),
           "branch": branch or next((f["branch_name"] for f in found if f.get("branch_name")), None)
                     or _git(cwd, "rev-parse", "--abbrev-ref", "HEAD"),
           "commit": commit, "ran_at": _ran_at(result), "added_at": now_iso(), "result": result}
    if rec["branch"] == "HEAD":   # detached: no branch to match a PR by
        rec["branch"] = None
    if not rec["pr"] and not (rec["repo"] and rec["branch"]):
        raise ValueError("can't tell which PR this review is for: pass --pr owner/repo#n, or --dir with the checkout on the PR's branch")
    STORE.mkdir(parents=True, exist_ok=True)
    # named by content too: two different results never overwrite each other, the same one handed over twice does
    name = re.sub(r"[^A-Za-z0-9._-]", "_", rec["local_review_id"]) + "-" + _digest(result)
    from ..file_lock import file_lock
    with file_lock(STORE / '.import.lock'):
        write_json(STORE / f'{name}.json', rec)  # publish before retiring any older copy
        for old in STORE.glob('*.json'):
            if old.name != f'{name}.json' and _kept_digest(old) == _digest(result):
                old.unlink()
    return rec


def _kept_digest(p: Path) -> str | None:
    try:
        r = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return _digest(r["result"]) if isinstance(r, dict) and isinstance(r.get("result"), dict) else None


def _order(r: dict) -> tuple:
    meta = r["result"].get("meta") if isinstance(r["result"].get("meta"), dict) else {}
    cp = meta.get("checkpoint") if isinstance(meta.get("checkpoint"), dict) else {}
    seq = cp.get("sequence") if isinstance(cp.get("sequence"), int) else -1
    return (r.get("ran_at") or r.get("added_at") or "", seq, r.get("added_at") or "")


def records() -> list[dict]:
    """Every kept review, in the order they ran; the same result kept under two names counts once (the later)."""
    by_result: dict[str, dict] = {}
    for p in sorted(STORE.glob("*.json")) if STORE.is_dir() else []:
        try:
            r = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(r, dict) and isinstance(r.get("result"), dict):
            d = _digest(r["result"])
            if d not in by_result or (r.get("added_at") or "") >= (by_result[d].get("added_at") or ""):
                by_result[d] = r
    return sorted(by_result.values(), key=_order)


def _same(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and a.lower() == b.lower()


def fetch(pr: dict, cfg: dict) -> list[dict]:
    """The local reviews of this PR's work, in the order they ran. The one place `local-findings` will plug in."""
    return [r for r in records()
            if _same(r.get("pr"), pr.get("key")) or (not r.get("pr") and _same(r.get("repo"), pr.get("repo")) and r.get("branch") == pr.get("head"))]


def _merge(old: dict | None, new: dict) -> dict:
    """A later copy of a finding wins field by field; one that names only its disposition keeps the details."""
    if not old:
        return dict(new)
    out = dict(old)
    for k, v in new.items():
        if v not in (None, "", [], {}):
            out[k] = v
    return out


def _review_reference(rec: dict, f: dict):
    meta = rec.get('result', {}).get('meta') or {}
    references = meta.get('local_review_ids') if isinstance(meta, dict) else {}
    reference = references.get(_fid(f)) if isinstance(references, dict) else None
    return reference if isinstance(reference, str) and reference else _first(f, 'local_review_id') or rec.get('local_review_id')


def to_finding(pr: dict, rec: dict, f: dict, state: str | None, *, source_record: dict | None = None) -> dict:
    loc = next((f[k] for k in ("diff_reference", "location") if isinstance(f.get(k), dict)), {})
    fid = _fid(f)
    path = _first(f, "path", "file_path", "file") or _first(loc, "file_path", "path", "file")
    line = _first(f, "line", "start_line") or _first(loc, "start_line", "line")
    end = _first(f, "end_line") or _first(loc, "end_line")
    if not fid:
        what = [path, line, _first(f, "title", "summary", "name"), _first(f, "description", "body")]
        fid = "noid-" + hashlib.sha1(json.dumps(what, default=str).encode()).hexdigest()[:12]
    status = state or CLOSED.get(str(f.get("attribution_status") or "").lower()) or "open"
    reference = _review_reference(rec, f)
    origin = source_record if source_record is not None else rec if reference == rec.get('local_review_id') else {}
    seen = _first(f, "git_sha") or origin.get("commit")   # never borrow a later run's commit for a carried finding
    pre = str(loc.get("side") or "").lower() == "left"   # a line the diff removed: not in the new file
    here = bool(seen) and seen == pr.get("head_sha") and not pre   # its lines are this PR's lines
    ev = f.get("evidence") if isinstance(f.get("evidence"), dict) else {}
    out = {"id": f"l-{pr['key'].replace('/', '-').replace('#', '-')}-{fid}", "pr": pr["key"], "source": "qodo-local",
           "qodo_id": None if fid.startswith("noid-") else fid,
           "category": str(_first(f, "category") or "general").lower(), "severity": _severity(_first(f, "action_level", "severity")),
           "path": None if pre else path, "line": line if here else None, "end_line": end if here else None,
           "title": str(_first(f, "title", "summary", "name") or "Local finding"),
           "body": str(_first(f, "description", "body", "rationale") or _first(ev, "explanation") or ""),
           "qodo_type": _first(f, "type", "finding_type") or kind_of(f.get("finding_source")),
           "local": {"review_id": reference,
                     "at": _first(f, "created_at") or origin.get("ran_at") or origin.get("added_at"), "commit": seen,
                     "line": None if here else line}}
    if status != "open":
        out["status"] = status
    if status == "resolved":
        out["status_why"] = "the author's local review confirmed the fix"
    elif status == "dismissed":
        why = ": ".join(str(x) for x in (_first(f, "dismiss_reason"), _first(f, "dismiss_explanation")) if x)
        out["status_why"] = "dismissed by the author before the PR" + (": " + why if why else "")
        if why:
            out["local"]["reason"] = why   # the author's own words, for the styles' "before the PR" list
    elif status == 'detected_after_merge':
        out['status_why'] = 'Detected after the PR merged; no fix was verified.'
    from ..product import enabled
    if enabled(pr):
        from ..finding_locations import qualify
        out['source_location'] = {'path': path, 'line': line, 'end_line': end,
                                  'side': f.get('side') or loc.get('side'), 'git_sha': seen,
                                  'review_run_id': reference}
        out['closed_as'] = state or str(f.get('attribution_status') or '').lower() or None
        out = qualify(pr, out)
    return {k: v for k, v in out.items() if v is not None}


def collect(pr: dict, cfg: dict) -> list[dict]:
    """One finding per local finding id, as the latest local review left it. Each copy of a finding is merged
    into what earlier reviews said, so a later entry that only carries a disposition keeps the details."""
    raw: dict[str, tuple[dict, dict]] = {}   # finding id -> (the review that last mentioned it, its merged copy)
    status: dict[str, str] = {}
    reviews = fetch(pr, cfg)
    origins = {}
    for rec in reviews:
        if rec.get('local_review_id'):
            origins.setdefault(rec['local_review_id'], rec)
            if rec['local_review_id'].startswith('noid-'):
                observed_id = _review_id(rec['result'])
                if not observed_id.startswith('noid-'):
                    origins.setdefault(observed_id, rec)   # read older synthetic records without rewriting them
    for rec in reviews:
        res = rec["result"]
        fs = res.get("finding_state") if isinstance(res.get("finding_state"), dict) else {}
        def key(f):
            return (_fid(f) or to_finding(pr, rec, f, None)['id']) if isinstance(f, dict) else str(f)
        listed = [f for k in ("still_open", "introduced", "resolved", "dismissed") for f in fs.get(k) or [] if isinstance(f, dict)]
        listed += [f for f in res.get("findings") or [] if isinstance(f, dict)]   # last: this call's own copy
        for f in listed:
            fid = key(f)
            raw[fid] = (rec, _merge(raw.get(fid, (None, None))[1], f))
        for k in ("still_open", "introduced"):
            for f in fs.get(k) or []:
                fid = key(f)
                if fid:
                    status[fid] = "open"   # a latest explicit reopen overrides retained attribution metadata
        for k in ("dismissed", "resolved"):   # resolved last: it wins over dismissed, as in the engine
            for f in fs.get(k) or []:
                fid = key(f)
                if fid:
                    status[fid] = k
    return [to_finding(pr, rec, f, status.get(fid), source_record=origins.get(_review_reference(rec, f))) for fid, (rec, f) in raw.items()]

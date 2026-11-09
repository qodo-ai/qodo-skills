"""Qodo's findings from its review DB, through the toolbox CLI (`qodo read pr-review-session findings`).
None when the CLI can't answer, so the caller falls back to Qodo's PR comments; ids match the comment adapter's."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess

from .qodo_comments import _fid

# attribution_status, as the tool documents it: open ones carry no status; closed ones map to the cockpit's.
# `implemented` isn't in the tool's documented list, but the review producer has serialized it; closed either way.
CLOSED = {"full_implementation": "resolved", "implemented": "resolved", "detected_after_merge": "resolved",
          "dismissed": "dismissed", "outdated": "outdated"}


# The review DB names a finding's kind in `finding_source` (the review agent that raised it). The labels are the
# review producer's own badges, so the cockpit says what Qodo's comment says; skills keep
# the summary comment's "Skill insight". Like the producer, an unlisted source is a suggestion.
TYPES = {"issuefinding": "Bug", "compliancerule": "Rule violation", "complianceagentfilerule": "Rule violation",
         "complianceticketrule": "Requirement gap", "specfinding": "Requirement gap", "uiruntimefinding": "UI issue",
         "uifinding": "UX issue", "crossrepofinding": "Cross-repo conflict", "personafinding": "Team insight",
         "skillsfinding": "Skill insight", "memoryfinding": "Memory", "securityfinding": "Security issue",
         "skillfinding": "Skill insight", "skillinsight": "Skill insight", "requirementgap": "Requirement gap"}


def kind_of(source) -> str | None:
    s = str(source or "").strip()
    return (TYPES.get(s.replace("_", "").lower()) or "Suggestion") if s else None


def _type(f: dict):
    return _first(f, "type", "finding_type") or kind_of(f.get("finding_source"))


def _severity(level) -> str:
    s = str(level or "").lower()
    for words, sev in ((("critical", "blocker"), "critical"), (("high", "required", "action"), "high"),
                       (("medium", "recommended", "remediation"), "medium"), (("low", "info", "optional", "nit"), "low")):
        if any(w in s for w in words):
            return sev
    return "medium"


def _first(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return None


def fetch(pr: dict, cfg: dict) -> dict | None:
    """The tool's raw answer, or None when the CLI can't give one for this PR."""
    from ..product import enabled
    if enabled(pr):
        from .managed import Client, ReadError
        if not isinstance(pr.get('url'), str) or not pr['url'].startswith(('https://', 'http://')):
            pr['qodo_read_error'] = 'Qodo findings unavailable: change context omitted a valid PR URL'
            return None
        try:
            return Client().read('pr-review-session', 'findings', pr_url=pr['url'], extended=True)
        except ReadError as e:
            pr['qodo_read_error'] = str(e)
            return None
    cmd = (cfg.get("qodo_findings") or {}).get("command") or "qodo"
    if not shutil.which(cmd) or not pr.get("url"):
        return None
    try:
        # `qodo read ...`: the tool's permission-safe gateway, which only runs non-mutating operations
        p = subprocess.run([cmd, "read", "pr-review-session", "findings", "--pr-url", pr["url"], "--extended", "--json"],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:   # not logged in, repo not in this workspace, deployment down
        return None
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return None
    if not isinstance(d, dict) or not isinstance(d.get("findings"), list):
        return None   # not the envelope the tool documents: don't mistake it for an empty review
    if not d.get("review_session") or d.get("qar_operation_result_truncated"):
        return None   # no review on this deployment (the comments may be from another), or an incomplete read
    return d


def to_finding(pr: dict, f: dict) -> dict:
    loc = f.get("location") if isinstance(f.get("location"), dict) else {}
    fid = str(_first(f, "id", "finding_id", "uuid") or "")
    if not fid:   # no id from the tool: a stable one from what the finding says, so two never collapse into one
        what = [_first(f, "path", "file_path", "file") or _first(loc, "path", "file_path", "file"),
                _first(f, "line", "start_line") or _first(loc, "line", "start_line"), _first(f, "title", "summary", "name"), _first(f, "description", "body")]
        fid = "noid-" + hashlib.sha1(json.dumps(what, default=str).encode()).hexdigest()[:12]
    status = CLOSED.get(str(f.get("attribution_status") or "").lower())
    out = {"id": _fid(pr, fid), "pr": pr["key"], "source": "qodo", "qodo_id": None if fid.startswith("noid-") else fid,
           "category": str(_first(f, "category") or "general").lower(), "severity": _severity(_first(f, "action_level", "severity")),
           "path": _first(f, "path", "file_path", "file") or _first(loc, "path", "file_path", "file"),
           "line": _first(f, "line", "start_line") or _first(loc, "line", "start_line"),
           "end_line": _first(f, "end_line") or _first(loc, "end_line"),
           "title": str(_first(f, "title", "summary", "name") or "Qodo finding"),
           "body": str(_first(f, "description", "body", "explanation", "rationale") or ""),
           "url": _first(f, "url", "comment_url"), "qodo_url": _first(f, "portal_url", "finding_url"),
           "qodo_type": _type(f), "commit": _first(f, "commit_sha", "commit"),
           "inline_comment_id": _first(f, "inline_comment_id")}   # its GitHub thread, when the review comment's link isn't matched
    from ..product import enabled
    if enabled(pr):
        origin = f.get('review_source') or 'unknown'
        out.update(review_source=origin, git_sha=f.get('git_sha'), review_run_id=f.get('review_run_id'), created_at=f.get('created_at'), side=f.get('side') or loc.get('side'))
        out['commit'] = f.get('git_sha') or out.get('commit')
        if origin == 'local_skill':
            out['source'] = 'qodo-local'
            out['local'] = {'origin': 'managed', 'review_id': f.get('review_run_id'),
                            'at': f.get('created_at'), 'commit': out.get('commit')}
        from ..finding_locations import qualify
        out = qualify(pr, out)
    if status:
        out["status"] = status
        out["closed_as"] = str(f.get("attribution_status") or "").lower()   # detected_after_merge is closed, not fixed
        if status == "dismissed":   # the producer sends flat dismiss_reason / dismiss_explanation; older shapes nest it
            d = f.get("dismissal") if isinstance(f.get("dismissal"), dict) else {}
            why = [x for x in (_first(f, "dismiss_reason") or _first(d, "reason"), _first(f, "dismiss_explanation") or _first(d, "explanation", "comment")) if x]
            if why:
                out["status_why"] = ": ".join(str(x) for x in dict.fromkeys(why))
    return {k: v for k, v in out.items() if v is not None}


def collect(pr: dict, cfg: dict) -> list[dict] | None:
    d = fetch(pr, cfg)
    if not isinstance(d, dict) or not isinstance(d.get('findings'), list):
        return None
    pr["qodo_review_evidence"] = {k: v for k, v in d.items() if k != "findings"}
    rs = d.get("review_session") if isinstance(d.get("review_session"), dict) else {}
    pr["qodo_review"] = {
        "status": rs.get("status"), "commit": rs.get("commit_sha") or rs.get('reviewed_commit_sha'),
        "review_complete": rs.get('review_complete', d.get('review_complete')),
        "run_id": rs.get('id') or rs.get('review_session_id') or rs.get('run_id'),
        "bounded": bool(d.get('qar_operation_result_truncated') or d.get('result_is_page') or d.get('next_read_cursor') or
                        d.get('truncated') or d.get('complete') is False or (d.get('finding_state') or {}).get('complete') is False or
                        ((d.get('meta') or {}).get('coverage') or {}).get('complete') is False),
        "review_session": rs,
    }
    return [to_finding(pr, f) for f in d["findings"] if isinstance(f, dict)]

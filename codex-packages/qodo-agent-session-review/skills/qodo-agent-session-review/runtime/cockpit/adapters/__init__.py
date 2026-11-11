"""Pluggable sources of findings: Qodo, and the security scanners that comment on PRs.

Each adapter exposes `collect(pr: dict, cfg: dict) -> list[dict]` returning normalized findings:
{id, pr, source, category, severity, path, line, title, body, url}
plus optional Qodo extras (qodo_id, qodo_url, qodo_type, qodo_aspect, rule, prompt, end_line, side).
An adapter may also expose `pr_context(pr, cfg) -> dict` (Qodo summary, labels, diagram).
"""
import sys

from . import qodo_api, qodo_cli, qodo_comments, qodo_local, scanners

REGISTRY = {"qodo_comments": qodo_comments, "qodo_api": qodo_api, "qodo_local": qodo_local, "scanners": scanners}


def qodo_findings(pr: dict, cfg: dict) -> list[dict]:
    """Qodo's findings from the source config `qodo_findings.source` names: `auto` (the default) reads Qodo's
    review DB through the `qodo` CLI when it is installed, logged in and has a review for the PR, else Qodo's
    PR comments; `cli` only the CLI; `comments` only the comments. pr["qodo_source"] says which one answered."""
    src = str((cfg.get("qodo_findings") or {}).get("source") or "auto").lower()
    if src in ("auto", "cli"):
        got = qodo_cli.collect(pr, cfg)
        if got is not None:
            # the review DB has no links (only ids): take them from the same finding's PR comment
            from_comments = qodo_comments.collect(pr, cfg)
            by_id = {c["id"]: c for c in from_comments if isinstance(c, dict) and c.get("id")}
            for f in got:
                c = by_id.get(f["id"]) or {}
                for k in ("url", "qodo_url"):
                    if not f.get(k) and c.get(k):
                        f[k] = c[k]
            if not got and src == "auto" and from_comments:
                # a session with no stored findings while the comments carry some: the DB write can fail after
                # the comments post, so trust the comments rather than show a clean review
                pr["qodo_source"] = "comments"
                return from_comments
            pr["qodo_source"] = "cli"
            return got
        if src == "cli":
            print(f"warning: {pr.get('key')}: qodo CLI has no review for this PR (not installed, not logged in, "
                  f"or the repo isn't in its workspace); no Qodo findings", file=sys.stderr)
            pr["qodo_source"] = "none"
            return []
    got = qodo_comments.collect(pr, cfg)
    # no findings and no review comment: Qodo hasn't reviewed this PR, which the page must not read as clean
    pr["qodo_source"] = "comments" if got or qodo_comments.reviewed(pr, cfg) else "none"
    return got


def collect_findings(pr: dict, cfg: dict) -> list[dict]:
    out, seen = [], set()
    for name in cfg.get("adapters", ["qodo_comments"]):
        from ..product import enabled
        if enabled(pr) and name == 'qodo_api':
            continue   # arbitrary user-configured command adapters are standalone-only
        mod = REGISTRY.get(name)
        if not mod:
            continue
        for f in (qodo_findings(pr, cfg) if name == "qodo_comments" else mod.collect(pr, cfg)):
            if f["id"] not in seen:
                seen.add(f["id"]); out.append(f)
    # one record: a local finding Qodo carried into the PR review is that finding, not a second one
    by_qodo = {f["qodo_id"]: f for f in out if f.get("qodo_id") and f.get("source") != "qodo-local"}
    for f in [f for f in out if f.get("source") == "qodo-local" and f.get("qodo_id") in by_qodo]:
        by_qodo[f["qodo_id"]]["local"] = {**f["local"], "status": f.get("status", "open")}
        out.remove(f)
    return out


def annotation_checks(cfg: dict) -> list[str]:
    """Check-run names or app slugs whose annotations the enabled scanners read."""
    if "scanners" not in cfg.get("adapters", ["qodo_comments"]):
        return []
    return [g for c in (cfg.get("scanners") or {}).values() if c.get("enabled") is not False for g in c.get("checks", [])]


def scan_summary(pr: dict, cfg: dict, findings: list[dict]) -> list[dict]:
    """Which scanners ran on the PR and what they concluded, clean runs included."""
    if "scanners" not in cfg.get("adapters", ["qodo_comments"]):
        return []
    return scanners.scans(pr, cfg, findings)


def pr_context(pr: dict, cfg: dict) -> dict:
    out: dict = {}
    for name in cfg.get("adapters", ["qodo_comments"]):
        fn = getattr(REGISTRY.get(name), "pr_context", None)
        if fn:
            out.update(fn(pr, cfg) or {})
    return out

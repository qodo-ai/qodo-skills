"""Qodo's Development Track Notes and PR Review Notes: the plan a coding agent left for the review.

Read through the qodo CLI (`qodo read review-notes ...`, reads only; the toolbox's managed tools). A PR's notes say
its intent, decisions, review focus, validation and known gaps; its track says the effort's goal, product decisions,
dependencies and merge/release order. Both are Markdown. The Decision Review style puts what the diff does against
them. Everything here is best effort: no CLI, no login, an unregistered repo or no notes all mean "no notes", said
plainly, and never stop a review.
"""
from __future__ import annotations

import json
import shutil
import subprocess

TIMEOUT = 20      # per CLI call
BUDGET = 90       # for the whole collect: notes are optional and never hold a review up for long
MAX_PAGES = 20    # a paged result (over 1 MiB) comes back in pieces; more than this is not a plan anyone reads
from contextvars import ContextVar
_END = ContextVar('cockpit_notes_end', default=None)   # while collect() runs: when its BUDGET ends; per thread, so parallel refreshes keep their own


def _cmd(cfg: dict) -> str | None:
    from .product import enabled
    if enabled():
        from .adapters.managed import Client
        return Client().command
    c = ((cfg.get("notes") or {}).get("command")) or "qodo"
    return c if shutil.which(c) else None


def _read(cmd: str, leaf: str, args: list[str]) -> tuple[dict | None, str | None]:
    """One read tool, following its pages. Returns (result, error)."""
    parts, cursor = [], None
    for _ in range(MAX_PAGES):
        argv = [cmd, "read", "review-notes", leaf, *args, "--json"] + (["--read-cursor", cursor] if cursor else [])
        try:
            from .product import enabled
            if enabled():
                from .adapters.managed import Client, ReadError
                from types import SimpleNamespace
                params = {args[i][2:].replace('-', '_'): args[i+1] for i in range(0, len(args), 2)}
                for k in ('pr_number',):
                    if k in params:
                        params[k] = int(params[k])
                if cursor:
                    params['read_cursor'] = cursor
                try:
                    import time
                    end = _END.get()
                    left = (end - time.monotonic()) if end else None   # notes never outlast their own budget
                    if left is not None and left <= 0:
                        return None, f'{leaf}: skipped, reading notes took over {BUDGET}s'
                    value = Client(cmd).read('review-notes', leaf, max_seconds=left, **params)
                except ReadError as err:
                    return None, str(err)
                r = SimpleNamespace(stdout=json.dumps(value), returncode=0)
            else:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
        except PermissionError:
            if enabled():
                raise
            return None, f'{leaf}: PermissionError'
        except (OSError, subprocess.TimeoutExpired) as e:
            return None, f"{leaf}: {e.__class__.__name__}"
        text = r.stdout[r.stdout.find("{"):] if "{" in r.stdout else ""   # the whole JSON, pretty-printed or not
        try:
            out = json.loads(text) if text else {}
        except ValueError:
            return None, f"{leaf}: unreadable output"
        if not isinstance(out, dict):
            return None, f"{leaf}: unexpected output"
        if r.returncode != 0 or "error" in out:
            err = out.get("error")
            code = (err.get("code") or err.get("message")) if isinstance(err, dict) else err
            return None, f"{leaf}: {code or f'exit {r.returncode}'}"
        if enabled() and out.get('qar_operation_result_truncated'):
            return None, f'{leaf}: truncated result'
        if not out.get("result_is_page"):
            if out.get('qar_operation_result_truncated'):
                return None, f'{leaf}: truncated result'
            return out, None
        parts.append(out.get("text") or "")
        cursor = out.get("next_read_cursor")
        if not cursor:
            try:
                joined = json.loads("".join(parts))
            except ValueError:
                return None, f"{leaf}: pages don't join"
            return (joined, None) if isinstance(joined, dict) else (None, f"{leaf}: unexpected output")
    return None, f"{leaf}: more than {MAX_PAGES} pages"


def repo_ref(cmd: str, repo: str, host: str, cache: dict, provider: str = "github") -> tuple[str | None, str | None]:
    """The registry's opaque id for owner/repo (GitHub: the numeric repo id). The notes tools take this, not the path."""
    if (repo, host, provider) not in cache:
        out, err = _read(cmd, "resolve-repository", ["--repo", repo, "--provider", provider, "--provider-host", host])
        cache[(repo, host, provider)] = ((out or {}).get("repo_ref") or (out or {}).get("repoRef"), err)
    return cache[(repo, host, provider)]


def _doc(rec: dict | None) -> dict:
    return (rec or {}).get("document") or {}


def for_pr(pr: dict, cfg: dict, cache: dict) -> dict:
    """The PR's notes and its track, or why there are none: {status, pr?, track?, why?}."""
    cmd = _cmd(cfg)
    if not cmd:
        return {"status": "unavailable", "why": "the qodo CLI is not installed"}
    host = pr.get('provider_host') or (cfg.get("notes") or {}).get("provider_host") or "github.com"
    provider = pr.get('provider') or 'github'
    ref, err = repo_ref(cmd, pr["repo"], host, cache, provider)
    if not ref:
        return {"status": "unavailable", "why": f"{pr['repo']} is not registered in this Qodo workspace" if err and "NOT-FOUND" in err else (err or "no repository id")}
    out, err = _read(cmd, "for-pr", ["--provider", provider, "--provider-host", host, "--target-repo-ref", str(ref),
                                     "--pr-number", str(pr["number"]), "--current-head-sha", pr.get("head_sha") or ""])
    if err:
        return {"status": "unavailable", "why": err}
    status = out.get("lookupStatus") or "lookup_failed"
    res: dict = {"status": status}
    if out.get("prContext"):
        rec, doc = out["prContext"], _doc(out["prContext"])
        checks, fits = doc.get("validationChecks") or [], out.get("validationApplicability") or []
        res["pr"] = {"id": rec.get("id"), "markdown": (doc.get("contentMarkdown") or "")[:60000],
                     "content_truncated": len(doc.get("contentMarkdown") or "") > 60000, "digest": rec.get("digest") or doc.get("digest"),
                     "revision": rec.get("publishedRevision"), "published_at": rec.get("publishedAt"),
                     "commit_at_update": doc.get("commitShaAtUpdate"),
                     "head_matches": bool(doc.get("commitShaAtUpdate")) and doc.get("commitShaAtUpdate") == pr.get("head_sha"),
                     "by": ((rec.get("updatedBy") or {}).get("agentName") or (rec.get("updatedBy") or {}).get("actorKind")),
                     "validation": [{"name": c.get("name"), "result": c.get("result"), "commit": c.get("testedCommitSha"),
                                     "applies": bool(fits[i]) if i < len(fits) else None} for i, c in enumerate(checks)]}
    if out.get("developmentTrack"):
        rec, doc = out["developmentTrack"], _doc(out["developmentTrack"])
        res["track"] = {"id": rec.get("id"), "title": doc.get("title"), "status": doc.get("status"),
                        "markdown": (doc.get("contentMarkdown") or "")[:60000],
                        "revision": rec.get("publishedRevision"), "digest": rec.get("digest") or doc.get("digest"),
                        "content_truncated": len(doc.get("contentMarkdown") or "") > 60000,
                        "issues": [i.get("displayKey") or i.get("issueId") for i in doc.get("issueRefs") or []]}
    if status == "no_pr_notes":
        res["why"] = "no PR Review Notes are bound to this PR"
    elif status == "linked_track_unavailable":
        res["why"] = "the PR's track is linked but can't be read (a repository it names is not readable to you)"
    return res


def collect(prs: list[dict], cfg: dict) -> None:
    """pr["notes"] for every PR. Off with config notes.enabled = false."""
    if (cfg.get("notes") or {}).get("enabled") is False:
        return
    import sys
    import time
    if _cmd(cfg):
        print("Reading Qodo's review notes", file=sys.stderr)
    cache: dict = {}
    end = time.monotonic() + BUDGET
    token = _END.set(end)
    try:
        for pr in prs:
            if time.monotonic() > end:
                pr["notes"] = {"status": "unavailable", "why": f"skipped: reading notes took over {BUDGET}s"}; continue
            try:
                pr["notes"] = for_pr(pr, cfg, cache)
            except PermissionError:
                from .product import enabled
                if enabled(pr):
                    raise
                pr['notes'] = {'status': 'unavailable', 'why': 'could not read optional notes (PermissionError)'}
            except Exception as e:   # an output shape we didn't expect: no notes, said plainly, and the review goes on
                pr["notes"] = {"status": "unavailable", "why": f"couldn't read the notes ({e.__class__.__name__})"}
    finally:
        _END.reset(token)   # later reads (a refresh's) use their own limits

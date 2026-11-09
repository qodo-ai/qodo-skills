"""Explicit managed product profile; saved sessions retain the local-only boundary."""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature
from urllib.parse import urlsplit

_SELECTED = ContextVar("cockpit_product_operation", default=False)


def enabled(data=None):
    return os.environ.get('REVIEW_COCKPIT_PRODUCT') == '1' or _SELECTED.get() or bool((data or {}).get('product'))


def activate():
    os.environ['REVIEW_COCKPIT_PRODUCT'] = '1'


@contextmanager
def scope(data=None):
    """Session/operation choice is local to this context, never a process environment toggle."""
    token = _SELECTED.set(enabled(data))
    try:
        yield
    finally:
        _SELECTED.reset(token)


def session_operation(fn):
    """Scope transitive reads to the saved session for the duration of one operation."""
    params = signature(fn)
    @wraps(fn)
    def run(*args, **kwargs):
        bound = params.bind(*args, **kwargs).arguments
        sdir = bound['sdir']
        path = sdir / 'review-data.json'
        saved = json.loads(path.read_text()) if path.is_file() else {}
        data = bound.get('data') or {}
        with scope({'product': bool(saved.get('product') or data.get('product'))}):
            return fn(*args, **kwargs)
    return run


def local_only(data=None):
    return enabled(data)


NOTICE = ('Local review and export only. Notes and accept/dismiss marks stay on this machine; '
          'they do not publish comments, resolve provider threads or change Qodo dispositions.')


def qodo_current(pr):
    rv = pr.get('qodo_review') or {}
    return bool(pr.get('qodo_source') == 'cli' and pr.get('head_sha') and
                rv.get('status') == 'completed' and rv.get('review_complete') is True and
                rv.get('commit') == pr['head_sha'] and rv.get('run_id') and rv.get('bounded') is False)


_LINK_FIELDS = {'url', 'qodo_url', 'repository_url', 'html_url', 'details_url', 'target_url', 'source_url', 'report_url', 'href'}
# These envelopes are source evidence, not normalized presentation objects.
_PROVENANCE_FIELDS = {'read_evidence', 'qodo_review_evidence', 'qodo_review', 'patch_evidence', 'source_evidence',
                      'identity', 'provenance', 'raw', 'raw_metadata', 'provider_threads', '_raw_comments', '_annotations', '_threads'}


def safe_http_url(value):
    if not isinstance(value, str) or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme.lower() in ('http', 'https') and parsed.netloc and parsed.hostname else None
    except ValueError:
        return None


def presentation_links(value):
    """Copy normalized links for product rendering; retain raw/provenance envelopes verbatim."""
    if isinstance(value, list):
        return [presentation_links(item) for item in value]
    if isinstance(value, dict):
        return {key: item if key in _PROVENANCE_FIELDS else safe_http_url(item) if key in _LINK_FIELDS else presentation_links(item)
                for key, item in value.items()}
    return value


def local_patch_evidence(pr):
    """Local collection quality, independent of Qodo's authoritative review run."""
    files = ((pr.get('read_evidence') or {}).get('sections') or {}).get('files') or {}
    if pr.get('files_complete', files.get('complete')) is not True:
        return {'complete':False, 'reason':'Changed-file list completeness is unknown.'}
    if pr.get('files_missing', 0) > 0:
        return {'complete':False, 'reason':f"{pr['files_missing']} known changed files are missing."}
    missing = []
    for file in pr.get('files', []):
        patch = file.get('patch_evidence') or {}
        if patch.get('complete') is not True or not patch.get('items') or not all(item.get('patch_complete') is True for item in patch['items']):
            missing.append(file.get('path') or 'unknown file')
    if missing:
        return {'complete':False, 'reason':'Patch evidence is missing or incomplete for ' + ', '.join(missing) + '.'}
    return {'complete':True, 'reason':None}


def project_pr(pr):
    """Presentation authority is separate from useful comment-derived evidence."""
    sections = (pr.get('read_evidence') or {}).get('sections') or {}
    known = lambda kinds: all((sections.get(k) or {}).get('complete') is True for k in kinds)
    ci = known(('checks', 'statuses'))
    scans = []
    for scan in pr.get('scans') or []:
        observed = scan.get('observed_status', scan.get('status'))
        authoritative = bool(pr.get('head_sha') and scan.get('commit_sha') == pr['head_sha'] and ci)
        scans.append({**scan, 'observed_status': observed, 'authoritative': authoritative,
                      'status': observed if authoritative else 'unknown',
                      'text': scan.get('text') if authoritative else 'Comment evidence; current-head scanner run unverified'})
    review = qodo_current(pr)
    patch_proof = local_patch_evidence(pr)
    patches = patch_proof['complete']
    complete = not pr.get('collection_incomplete') and patches and review and ci and known(('comments', 'inline_comments', 'annotations')) and all(s['authoritative'] for s in scans)
    from .finding_locations import qualify
    return presentation_links({**pr, 'product': True, 'scans': scans, 'findings': [qualify(pr, f) for f in pr.get('findings', [])],
            'product_evidence': {'qodo_complete': review, 'ci_complete': ci, 'patches_complete': patches, 'patches_reason': patch_proof['reason'], 'quality_complete': complete}})


def project_data(data):
    return presentation_links({**data, 'product': True, 'provider_writes': False,
            'prs': [project_pr({**p, 'collection_incomplete': (data.get('collection') or {}).get('complete') is False}) for p in data.get('prs', [])]})

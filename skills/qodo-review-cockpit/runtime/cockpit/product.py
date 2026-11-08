"""Explicit managed product profile; saved sessions retain the local-only boundary."""
from __future__ import annotations

import os


def enabled(data=None):
    return os.environ.get('REVIEW_COCKPIT_PRODUCT') == '1' or bool((data or {}).get('product'))


def activate():
    os.environ['REVIEW_COCKPIT_PRODUCT'] = '1'


def local_only(data=None):
    return enabled(data)


NOTICE = ('Local review and export only. Notes and accept/dismiss marks stay on this machine; '
          'they do not publish comments, resolve provider threads or change Qodo dispositions.')


def qodo_current(pr):
    rv = pr.get('qodo_review') or {}
    return bool(pr.get('qodo_source') == 'cli' and pr.get('head_sha') and
                rv.get('status') == 'completed' and rv.get('review_complete') is True and
                rv.get('commit') == pr['head_sha'] and rv.get('run_id') and rv.get('bounded') is False)


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
    paths = pr.get('files_complete', (sections.get('files') or {}).get('complete')) is True
    complete = paths and review and ci and known(('comments', 'inline_comments', 'annotations')) and all(s['authoritative'] for s in scans)
    return {**pr, 'product': True, 'scans': scans,
            'product_evidence': {'qodo_complete': review, 'ci_complete': ci, 'quality_complete': complete}}


def project_data(data):
    return {**data, 'product': True, 'provider_writes': False,
            'prs': [project_pr(p) for p in data.get('prs', [])]}

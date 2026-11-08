"""Bounded Qodo CLI managed repository reads. Never falls back to a provider client.

Raw page envelopes are retained alongside normalized data: exhaustion is not completeness,
capability is not permission, and an observed change revision is not an atomic snapshot.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

MAX_PAGES = 20
MAX_PATCHES = 100
MAX_OPERATION_CALLS = 96
MAX_OPERATION_SECONDS = 180
_CURRENT_BUDGET = ContextVar('cockpit_managed_read_budget', default=None)


class ReadError(RuntimeError):
    pass


class ScopedPermissionDenied(ReadError):
    """This provider read is unavailable; independent authorized reads may continue."""


class BudgetExceeded(ReadError):
    pass


class ReadBudget:
    """Shared across a whole product operation, including nested adapters and secondary reads."""
    def __init__(self, max_calls=None, seconds=None):
        self.max_calls = MAX_OPERATION_CALLS if max_calls is None else max_calls
        self.deadline = time.monotonic() + (MAX_OPERATION_SECONDS if seconds is None else seconds)
        self.calls = 0

    def reserve(self):
        left = self.deadline - time.monotonic()
        if self.calls >= self.max_calls or left <= 0:
            raise BudgetExceeded('Managed read operation budget exhausted; remaining evidence is unavailable')
        self.calls += 1
        return min(120, left)

    def summary(self):
        return {'calls': self.calls, 'max_calls': self.max_calls,
                'remaining_seconds': max(0, self.deadline-time.monotonic()),
                'exhausted': self.calls >= self.max_calls or time.monotonic() >= self.deadline}


@contextmanager
def read_operation(budget=None):
    existing = _CURRENT_BUDGET.get()
    if existing is not None:
        yield existing
        return
    token = _CURRENT_BUDGET.set(budget or ReadBudget())
    try:
        yield _CURRENT_BUDGET.get()
    finally:
        _CURRENT_BUDGET.reset(token)


def bounded_operation(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with read_operation():
            return fn(*args, **kwargs)
    return wrapped


def current_budget():
    return _CURRENT_BUDGET.get()


class PermissionDenied(PermissionError):
    """Stop this path. Callers must surface it rather than try alternate credentials/transports."""


def decode_result(result, group, tool):
    try:
        out = json.loads(result.stdout)
    except ValueError as e:
        if any(code in (result.stderr or '').lower() for code in ('not_logged_in', 'token_expired', 'invalid_token', 'forbidden', 'permission denied')):
            raise PermissionDenied(f'{group}/{tool}: CLI authentication or permission unavailable; owner action required') from e
        raise ReadError(f'{group}/{tool}: unreadable response (exit {result.returncode})') from e
    if result.returncode or (isinstance(out, dict) and out.get('error')):
        err = out.get('error') if isinstance(out, dict) else None
        code = str((err or {}).get('code', 'unavailable')) if isinstance(err, dict) else 'unavailable'
        metadata = (err.get('metadata') or {}) if isinstance(err, dict) else {}
        if str(metadata.get('upstream_status')) in ('401', '403'):
            raise ScopedPermissionDenied(f'{group}/{tool}: provider permission limited ({metadata["upstream_status"]}); no retry or fallback')
        if any(x in code.upper() for x in ('PERMISSION', 'FORBIDDEN', 'DENIED', 'NOT-IN-SCOPE', 'UNAUTHORIZED', 'NO-CREDENTIAL', 'NOT_LOGGED_IN', 'TOKEN_EXPIRED', 'INVALID_TOKEN')):
            raise PermissionDenied(f'{group}/{tool}: {code}; owner action required')
        raise ReadError(f'{group}/{tool}: {code} (exit {result.returncode})')
    if not isinstance(out, dict):
        raise ReadError(f'{group}/{tool}: expected object')
    return out


class Client:
    def __init__(self, command=None, budget=None):
        self.budget = budget or current_budget() or ReadBudget()
        self.command = command or os.environ.get('REVIEW_COCKPIT_QODO') or shutil.which('qodo') or str(Path.home() / '.qodo/bin/qodo')

    def read(self, group, tool, **args):
        timeout = (current_budget() or self.budget).reserve()
        try:
            # Installed CLI 2.1.1 advertises --args-file. Preserve booleans/numbers/cursors
            # as JSON instead of treating every dynamic schema option as a string flag.
            with tempfile.TemporaryDirectory(prefix='cockpit-qodo-') as temporary:
                params = Path(temporary) / 'args.json'
                params.write_text(json.dumps({key: value for key, value in args.items() if value is not None}), encoding='utf-8')
                argv = [self.command, 'read', group, tool, '--args-file', str(params), '--json']
                result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except PermissionError as e:
            raise PermissionDenied(f'{group}/{tool}: process permission denied; owner action required') from e
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ReadError(f'{group}/{tool}: {type(e).__name__}') from e
        return decode_result(result, group, tool)

    def identity(self, repo, host=None):
        # Native URL routes are not necessarily the registry's canonical full_name.
        native_route = '/_git/' in repo or bool(re.match(r'^projects/[^/]+/repos/', repo, re.I))
        result = self.read('codebase', 'search-repos', query=repo.rsplit('/', 1)[-1] if native_route else repo, max_results=1000)
        matches = [r for r in result.get('repos', []) if
                   (r.get('full_name') == repo or (str(r.get('provider') or '').lower() == 'github' and str(r.get('full_name') or '').casefold() == repo.casefold()) or (native_route and urlsplit(r.get('html_url') or '').path.rstrip('/') == '/' + repo.rstrip('/'))) and
                   (not host or urlsplit(r.get('html_url') or '').hostname == host)]
        if len(matches) != 1 or result.get('truncated') or result.get('next_page_token'):
            raise ReadError('Repository discovery is ambiguous, missing or truncated; supply an exact registered repository and host URL')
        r = matches[0]
        url = r.get('html_url')
        instance = r.get('host') or r.get('provider_host') or urlsplit(url or '').hostname
        if not r.get('provider') or not instance:
            raise ReadError('Repository discovery omitted canonical provider/host')
        return dict(repo=r['full_name'], provider=r['provider'], provider_host=instance, repository_url=url)

    def pages(self, identity, kind, number=None, revision=None, **selectors):
        args = dict(identity, kind=kind, change_number=number, revision=revision, limit=100, max_bytes=65536, **selectors)
        pages, items, cursor, seen = [], [], None, set()
        for _ in range(MAX_PAGES):
            try:
                page = self.read('codebase', 'read-review-data', **args, cursor=cursor)
            except ReadError as e:
                return {'items': items, 'pages': pages, 'complete': False, 'status': 'bounded' if isinstance(e, BudgetExceeded) else 'permission_limited' if isinstance(e, ScopedPermissionDenied) else 'unavailable', 'error': str(e), 'next_cursor': cursor}
            if not isinstance(page.get('items'), list) or 'complete' not in page or 'next_cursor' not in page:
                raise ReadError('Malformed provider-evidence page for ' + kind)
            # Mixing revisions would associate patches/evidence with the wrong head. Abort collection.
            if revision and page.get('revision') != revision:
                raise ReadError('Change revision changed or missing while reading ' + kind + '; restart collection')
            pages.append(page)
            items.extend(page.get('items') or [])
            cursor = page.get('next_cursor')
            if not cursor:
                complete = page.get('complete') if page.get('complete') in (True, False) else None
                return {'items': items, 'pages': pages, 'complete': complete, 'status': 'observed', 'next_cursor': None}
            if cursor in seen:
                break
            seen.add(cursor)
        return {'items': items, 'pages': pages, 'complete': False, 'status': 'bounded', 'next_cursor': cursor}

    def change(self, repo, number, host=None, identity=None):
        from ..collect import parse_diff, human_reviews
        identity = identity or self.identity(repo, host)
        caps = self.read('codebase', 'get-read-capabilities', **identity)
        context = self.read('codebase', 'get-change-context', **identity, change_number=number)
        revision = context.get('revision')
        if not revision:
            raise ReadError('Change context omitted its revision')
        change = context.get('change') or {}
        evidence = {}
        for kind in ('files', 'comments', 'inline_comments', 'reviews', 'threads', 'checks', 'statuses', 'annotations', 'readiness', 'history'):
            if (caps.get('review_reads') or {}).get(kind) is not True:
                evidence[kind] = {'items': [], 'complete': None, 'status': 'unavailable', 'capability': (caps.get('review_reads') or {}).get(kind)}
            else:
                evidence[kind] = self.pages(identity, kind, number, revision)
        files = []
        for index, f in enumerate(evidence['files']['items']):
            path = f.get('filename') or f.get('path') or f.get('filepath')
            if not path:
                continue
            patch = {'items': [], 'complete': None, 'status': 'unavailable'}
            if index < MAX_PATCHES and (caps.get('review_reads') or {}).get('patch') is True and f.get('patch_available') is not False:
                patch = self.pages(identity, 'patch', number, revision, path=path)
            text = ''.join(x.get('patch') or x.get('content') or '' for x in patch['items'] if isinstance(x, dict))
            files.append({'path': path, 'previous': f.get('previous_filepath') or f.get('previous_filename'),
                          'additions': f.get('additions', 0), 'deletions': f.get('deletions', 0),
                          'hunks': parse_diff('+++ b/' + path + '\n' + text).get(path, []), 'patch_evidence': patch, 'provider_file': f})
        comments = []
        for kind in ('comments', 'inline_comments', 'reviews'):
            for c in evidence[kind]['items']:
                user = c.get('actor') or c.get('author') or c.get('user')
                author = (user.get('login') or user.get('name')) if isinstance(user, dict) else user
                comments.append({**c, 'author': author, 'body': c.get('body') or '', 'url': c.get('url') or c.get('html_url'),
                                 'created': c.get('created_at') or c.get('submitted_at'), 'updated': c.get('updated_at'),
                                 'line': c.get('line') or c.get('original_line'), 'reply_to': c.get('parent_id') or c.get('in_reply_to_id')})
        checks = []
        for c in evidence['checks']['items'] + evidence['statuses']['items']:
            checks.append({**c, 'name': c.get('name') or c.get('context') or 'check',
                           'state': c.get('conclusion') or c.get('state') or c.get('status') or 'unknown',
                           'url': c.get('url') or c.get('details_url') or c.get('target_url')})
        head = context.get('head_sha')
        reviews = normalize_reviews(evidence['reviews']['items'])
        return {'key': f"{identity['repo']}#{number}", 'repo': identity['repo'], 'number': number,
                'provider': identity['provider'], 'provider_host': identity['provider_host'], 'repository_url': identity.get('repository_url'),
                'product': True, 'identity': identity, 'title': change.get('title') or f'Change {number}', 'body': change.get('body') or '',
                'url': change.get('url'), 'author': change.get('author'), 'head': change.get('source_branch'), 'base': change.get('target_branch'),
                'head_sha': head, 'base_sha': context.get('base_sha'), 'prior_bases': [], 'labels': change.get('labels') or [],
                'additions': change.get('additions', 0), 'deletions': change.get('deletions', 0), 'created': change.get('created_at'),
                'files': files, 'files_complete': evidence['files']['complete'], 'files_missing': max(0, (change.get('changed_files') or 0)-len(files)), 'checks': checks, '_raw_comments': comments, '_annotations': evidence['annotations']['items'],
                '_threads': None, 'provider_threads': evidence['threads'], 'summary': '', 'risk': '', 'diagrams': [],
                'read_evidence': {'capabilities': caps, 'context': context, 'sections': evidence},
                **human_reviews(reviews, head)}


def normalize_reviews(items):
    """Canonical actors and reviewed revisions into the existing human-review model."""
    reviews = []
    for review in items:
        actor = dict(review.get('actor') or review.get('user') or {})
        if actor.get('is_bot') is True or str(actor.get('type') or '').lower() == 'bot':
            actor['type'] = 'Bot'
        reviews.append({**review, 'user': actor,
                        'commit_id': review.get('reviewed_revision') or review.get('commit_sha') or review.get('commit_id'),
                        'submitted_at': review.get('submitted_at') or review.get('created_at') or ''})
    return reviews


def parse_ref(ref, default_repo=None):
    if ref.isdigit() and default_repo:
        return default_repo, int(ref), None
    if '#' in ref and not ref.startswith(('http://', 'https://')):
        repo, number = ref.rsplit('#', 1)
        if number.isdigit():
            return repo, int(number), None
    u = urlsplit(ref)
    patterns = (r'^/(.+)/pull/(\d+)', r'^/(.+)/-/merge_requests/(\d+)', r'^/(.+)/pull-requests/(\d+)',
                r'^/(.+)/pullrequest/(\d+)', r'^/c/(.+)/\+/(\d+)')
    for pattern in patterns:
        m = re.match(pattern, u.path, re.I)
        if m and u.hostname:
            return m[1], int(m[2]), u.hostname
    raise ValueError('Use a registered repo#number, a provider change URL, or number with --repo')

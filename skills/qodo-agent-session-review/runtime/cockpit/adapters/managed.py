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
MAX_OPERATION_CALLS = None   # no cap on managed reads per operation: a multi-PR package reads in full
MAX_OPERATION_SECONDS = None   # no total time limit either; each read still has its own timeout
READ_TIMEOUT_SECONDS = 120
MAX_TIMEOUTS_IN_A_ROW = 3   # a stalled service: stop after this many reads time out in a row, and mark the rest unavailable
RATE_LIMIT_RETRIES = 3   # a rate-limited read waits for the reset and tries again, up to this many times
RATE_LIMIT_MAX_WAIT = 60
RATE_LIMIT_BACKOFF = (10, 20, 40)   # seconds, when the service gives no reset time: long enough to clear a one-minute window
RATE_LIMIT_TOTAL_WAIT = 300   # seconds an operation may spend waiting out rate limits, across all its reads
MAX_THROTTLED_IN_A_ROW = 2   # reads that stay rate-limited after their retries: this many in a row stop the operation
_CURRENT_BUDGET = ContextVar('cockpit_managed_read_budget', default=None)


class ReadError(RuntimeError):
    pass


class ScopedPermissionDenied(ReadError):
    """This provider read is unavailable; independent authorized reads may continue."""


class BudgetExceeded(ReadError):
    pass


def reset_wait(metadata):
    """Seconds until a rate limit resets, from the error's metadata: a duration, or reset_at (epoch seconds or ms, or
    ISO time). None when it gives neither; never negative (a stale reset means try now)."""
    for key in ('retry_after', 'retry_after_seconds', 'reset_after', 'reset_in_seconds'):
        value = metadata.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.0, float(value))
    at = metadata.get('reset_at')
    if isinstance(at, (int, float)) and not isinstance(at, bool):
        if at <= 0:
            return None   # QAR's sentinel for "no reset time given": use the backoff
        return max(0.0, (at / 1000 if at > 1e11 else at) - time.time())
    if isinstance(at, str):
        from datetime import datetime
        try:
            return max(0.0, datetime.fromisoformat(at.replace('Z', '+00:00')).timestamp() - time.time())
        except ValueError:
            return None
    return None


class RateLimited(ReadError):
    """The service throttled this read; retry_after is its suggested wait in seconds, when it gave one."""
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ReadBudget:
    """Shared across a whole product operation, including nested adapters and secondary reads. It counts the reads;
    a cap on calls or time applies only when a caller sets one (Ask Qodo, the system map), not by default."""
    def __init__(self, max_calls=None, seconds=None):
        self.max_calls = MAX_OPERATION_CALLS if max_calls is None else max_calls
        limit = MAX_OPERATION_SECONDS if seconds is None else seconds
        self.deadline = None if limit is None else time.monotonic() + limit
        self.calls = 0
        self.timeouts = 0   # reads that timed out in a row
        self.throttled = 0   # reads that stayed rate-limited after their retries, in a row
        self.waited = 0.0   # seconds spent waiting out rate limits

    def _left(self):
        return None if self.deadline is None else self.deadline - time.monotonic()

    def _spent(self):
        left = self._left()
        return ((self.max_calls is not None and self.calls >= self.max_calls) or (left is not None and left <= 0)
                or self.timeouts >= MAX_TIMEOUTS_IN_A_ROW or self.throttled >= MAX_THROTTLED_IN_A_ROW)

    def reserve(self):
        if self._spent():
            raise BudgetExceeded('Managed read operation budget exhausted; remaining evidence is unavailable')
        self.calls += 1
        left = self._left()
        return READ_TIMEOUT_SECONDS if left is None else min(READ_TIMEOUT_SECONDS, left)

    def summary(self):
        left = self._left()
        return {'calls': self.calls, 'max_calls': self.max_calls, 'timeouts_in_a_row': self.timeouts,
                'remaining_seconds': None if left is None else max(0, left),
                'exhausted': self._spent()}


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


def page_error(page, kind):
    """Reject malformed evidence before normalization; retain the rejected envelope as a visible gap."""
    if (not isinstance(page.get('items'), list) or 'complete' not in page
            or (page['complete'] is not None and type(page['complete']) is not bool)
            or 'next_cursor' not in page or not isinstance(page['next_cursor'], (str, type(None)))):
        return 'Malformed provider-evidence page for ' + kind
    for row in page['items']:
        if not isinstance(row, dict):
            return 'Malformed provider-evidence row for ' + kind
        if kind == 'files' and not any(isinstance(row.get(k), str) and row[k].strip()
                                       for k in ('filename', 'path', 'filepath')):
            return 'Changed-file evidence omitted its path'
    return None


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
        if 'RATE-LIMIT' in code.upper() or 'RATE_LIMIT' in code.upper():
            raise RateLimited(f'{group}/{tool}: {code}', reset_wait(metadata))
        if code.upper().startswith('MT-AUTH-'):
            raise PermissionDenied(f'{group}/{tool}: {code}; owner action required')
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
        self.own = budget is not None   # a caller's own limit (Ask Qodo, the system map) applies alongside the operation's
        self.budget = budget or current_budget() or ReadBudget()
        self.command = command or os.environ.get('QODO_AGENT_SESSION_REVIEW_CLI') or os.environ.get('REVIEW_COCKPIT_QODO') or shutil.which('qodo') or str(Path.home() / '.qodo/bin/qodo')

    def read(self, group, tool, max_seconds=None, **args):
        """max_seconds: a caller's own deadline for this read (the notes step's), within the operation's budget.
        Every attempt, a rate-limit retry included, reserves its own call and gets only the time still left."""
        budget = current_budget() or self.budget
        budgets = [budget] + ([self.budget] if self.own and self.budget is not budget else [])   # both count, the tighter one decides
        until = None if max_seconds is None else time.monotonic() + max_seconds
        def left():
            ends = [x for x in [None if until is None else until - time.monotonic()] + [b._left() for b in budgets] if x is not None]
            return min(ends) if ends else None
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            remaining = left()
            if remaining is not None and remaining <= 0:
                raise BudgetExceeded(f'{group}/{tool}: the caller\'s time ran out before the read')
            timeout = min([b.reserve() for b in budgets] + ([remaining] if remaining is not None else []))   # a cap on calls counts every attempt
            try:
                return self._read_once(group, tool, args, timeout, budget)
            except RateLimited as e:   # throttled: wait for the reset (or back off) and try again, within the time and waiting still left
                wait = min(RATE_LIMIT_MAX_WAIT, max(1.0, e.retry_after) if e.retry_after is not None else RATE_LIMIT_BACKOFF[min(attempt, len(RATE_LIMIT_BACKOFF) - 1)])
                remaining = left()
                if attempt == RATE_LIMIT_RETRIES or (remaining is not None and wait >= remaining) or budget.waited + wait > RATE_LIMIT_TOTAL_WAIT:
                    budget.throttled += 1   # persistent throttling: a couple of these in a row stop the operation instead of waiting read after read
                    raise
                budget.waited += wait
                time.sleep(wait)

    def _read_once(self, group, tool, args, timeout, budget):
        try:
            # Installed CLI 2.1.1 advertises --args-file. Preserve booleans/numbers/cursors
            # as JSON instead of treating every dynamic schema option as a string flag.
            with tempfile.TemporaryDirectory(prefix='cockpit-qodo-') as temporary:
                params = Path(temporary) / 'args.json'
                params.write_text(json.dumps({key: value for key, value in args.items() if value is not None}), encoding='utf-8')
                from ..cli_process import argv
                command = argv(self.command) + ['read', group, tool, '--args-file', str(params), '--json']
                result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            budget.timeouts += 1; budget.throttled = 0   # several timeouts in a row stop the operation (see MAX_TIMEOUTS_IN_A_ROW)
            raise ReadError(f'{group}/{tool}: {type(e).__name__}') from e
        except PermissionError as e:
            budget.timeouts = budget.throttled = 0   # any other outcome breaks both runs
            raise PermissionDenied(f'{group}/{tool}: process permission denied; owner action required') from e
        except OSError as e:
            budget.timeouts = budget.throttled = 0
            raise ReadError(f'{group}/{tool}: {type(e).__name__}') from e
        budget.timeouts = 0   # the process answered: not a timeout
        try:
            out = decode_result(result, group, tool)
        except RateLimited:
            raise   # a throttled attempt: read() decides whether the run of throttled reads grows
        except Exception:
            budget.throttled = 0   # a different failure breaks the run of throttled reads
            raise
        budget.throttled = 0   # an answered read ends a run of throttled ones
        return out

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
            # Mixing revisions would associate patches/evidence with the wrong head. Abort collection.
            if revision and page.get('revision') != revision:
                raise ReadError('Change revision changed or missing while reading ' + kind + '; restart collection')
            if page.get('qar_operation_result_truncated'):
                return {'items': items, 'pages': pages, 'rejected_page': page, 'complete': False,
                        'status': 'bounded', 'error': 'QAR truncated the review-data page', 'next_cursor': cursor}
            malformed = page_error(page, kind)
            if malformed:
                return {'items': items, 'pages': pages, 'rejected_page': page, 'complete': False,
                        'status': 'malformed', 'error': malformed, 'next_cursor': cursor}
            next_cursor = page.get('next_cursor')
            if next_cursor and next_cursor in seen:
                return {'items': items, 'pages': pages, 'rejected_page': page, 'complete': False,
                        'status': 'bounded', 'error': 'Review-data continuation cursor did not advance', 'next_cursor': next_cursor}
            pages.append(page)
            items.extend(page.get('items') or [])
            cursor = next_cursor
            if not cursor:
                complete = page.get('complete') if page.get('complete') in (True, False) else None
                return {'items': items, 'pages': pages, 'complete': complete, 'status': 'observed', 'next_cursor': None}
            seen.add(cursor)
        return {'items': items, 'pages': pages, 'complete': False, 'status': 'bounded', 'next_cursor': cursor}

    def change(self, repo, number, host=None, identity=None):
        from ..collect import parse_diff
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
            path = next(f[k] for k in ('filename', 'path', 'filepath') if isinstance(f.get(k), str) and f[k].strip())
            patch = {'items': [], 'complete': None, 'status': 'unavailable'}
            if index < MAX_PATCHES and (caps.get('review_reads') or {}).get('patch') is True and f.get('patch_available') is not False:
                patch = self.pages(identity, 'patch', number, revision, path=path)
            text = ''.join(x.get('patch') or x.get('content') or '' for x in patch['items'] if isinstance(x, dict))
            files.append({'path': path, 'previous': f.get('previous_filepath') or f.get('previous_filename'),
                          'additions': f.get('additions', 0), 'deletions': f.get('deletions', 0),
                          'hunks': parse_diff('+++ b/' + path + '\n' + text, deleted_path=path).get(path, []), 'patch_evidence': patch, 'provider_file': f})
        comments = []
        for kind in ('comments', 'inline_comments', 'reviews'):
            for c in evidence[kind]['items']:
                user = c.get('actor') or c.get('author') or c.get('user')
                author = (user.get('login') or user.get('name')) if isinstance(user, dict) else user
                comments.append({**c, 'author': author, 'body': c.get('body') or '', 'url': c.get('url') or c.get('html_url'),
                                 'created': c.get('created_at') or c.get('submitted_at'), 'updated': c.get('updated_at'),
                                 'line': c.get('line') if identity['provider'] == 'github' else c.get('line') or c.get('original_line'),
                                 'reply_to': c.get('parent_id') or c.get('in_reply_to_id'),
                                 **({'provider_position_current': False} if identity['provider'] == 'github'
                                    and 'line' in c and c['line'] is None and c.get('original_line') is not None else {})})
        checks = []
        for c in evidence['checks']['items'] + evidence['statuses']['items']:
            checks.append({**c, 'name': c.get('name') or c.get('context') or 'check',
                           'state': c.get('conclusion') or c.get('state') or c.get('status') or 'unknown',
                           'url': c.get('url') or c.get('details_url') or c.get('target_url')})
        head = context.get('head_sha')
        reviews = normalize_reviews(evidence['reviews']['items'])
        human, decision_known = human_review_decision(reviews, head)
        decision_known = decision_known and evidence['reviews'].get('complete') is True
        if not decision_known:
            human = {'approvals': [], 'changes_requested': []}
        return {'key': f"{identity['repo']}#{number}", 'repo': identity['repo'], 'number': number,
                'provider': identity['provider'], 'provider_host': identity['provider_host'], 'repository_url': identity.get('repository_url'),
                'product': True, 'identity': identity, 'title': change.get('title') or f'Change {number}', 'body': change.get('body') or '',
                'url': change.get('url'), 'author': change.get('author'), 'head': change.get('source_branch'), 'base': change.get('target_branch'),
                'head_sha': head, 'base_sha': context.get('base_sha'), 'prior_bases': [], 'labels': change.get('labels') or [],
                'additions': change.get('additions', 0), 'deletions': change.get('deletions', 0), 'created': change.get('created_at'),
                'files': files, 'files_complete': evidence['files']['complete'], 'files_missing': max(0, (change.get('changed_files') or 0)-len(files)), 'checks': checks, '_raw_comments': comments, '_annotations': evidence['annotations']['items'],
                '_threads': None, 'provider_threads': evidence['threads'], 'summary': '', 'risk': '', 'diagrams': [],
                'read_evidence': {'capabilities': caps, 'context': context, 'sections': evidence},
                'review_decision_complete': decision_known, **human}



def human_review_decision(reviews, head):
    """Latest decisive human review needs a head and ordering evidence, not only a full page."""
    from ..collect import human_reviews
    decisive = []
    for review in reviews:
        actor = review.get('user') or {}
        login = actor.get('login') or ''
        if not login or actor.get('type') == 'Bot' or login.endswith('[bot]') or login.lower().startswith('qodo'):
            continue
        if str(review.get('state') or '').upper() in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
            decisive.append(review)
    known = bool(head) and all(isinstance(review.get('submitted_at'), str) and review['submitted_at'] for review in decisive)
    return (human_reviews(reviews, head) if known else {'approvals': [], 'changes_requested': []}), known


def normalize_reviews(items):
    """Canonical actors and reviewed revisions into the existing human-review model."""
    reviews = []
    for review in items:
        actor = dict(review.get('actor') or review.get('user') or {})
        if actor.get('is_bot') is True or str(actor.get('type') or '').lower() == 'bot':
            actor['type'] = 'Bot'
        submitted = review.get('submitted_at') or review.get('created_at')
        reviews.append({**review, 'user': actor,
                        'commit_id': review.get('reviewed_revision') or review.get('commit_sha') or review.get('commit_id'),
                        'submitted_at': submitted if isinstance(submitted, str) else ''})
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

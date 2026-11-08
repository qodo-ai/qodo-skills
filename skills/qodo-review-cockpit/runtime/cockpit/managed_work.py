"""Product collection and secondary reads, using only the managed adapter."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .adapters.managed import Client, ReadError, BudgetExceeded, bounded_operation, normalize_reviews, parse_ref
from .util import write_json


def canonical_identity(pr):
    identity = pr.get('identity') or {}
    return (identity.get('provider') or pr.get('provider'), identity.get('provider_host') or pr.get('provider_host'), pr['repo'])


def validate_identities(prs):
    grouped = defaultdict(set)
    for pr in prs:
        grouped[pr['repo']].add(canonical_identity(pr))
    if any(len(identities) > 1 for identities in grouped.values()):
        raise ReadError('The same repository path maps to different provider/hosts. Review these repositories in separate sessions; no associations were built.')
    return prs


def _rows(result):
    for key in ('pull_requests', 'prs', 'items', 'commits', 'results'):
        if isinstance(result.get(key), list):
            return result[key]
    return []


@bounded_operation
def collect(refs, default_repo, cfg):
    from .collect import build
    client = Client()
    requested = list(refs)
    prs, omitted = [], []
    for index, ref in enumerate(requested):
        try:
            repo, number, host = parse_ref(ref, default_repo)
            prs.append(client.change(repo, number, host))
            validate_identities(prs)
        except BudgetExceeded:
            if not prs:
                raise
            omitted = requested[index:]
            break
    meta = {'complete': not omitted, 'requested_refs': requested, 'collected_refs': requested[:len(prs)],
            'omitted_refs': omitted, 'default_repo': default_repo,
            'reason': 'budget_exhausted' if omitted else None}
    return build(prs, cfg, collection_meta=meta)



@bounded_operation
def refresh(sdir, old, cfg):
    from .product import scope
    from .session_writer import session_writer
    with scope({'product': True}), session_writer(sdir):
        # The caller may have read before a newer enrichment was accepted.
        current = json.loads((sdir / 'review-data.json').read_text())
        return _refresh(sdir, current, cfg)


def _refresh(sdir, old, cfg):
    from .collect import build, _events
    client = Client()
    prs = []
    previous_collection = old.get('collection') or {}
    requested = previous_collection.get('requested_refs') or [p.get('url') or f"{p['repo']}#{p['number']}" for p in old['prs']]
    for ref in requested:
        repo, number, host = parse_ref(ref, previous_collection.get('default_repo'))
        collected = previous_collection.get('collected_refs') or []
        paired = list(zip(collected, old['prs'])) if len(collected) == len(old['prs']) else []
        # Exact saved inputs and returned native URLs bind to the identity observed at collection.
        saved = [p for p in old['prs'] if p.get('url') == ref or any(saved_ref == ref and candidate is p for saved_ref, candidate in paired)]
        saved = [p for p in saved if p['number'] == number and (p.get('identity') or {}).get('repo') == p['repo'] and
                 (not host or (p.get('identity') or {}).get('provider_host') == host)]
        if len(saved) > 1:
            raise ReadError('Saved input reference maps to multiple changes; no identity was selected')
        previous = saved[0] if saved else next((p for p in old['prs'] if p['repo'] == repo and p['number'] == number and
                         (not host or (p.get('identity') or {}).get('provider_host') == host)), {})
        pr = client.change(repo, number, host, identity=previous.get('identity'))
        pr['key'] = previous.get('key') or pr['key']
        prs.append(pr)
        validate_identities(prs)
    meta = {'complete': True, 'requested_refs': requested, 'collected_refs': requested,
            'omitted_refs': [], 'default_repo': previous_collection.get('default_repo'), 'reason': None}
    known = {e.get('github_id') for e in _events(sdir) if e.get('github_id')}
    snapshot_path = sdir / 'review-data.json'
    snapshot = snapshot_path.read_bytes()
    try:
        build(prs, cfg, session=sdir.name, reviewer_login=old.get('reviewer_login'), skip_github_ids=known, dest=sdir, collection_meta=meta, require_complete_budget=True)
        data = json.loads((sdir / 'review-data.json').read_text())
        if old.get('reviewers'):
            from .reviewers import basis
            data['reviewers'] = {**old['reviewers'], 'stale': old['reviewers'].get('basis') != basis(data)}
        write_json(sdir / 'review-data.json', data)
        warnings = []
        if (sdir / 'enrich.json').is_file():
            from .enrich import enrich
            warnings = enrich(sdir, json.loads((sdir / 'enrich.json').read_text()))['warnings']
        return {'session': sdir.name, 'warnings': warnings}
    except BaseException:
        # Rebuild and re-enrichment are one saved-snapshot operation. Local events are
        # append-only and may include concurrent reader work: never roll their log back.
        import os
        import tempfile
        fd, temporary = tempfile.mkstemp(dir=sdir, prefix='.refresh-rollback-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(snapshot)
            os.replace(temporary, snapshot_path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        raise



@bounded_operation
def live_state(prs, since_default=''):
    out, client = {}, Client()
    for pr in prs:
        try:
            identity = pr.get('identity') or client.identity(pr['repo'], pr.get('provider_host'))
            ctx = client.read('codebase', 'get-change-context', **identity, change_number=pr['number'])
            if not ctx.get('revision'):
                raise ReadError('Change context omitted its revision')
            ready = client.pages(identity, 'readiness', pr['number'], ctx['revision'])
            comments = client.pages(identity, 'comments', pr['number'], ctx['revision'])
            reviews = client.pages(identity, 'reviews', pr['number'], ctx['revision'])
            observed_ready = next(iter(ready['items']), {})
            known_readiness = ready.get('complete') is True
            r = observed_ready if known_readiness else {}
            known_comments = comments.get('complete') is True
            head, old = ctx.get('head_sha'), pr.get('head_sha')
            since = pr.get('collected_at') or since_default
            observed_comments = sum(c.get('created_at', '') > since for c in comments['items'])
            from .collect import human_reviews
            known_reviews = reviews.get('complete') is True
            normalized = normalize_reviews(reviews['items'])
            human = human_reviews(normalized, head) if known_reviews and head else None
            baseline = pr.get('approvals') if pr.get('head_sha') == head and isinstance(pr.get('approvals'), list) else []
            newly_observed = [name for name in human['approvals'] if name not in baseline] if human else None
            decision = ('CHANGES_REQUESTED' if human['changes_requested'] else 'APPROVED' if human['approvals'] else None) if human else None
            out[pr['key']] = {'head': head, 'snapshot_head': old, 'moved': bool(head and old and head != old),
                             'new_commits': -1 if head != old else 0, 'state': str(r.get('state') or '').upper() or None, 'merge_state': r.get('native_state'),
                             'draft': r.get('draft'), 'review_decision': decision, 'approved_by': newly_observed, 'current_approved_by': human['approvals'] if human else None,
                             'reviews_complete': known_reviews, 'review_decision_source': 'observed_human_reviews' if human else 'unknown',
                             'new_comments': observed_comments if known_comments else None,
                             'new_comments_observed': observed_comments, 'comments_complete': known_comments,
                             'readiness_complete': known_readiness, 'observed_readiness': observed_ready,
                             'read_evidence': {'context': ctx, 'readiness': ready, 'comments': comments, 'reviews': reviews}}
        except ReadError as e:
            out[pr['key']] = {'error': str(e), 'complete': False}
    return out


@bounded_operation
def related(prs, ctx):
    client, out = Client(), []
    for r in ctx.get('related', [])[:20]:
        try:
            repo, number, host = parse_ref(r['key'])
            identity = client.identity(repo, host)
            change = client.read('codebase', 'get-change-context', **identity, change_number=number)
            out.append({**r, 'title': (change.get('change') or {}).get('title'), 'url': (change.get('change') or {}).get('url'),
                        'read_evidence': change})
        except (ReadError, ValueError) as e:
            out.append({**r, 'unavailable': str(e)})
    return out


@bounded_operation
def overlaps(prs, cfg, session=None):
    """Bounded open/merged history. Gaps are explicit; no clean/non-overlapping inference."""
    from .overlaps import _hit, spans
    client, out, warnings = Client(), [], []
    own = {(canonical_identity(p), p['number']) for p in prs}
    grouped = defaultdict(list)
    for p in prs:
        grouped[canonical_identity(p)].append(p)
    if (cfg.get('overlaps') or {}).get('enabled') is False:
        return [], []
    for canonical, ours in grouped.items():
        repo = canonical[2]
        identity = ours[0]['identity']
        for state in ('open', 'merged'):
            try:
                result = client.read('codebase', 'list-prs', repo=identity.get('repository_url') or repo, state=state, max_results=10)
                rows = _rows(result)
                warnings.append(f'overlaps: {repo} {state} discovery bounded to 10 changes; not exhaustive')
                for row in rows[:10]:
                    number = row.get('number') or row.get('pr_number')
                    if not number or (canonical, number) in own:
                        continue
                    context = client.read('codebase', 'get-change-context', **identity, change_number=number)
                    if not context.get('revision'):
                        raise ReadError('Change context omitted its revision')
                    files = client.pages(identity, 'files', number, context['revision'])
                    if files['complete'] is not True:
                        warnings.append(f'overlaps: {repo}#{number} files incomplete/unknown')
                    changed = {f.get('filename') or f.get('path') for f in files['items']}
                    other = {'repo': repo, 'number': number, 'key': f'{canonical[0]}@{canonical[1]}/{repo}#{number}', 'title': row.get('title'),
                             'url': row.get('url'), 'state': state, 'read_evidence': {'context': context, 'files': files}}
                    for pr in ours:
                        for f in pr['files']:
                            if f['path'] in changed:
                                # No shared base/line proof here: a path overlap only.
                                out.append(_hit(pr, 'open_pr' if state == 'open' else 'merged', other, f['path'], spans(f['hunks']), [], 0))
            except ReadError as e:
                warnings.append(f'overlaps: {repo} {state} unavailable: {e}')
    for pr in prs:
        pr['overlap_spans'] = []
        pr['overlap_read_warnings'] = warnings
    return out, warnings


@bounded_operation
def reviewers(data, cfg, max_calls):
    """Historical human reviewers through managed history; reports the bounded basis."""
    from .reviewers import basis
    client, calls, failed, evidence = Client(), 0, 0, defaultdict(list)
    excluded = {p.get('author') for p in data['prs']} | {data.get('reviewer_login')}
    owned, gaps = {}, {}
    for pr in data['prs']:
        identity = pr['identity']
        try:
            if calls >= max_calls:
                break
            calls += 1
            result = client.read('codebase', 'list-prs', repo=identity.get('repository_url') or pr['repo'], state='merged', max_results=5)
            gaps[pr['repo']] = 'Bounded recent merged changes; CODEOWNERS, per-path authorship and similar-PR scoring not qualified'
            for r in _rows(result)[:5]:
                if calls + 2 > max_calls:
                    break
                number = r.get('number') or r.get('pr_number')
                if not number:
                    continue
                calls += 2
                ctx = client.read('codebase', 'get-change-context', **identity, change_number=number)
                if not ctx.get('revision'):
                    raise ReadError('Change context omitted its revision')
                reviews = client.pages(identity, 'reviews', number, ctx['revision'])
                for rv in normalize_reviews(reviews['items']):
                    actor = rv['user']
                    login = actor.get('login')
                    if login and login not in excluded and actor.get('type') != 'Bot' and not login.endswith('[bot]'):
                        evidence[login].append({'pr': pr['key'], 'why': f'Reviewed {pr["repo"]}#{number}; recent history, path ownership unverified', 'source': reviews})
        except ReadError as e:
            failed += 1
            gaps[pr['repo']] = str(e)
    return {'suggested': [{'login': u, 'score': len(es), 'weak': True, 'prs': sorted({e['pr'] for e in es}),
                           'evidence': list(dict.fromkeys(e['why'] for e in es)), 'read_evidence': es} for u, es in evidence.items()],
            'ownership_complete': False, 'basis': basis(data), 'similar_unavailable': gaps, 'failed_calls': failed, 'calls': calls,
            'excluded': sorted(x for x in excluded if x), 'complete': False}

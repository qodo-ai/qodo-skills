"""Product collection and secondary reads, using only the managed adapter."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .adapters.managed import Client, ReadError, bounded_operation, parse_ref
from .util import write_json


def canonical_identity(pr):
    identity = pr.get('identity') or {}
    return (identity.get('provider') or pr.get('provider'), identity.get('provider_host') or pr.get('provider_host'), pr['repo'])


def qualify_keys(prs):
    grouped = defaultdict(list)
    for pr in prs:
        grouped[pr['key']].append(pr)
    for group in grouped.values():
        if len({canonical_identity(p) for p in group}) > 1:
            for pr in group:
                provider, host, repo = canonical_identity(pr)
                pr['key'] = f'{provider}@{host}/{repo}#{pr["number"]}'
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
    prs = [client.change(repo, number, host) for repo, number, host in (parse_ref(r, default_repo) for r in refs)]
    return build(qualify_keys(prs), cfg)


@bounded_operation
def refresh(sdir, old, cfg):
    from .collect import build, _events
    from .product import activate
    activate()
    client = Client()
    prs = [{**client.change(p['repo'], p['number'], identity=p.get('identity')), 'key': p['key']} for p in old['prs']]
    known = {e.get('github_id') for e in _events(sdir) if e.get('github_id')}
    build(prs, cfg, session=sdir.name, reviewer_login=old.get('reviewer_login'), skip_github_ids=known, dest=sdir)
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
            r = next(iter(ready['items']), {})
            head, old = ctx.get('head_sha'), pr.get('head_sha')
            since = pr.get('collected_at') or since_default
            out[pr['key']] = {'head': head, 'snapshot_head': old, 'moved': bool(head and old and head != old),
                             'new_commits': -1 if head != old else 0, 'state': r.get('state'), 'merge_state': r.get('native_state'),
                             'draft': r.get('draft'), 'review_decision': None, 'approved_by': [],
                             'new_comments': sum(c.get('created_at', '') > since for c in comments['items']),
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
                for rv in reviews['items']:
                    actor = rv.get('actor') or rv.get('user') or {}
                    login = actor.get('login')
                    if login and login not in excluded and not actor.get('is_bot') and not login.endswith('[bot]'):
                        evidence[login].append({'pr': pr['key'], 'why': f'Reviewed {pr["repo"]}#{number}; recent history, path ownership unverified', 'source': reviews})
        except ReadError as e:
            failed += 1
            gaps[pr['repo']] = str(e)
    return {'suggested': [{'login': u, 'score': len(es), 'weak': True, 'prs': sorted({e['pr'] for e in es}),
                           'evidence': list(dict.fromkeys(e['why'] for e in es)), 'read_evidence': es} for u, es in evidence.items()],
            'ownership_complete': False, 'basis': basis(data), 'similar_unavailable': gaps, 'failed_calls': failed, 'calls': calls,
            'excluded': sorted(x for x in excluded if x), 'complete': False}

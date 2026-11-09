"""Qualify managed finding coordinates independently of finding origin."""
from __future__ import annotations


def qualify(pr: dict, finding: dict) -> dict:
    local = finding.get('local') if isinstance(finding.get('local'), dict) else {}
    if 'review_source' not in finding and finding.get('source') != 'qodo-local' and local.get('origin') != 'managed' and 'source_location' not in finding:
        return finding
    recorded = finding.get('source_location') or local.get('source_location')
    original = dict(recorded) if isinstance(recorded, dict) else {
        'path': finding.get('path'), 'line': finding.get('line') if finding.get('line') is not None else local.get('line'), 'end_line': finding.get('end_line'),
        'side': finding.get('side'), 'git_sha': finding.get('git_sha') or finding.get('commit') or local.get('commit'),
        'review_run_id': finding.get('review_run_id') or local.get('review_id'),
    }
    side = {'left': 'LEFT', 'old': 'LEFT', 'right': 'RIGHT', 'new': 'RIGHT'}.get(str(original.get('side') or '').lower())
    # Head SHA identifies the new tree; only a known PR-origin finding binds its old diff side.
    hosted = finding.get('review_source') == 'git_pr' and local.get('origin') != 'managed'
    sha, head = original.get('git_sha'), pr.get('head_sha')
    current = bool(isinstance(sha, str) and isinstance(head, str) and sha and sha.lower() == head.lower()
                   and side in (('LEFT', 'RIGHT') if hosted else ('RIGHT',))
                   and original.get('path') in {f.get('path') for f in pr.get('files', [])}
                   and type(original.get('line')) is int and original['line'] > 0)
    out = {**finding, 'source_location': original, 'current_anchor': current,
           'side': side if side else original.get('side')}
    if finding.get('source') == 'qodo-local':
        out['local'] = {**local, 'source_location': original, 'current_anchor': current}
        if local.get('origin') != 'managed':
            out['local']['line'] = None if current else original.get('line')
    for name in ('path', 'line', 'end_line'):
        out[name] = original.get(name) if current else None
    return out

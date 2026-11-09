"""Stable authored-finding identity across array edits and managed refreshes."""
import hashlib
import json


def fingerprint(finding):
    fields = {key: finding.get(key, default) for key, default in (
        ('category', 'general'), ('severity', 'medium'), ('path', None), ('line', None), ('title', ''), ('body', ''))}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def remembered(pr):
    known = dict(pr.get('agent_finding_ids') or {})
    occurrences = {}
    for finding in pr.get('findings', []):
        if finding.get('source') != 'agent':
            continue
        key = fingerprint(finding)
        index = occurrences.get(key, 0); occurrences[key] = index + 1
        known.setdefault(key + ':' + str(index), finding['id'])
    return known


def assign(pr, findings, reserved_ids=()):
    known = remembered(pr)
    prefix = 'a-' + pr['key'].replace('/', '-').replace('#', '-') + '-'
    used, seen, occurrences, ids = set(known.values()) | set(reserved_ids), set(), {}, []
    number = 0
    for finding in findings:
        key = fingerprint(finding)
        index = occurrences.get(key, 0); occurrences[key] = index + 1
        key += ':' + str(index)
        explicit = finding.get('id')
        if isinstance(explicit, str) and explicit:
            fid = explicit if explicit.startswith(prefix) else prefix + 'named-' + hashlib.sha256(explicit.encode()).hexdigest()[:16]
        else:
            fid = known.get(key)
            if not fid:
                while prefix + str(number) in used:
                    number += 1
                fid = prefix + str(number)
        if fid in seen:
            raise ValueError('Agent findings need distinct IDs; do not reuse an explicit ID in one PR.')
        ids.append(fid); seen.add(fid); used.add(fid); known[key] = fid
    pr['agent_finding_ids'] = known
    return ids
